import json
import time
import logging
from typing import Any, Dict, List, Tuple, Optional

from utils.model import get_gpt_response, parse_gpt_meal_conversion_response
from utils.prompt import get_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

PRICING_PER_1M = {
    "gpt-4o": {"input": 2.50, "cached_input": 1.25, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-4.1-nano": {"input": 0.10, "cached_input": 0.025, "output": 0.40},
}


def _percentile(values: List[float], pct: float) -> float:
    """Simple percentile without numpy. pct in [0, 100]."""
    if not values:
        return 0.0
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(values_sorted) - 1)
    if f == c:
        return float(values_sorted[f])
    return float(values_sorted[f] + (values_sorted[c] - values_sorted[f]) * (k - f))


def _safe_get_usage(response: Any) -> Tuple[int, int, int, int]:
    """
    Extract usage from response.

    Supports your object:
      ResponseUsage(input_tokens=..., input_tokens_details.cached_tokens=...,
                    output_tokens=..., total_tokens=...)

    Returns: (input_tokens, output_tokens, total_tokens, cached_input_tokens)
    """
    usage = None
    if hasattr(response, "usage"):
        usage = getattr(response, "usage")
    elif isinstance(response, dict):
        usage = response.get("usage")

    if usage is None:
        return 0, 0, 0, 0

    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    cached_input_tokens = 0

    if hasattr(usage, "__dict__"):
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or 0)

        details = getattr(usage, "input_tokens_details", None)
        if details is not None:
            cached_input_tokens = int(getattr(details, "cached_tokens", 0) or 0)

    elif isinstance(usage, dict):
        input_tokens = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0)
        output_tokens = int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0)
        total_tokens = int(usage.get("total_tokens", 0) or (input_tokens + output_tokens))

        details = usage.get("input_tokens_details", {}) or {}
        cached_input_tokens = int(details.get("cached_tokens", 0) or 0)

    cached_input_tokens = min(cached_input_tokens, input_tokens)
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens

    return input_tokens, output_tokens, total_tokens, cached_input_tokens


def estimate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    *,
    cached_prompt_tokens: int = 0,
) -> float:
    
    """
    Estimate cost using text-token pricing (USD per 1M tokens).
    If cached_prompt_tokens is provided, that portion is charged at cached_input rate.
    """

    logging.info(f"Estimating cost for model={model} with prompt_tokens={prompt_tokens}, ")
    logging.info(f"completion_tokens={completion_tokens}, cached_prompt_tokens={cached_prompt_tokens}")

    if model not in PRICING_PER_1M:
        return 0.0

    rates = PRICING_PER_1M[model]
    cached_prompt_tokens = min(int(cached_prompt_tokens or 0), int(prompt_tokens or 0))
    non_cached_prompt_tokens = int(prompt_tokens or 0) - cached_prompt_tokens

    cost = (
        (non_cached_prompt_tokens / 1_000_000) * rates["input"]
        + (cached_prompt_tokens / 1_000_000) * rates["cached_input"]
        + (int(completion_tokens or 0) / 1_000_000) * rates["output"]
    )

    return float(cost)


