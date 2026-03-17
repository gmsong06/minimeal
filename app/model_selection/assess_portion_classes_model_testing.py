import json
import time
import logging
from typing import Any, Dict, List, Tuple

from utils.model import get_gpt_response, parse_gpt_assign_portion_classes_response
from utils.prompt import get_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

PRICING_PER_1M = {
    "gpt-4o": {"input": 2.50, "cached_input": 1.25, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-4.1-nano": {"input": 0.10, "cached_input": 0.025, "output": 0.40},
}


ALLOWED_CLASSES = {
    "primary_protein",
    "secondary_protein",
    "primary_starch",
    "secondary_starch",
    "primary_veg",
    "secondary_veg",
    "legume_component",
    "sauce_condiment",
    "added_fat",
    "dairy_component",
    "snack_item_single",
    "snack_handful",
    "beverage_caloric",
    "beverage_noncaloric",
    "garnish_trace",
    "other",
}


def _percentile(values: List[float], pct: float) -> float:
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


def _normalize_food_name(s: str) -> str:
    # Keep very conservative normalization to avoid "inventing" foods.
    return (s or "").strip().lower()


def _extract_pred_map(parsed: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    parsed output format expected:
    {
      "meal_description": "...",
      "foods": [{"name": "...", "portion_class": "...", "confidence": 0.0-1.0}, ...],
      "notes": [...]
    }
    """
    pred_map: Dict[str, Dict[str, Any]] = {}
    foods = parsed.get("foods", []) or []
    for item in foods:
        name = _normalize_food_name(item.get("name", ""))
        # If duplicates exist (e.g., onion appears twice), keep the first occurrence only;
        # optionally you can change this to keep a list per name.
        if name and name not in pred_map:
            pred_map[name] = {
                "portion_class": item.get("portion_class"),
                "confidence": item.get("confidence"),
            }
    return pred_map


def _extract_truth_map(example: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    truth_map: Dict[str, Dict[str, Any]] = {}
    foods = example.get("output", {}).get("foods", []) or []
    for item in foods:
        name = _normalize_food_name(item.get("name", ""))
        if name and name not in truth_map:
            truth_map[name] = {
                "portion_class": item.get("portion_class"),
                "confidence": item.get("confidence"),
            }
    return truth_map


def _evaluate_example(
    example: Dict[str, Any],
    pred_parsed: Dict[str, Any],
) -> Dict[str, float]:
    """
    Metrics:
      - class_accuracy: exact match rate for portion_class over foods in input list
      - confidence_mae: mean absolute error vs ground-truth confidence (only where both present)
      - invalid_class_rate: fraction of predicted items with portion_class not in allowed set
      - missing_item_rate: fraction of input foods missing from prediction
      - extra_item_rate: fraction of predicted foods not in input foods list (should be 0 if parser is strict)
    """
    input_foods = example["input"]["foods"]
    input_names = [_normalize_food_name(x) for x in input_foods]
    input_set = set(input_names)

    pred_map = _extract_pred_map(pred_parsed)
    truth_map = _extract_truth_map(example)

    # invalid class rate over predicted items
    invalid = 0
    for v in pred_map.values():
        pc = v.get("portion_class")
        if pc not in ALLOWED_CLASSES:
            invalid += 1
    invalid_class_rate = invalid / max(len(pred_map), 1)

    # missing / extra
    missing = sum(1 for n in input_names if n not in pred_map)
    missing_item_rate = missing / max(len(input_names), 1)

    extra = sum(1 for n in pred_map.keys() if n not in input_set)
    extra_item_rate = extra / max(len(pred_map), 1)

    # class accuracy + confidence MAE (aligned by normalized name)
    correct = 0
    conf_abs_err_sum = 0.0
    conf_cnt = 0

    for n in input_names:
        pred = pred_map.get(n)
        truth = truth_map.get(n)

        if pred and truth:
            if pred.get("portion_class") == truth.get("portion_class"):
                correct += 1

            pred_c = pred.get("confidence")
            truth_c = truth.get("confidence")
            if isinstance(pred_c, (int, float)) and isinstance(truth_c, (int, float)):
                conf_abs_err_sum += abs(float(pred_c) - float(truth_c))
                conf_cnt += 1

    class_accuracy = correct / max(len(input_names), 1)
    confidence_mae = conf_abs_err_sum / max(conf_cnt, 1)

    return {
        "class_accuracy": class_accuracy,
        "confidence_mae": confidence_mae,
        "invalid_class_rate": invalid_class_rate,
        "missing_item_rate": missing_item_rate,
        "extra_item_rate": extra_item_rate,
    }


def evaluate_model(model: str, system_prompt: str, test_set: list, results_path: str):
    results: List[Dict[str, Any]] = []

    sum_class_acc = 0.0
    sum_conf_mae = 0.0
    sum_invalid_rate = 0.0
    sum_missing_rate = 0.0
    sum_extra_rate = 0.0

    latencies_ms: List[float] = []
    prompt_tokens_list: List[int] = []
    completion_tokens_list: List[int] = []
    total_tokens_list: List[int] = []
    costs_usd: List[float] = []

    for ex in test_set:
        time.sleep(3)
        logging.info(f"Evaluating model {model} on id={ex.get('id')}")
        user_prompt = ex["input"]

        t0 = time.perf_counter()
        response = get_gpt_response(model, system_prompt, str(user_prompt))
        t1 = time.perf_counter()
        latency_ms = (t1 - t0) * 1000.0
        latencies_ms.append(latency_ms)

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

        parsed = parse_gpt_assign_portion_classes_response(response.output_text)

        metrics = _evaluate_example(ex, parsed)

        results.append({
            "id": ex.get("id"),
            "input": user_prompt,
            "prediction": parsed,
            "ground_truth": ex.get("output"),
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_prompt_tokens": cached_prompt_tokens,
            },
            "cost": {"usd_estimate": cost_usd},
            "metrics": {
                **metrics,
                "latency_ms": latency_ms,
            },
        })

        sum_class_acc += metrics["class_accuracy"]
        sum_conf_mae += metrics["confidence_mae"]
        sum_invalid_rate += metrics["invalid_class_rate"]
        sum_missing_rate += metrics["missing_item_rate"]
        sum_extra_rate += metrics["extra_item_rate"]

    n = max(len(test_set), 1)

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
            "class_accuracy": sum_class_acc / n,
            "confidence_mae": sum_conf_mae / n,
            "invalid_class_rate": sum_invalid_rate / n,
            "missing_item_rate": sum_missing_rate / n,
            "extra_item_rate": sum_extra_rate / n,
            "latency_ms": latency_summary,
            "tokens": token_summary,
            "cost": cost_summary,
            "number_of_tests": n,
        }
    })

    with open(results_path, "w") as f:
        json.dump(results, f, indent=4)


def compare_models(models: list, results_paths: list, model_comparison_path: str, number_of_tests: int):
    logging.info(f"Comparing models: {models}")
    with open(model_comparison_path, "w") as comparison_file:
        comparison_file.write(f"Model Comparison Results with {number_of_tests} tests:\n\n")

        for model, path in zip(models, results_paths):
            with open(path, "r") as f:
                results = json.load(f)
                avg = results[-1]["average_metrics"]

            comparison_file.write(f"Model: {model}\n")
            comparison_file.write(f"Avg Class Accuracy: {avg['class_accuracy']:.4f}\n")
            comparison_file.write(f"Avg Confidence MAE: {avg['confidence_mae']:.4f}\n")
            comparison_file.write(f"Avg Invalid Class Rate: {avg['invalid_class_rate']:.4f}\n")
            comparison_file.write(f"Avg Missing Item Rate: {avg['missing_item_rate']:.4f}\n")
            comparison_file.write(f"Avg Extra Item Rate: {avg['extra_item_rate']:.4f}\n")

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

            # print summary to stdout too
            print(f"Model: {model}")
            print(f"Avg Class Accuracy: {avg['class_accuracy']:.4f}")
            print(f"Avg Confidence MAE: {avg['confidence_mae']:.4f}")
            print(f"Avg Invalid Class Rate: {avg['invalid_class_rate']:.4f}")
            print(f"Avg Missing Item Rate: {avg['missing_item_rate']:.4f}")
            print(f"Avg Extra Item Rate: {avg['extra_item_rate']:.4f}")

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
    # System prompt should instruct the model to do assign_portion_classes and output strict JSON.
    system_prompt = get_prompt(
        "prompts/system_prompts/assign_portion_classes/assign_portion_classes_v1.txt",
        "prompts/few_shot_examples/assign_portion_classes_examples.json",
        False
    )

    with open("prompts/test_sets/assign_portion_classes_subtests.json", "r") as f:
        test_set = json.load(f)

    models = ["gpt-4o", "gpt-4o-mini", "gpt-4.1-nano"]

    for model in models:
        evaluate_model(
            model,
            system_prompt,
            test_set["examples"],
            f"model_selection/models/assign_portion_classes/{model}_assign_portion_classes_test_results.json",
        )

    compare_models(
        models,
        [f"model_selection/models/assign_portion_classes/{model}_assign_portion_classes_test_results.json" for model in models],
        "model_selection/models/assign_portion_classes/model_comparison.txt",
        number_of_tests=len(test_set["examples"]),
    )