def evaluate_model(model: str, system_prompt: str, test_set: list, results_path: str):
    results: List[Dict[str, Any]] = []

    sum_precision = 0.0
    sum_recall = 0.0
    sum_f1_score = 0.0
    sum_confidence_score_error = 0.0

    latencies_ms: List[float] = []
    prompt_tokens_list: List[int] = []
    completion_tokens_list: List[int] = []
    total_tokens_list: List[int] = []
    costs_usd: List[float] = []

    for test in test_set:
        logging.info(f"Evaluating model {model} on test input: {test['input']}")
        user_prompt = test["input"]

        # ---- latency timing (end-to-end for model call) ----
        t0 = time.perf_counter()
        response = get_gpt_response(model, system_prompt, user_prompt)
        t1 = time.perf_counter()
        latency_ms = (t1 - t0) * 1000.0
        latencies_ms.append(latency_ms)

        # Cost
        prompt_tokens, completion_tokens, total_tokens, cached_prompt_tokens = _safe_get_usage(response)
        prompt_tokens_list.append(prompt_tokens)
        completion_tokens_list.append(completion_tokens)
        total_tokens_list.append(total_tokens)

        cost_usd = estimate_cost_usd(
            model,
            prompt_tokens,
            completion_tokens,
            cached_prompt_tokens=cached_prompt_tokens,
        )
        costs_usd.append(cost_usd)

        parsed_response = parse_gpt_meal_conversion_response(response.output_text)
        ingredients = parsed_response["ingredients"]
        confidence_score = parsed_response["confidence_score"]

        ground_truth_ingredients = test["output"]["ingredients"]
        ground_truth_confidence = test["output"]["confidence_score"]

        recall = (
            len(set(ingredients) & set(ground_truth_ingredients)) / len(set(ground_truth_ingredients))
            if ground_truth_ingredients else 0.0
        )
        precision = (
            len(set(ingredients) & set(ground_truth_ingredients)) / len(set(ingredients))
            if ingredients else 0.0
        )
        confidence_score_error = abs(confidence_score - ground_truth_confidence)
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0 else 0.0
        )

        results.append({
            "input": user_prompt,
            "prediction": {
                "ingredients": ingredients,
                "confidence_score": confidence_score
            },
            "ground_truth": {
                "ingredients": ground_truth_ingredients,
                "confidence_score": ground_truth_confidence
            },
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_prompt_tokens": cached_prompt_tokens
            },
            "cost": {
                "usd_estimate": cost_usd
            },
            "metrics": {
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "confidence_score_error": confidence_score_error,
                "latency_ms": latency_ms
            }
        })

        sum_precision += precision
        sum_recall += recall
        sum_f1_score += f1_score
        sum_confidence_score_error += confidence_score_error

    n = max(len(test_set), 1)
    avg_precision = sum_precision / n
    avg_recall = sum_recall / n
    avg_f1 = sum_f1_score / n
    avg_conf_err = sum_confidence_score_error / n

    # latency summary
    latency_summary = {
        "avg": (sum(latencies_ms) / n) if latencies_ms else 0.0,
        "p50": _percentile(latencies_ms, 50),
        "p95": _percentile(latencies_ms, 95),
        "p99": _percentile(latencies_ms, 99),
        "max": max(latencies_ms) if latencies_ms else 0.0,
    }

    # token + cost summary
    cost_summary = {
        "avg_usd": (sum(costs_usd) / n) if costs_usd else 0.0,
        "p50_usd": _percentile(costs_usd, 50),
        "p95_usd": _percentile(costs_usd, 95),
        "p99_usd": _percentile(costs_usd, 99),
        "total_usd": sum(costs_usd),
    }

    token_summary = {
        "avg_prompt_tokens": (sum(prompt_tokens_list) / n) if prompt_tokens_list else 0.0,
        "avg_completion_tokens": (sum(completion_tokens_list) / n) if completion_tokens_list else 0.0,
        "avg_total_tokens": (sum(total_tokens_list) / n) if total_tokens_list else 0.0,
        "p95_total_tokens": _percentile([float(x) for x in total_tokens_list], 95) if total_tokens_list else 0.0,
    }

    results.append({
        "average_metrics": {
            "precision": avg_precision,
            "recall": avg_recall,
            "f1_score": avg_f1,
            "confidence_score_error": avg_conf_err,
            "latency_ms": latency_summary,
            "tokens": token_summary,
            "cost": cost_summary,
            "number_of_tests": n,
        }
    })

    with open(results_path, "w") as file:
        json.dump(results, file, indent=4)


def compare_models(models: list, results_paths: list, model_comparison_path: str, number_of_tests: int):
    logging.info(f"Comparing models: {models} using results from paths: {results_paths}")
    with open(model_comparison_path, "w") as comparison_file:
        comparison_file.write(f"Model Comparison Results with {number_of_tests} tests:\n\n")

        for model, path in zip(models, results_paths):
            with open(path, "r") as file:
                results = json.load(file)
                avg = results[-1]["average_metrics"]

            comparison_file.write(f"Model: {model}\n")
            comparison_file.write(f"Average Precision: {avg['precision']:.4f}\n")
            comparison_file.write(f"Average Recall: {avg['recall']:.4f}\n")
            comparison_file.write(f"Average F1 Score: {avg['f1_score']:.4f}\n")
            comparison_file.write(f"Average Confidence Score Error: {avg['confidence_score_error']:.4f}\n")

            lat = avg.get("latency_ms", {})
            if isinstance(lat, dict):
                comparison_file.write(f"Latency avg (ms): {lat.get('avg', 0.0):.2f}\n")
                comparison_file.write(f"Latency p50 (ms): {lat.get('p50', 0.0):.2f}\n")
                comparison_file.write(f"Latency p95 (ms): {lat.get('p95', 0.0):.2f}\n")
                comparison_file.write(f"Latency p99 (ms): {lat.get('p99', 0.0):.2f}\n")
                comparison_file.write(f"Latency max (ms): {lat.get('max', 0.0):.2f}\n")

            tok = avg.get("tokens", {})
            if isinstance(tok, dict):
                comparison_file.write(f"Avg total tokens: {tok.get('avg_total_tokens', 0.0):.1f}\n")
                comparison_file.write(f"P95 total tokens: {tok.get('p95_total_tokens', 0.0):.1f}\n")

            cost = avg.get("cost", {})
            if isinstance(cost, dict):
                comparison_file.write(f"Avg cost (USD): {cost.get('avg_usd', 0.0):.6f}\n")
                comparison_file.write(f"P95 cost (USD): {cost.get('p95_usd', 0.0):.6f}\n")
                comparison_file.write(f"Total cost (USD): {cost.get('total_usd', 0.0):.6f}\n")

            comparison_file.write("\n")

            print(f"Model: {model}")
            print(f"Average Precision: {avg['precision']:.4f}")
            print(f"Average Recall: {avg['recall']:.4f}")
            print(f"Average F1 Score: {avg['f1_score']:.4f}")
            print(f"Average Confidence Score Error: {avg['confidence_score_error']:.4f}")

            if isinstance(lat, dict):
                print(f"Latency avg (ms): {lat.get('avg', 0.0):.2f}")
                print(f"Latency p50 (ms): {lat.get('p50', 0.0):.2f}")
                print(f"Latency p95 (ms): {lat.get('p95', 0.0):.2f}")
                print(f"Latency p99 (ms): {lat.get('p99', 0.0):.2f}")
                print(f"Latency max (ms): {lat.get('max', 0.0):.2f}")

            if isinstance(tok, dict):
                print(f"Avg total tokens: {tok.get('avg_total_tokens', 0.0):.1f}")
                print(f"P95 total tokens: {tok.get('p95_total_tokens', 0.0):.1f}")

            if isinstance(cost, dict):
                print(f"Avg cost (USD): {cost.get('avg_usd', 0.0):.6f}")
                print(f"P95 cost (USD): {cost.get('p95_usd', 0.0):.6f}")
                print(f"Total cost (USD): {cost.get('total_usd', 0.0):.6f}")

            print()


if __name__ == "__main__":
    system_prompt = get_prompt(
        "prompts/system_prompts/meal_conversion/meal_conversion_v3.txt",
        "prompts/few_shot_examples/meal_conversion_examples.json",
    )

    with open("prompts/test_sets/meal_conversion_tests.json", "r") as file:
        test_set = json.load(file)

    models = ["gpt-4o", "gpt-4o-mini", "gpt-4.1-nano"]

    for model in models:
        evaluate_model(
            model,
            system_prompt,
            test_set["tests"],
            f"model_selection/models/{model}_meal_conversion_test_results.json",
        )

    compare_models(
        models,
        [f"model_selection/models/{model}_meal_conversion_test_results.json" for model in models],
        "model_selection/model_comparison.txt",
        number_of_tests=len(test_set["tests"]),
    )
