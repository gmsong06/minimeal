import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import ulid

from .. import config
from ..utils.model import (
    get_gpt_response,
    parse_gpt_assign_portion_classes_response,
    parse_gpt_meal_conversion_response,
)
from ..utils.nutrients import classify_day_contribution, load_usda_foods
from ..utils.prompt import get_prompt

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MEAL_LOG_PATH = BACKEND_ROOT / "meal_log.json"
DEFAULT_TIMEZONE = "America/New_York"


def initialize_app_data():
    if not MEAL_LOG_PATH.exists():
        MEAL_LOG_PATH.write_text("[]", encoding="utf-8")


def normalize_nutrient_exposure(nutrient_exposure: dict) -> dict[str, float]:
    return {str(k): float(v) for k, v in nutrient_exposure.items()}


def process_input(
    user_meal: str,
    meal_conversion_model: str,
    assign_portion_classes_model: str,
):
    meal_conversion_system_prompt = get_prompt(
        "prompts/system_prompts/meal_conversion/meal_conversion_v3.txt",
        "prompts/few_shot_examples/meal_conversion_examples.json",
        want_reasoning=True,
    )

    assign_portion_classes_system_prompt = get_prompt(
        "prompts/system_prompts/assign_portion_classes/assign_portion_classes_v2.txt",
        "prompts/few_shot_examples/assign_portion_classes_examples.json",
        want_reasoning=False,
    )

    meal_conversion_response = get_gpt_response(
        meal_conversion_model,
        meal_conversion_system_prompt,
        user_meal,
    )

    parsed_meal = parse_gpt_meal_conversion_response(
        meal_conversion_response.output_text
    )

    ingredients = parsed_meal.get("ingredients")
    confidence_score = parsed_meal.get("confidence_score")

    if ingredients is None:
        raise ValueError("Could not parse ingredients from meal conversion response.")

    portion_classes_input = {
        "meal_desc": user_meal,
        "foods": ingredients,
    }

    assign_portion_classes_response = get_gpt_response(
        assign_portion_classes_model,
        assign_portion_classes_system_prompt,
        str(portion_classes_input),
    )

    processed_meal = parse_gpt_assign_portion_classes_response(
        assign_portion_classes_response.output_text
    )

    if isinstance(processed_meal, dict) and confidence_score is not None:
        processed_meal["confidence_score"] = confidence_score

    return processed_meal


def get_meal_log(meal_log_path: str | Path):
    meal_log_path = Path(meal_log_path)

    if not meal_log_path.exists():
        return []

    with open(meal_log_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []

    return data


def save_meal_log(meal_log_path: str | Path, data: list):
    meal_log_path = Path(meal_log_path)
    with open(meal_log_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def delete_meal(meal_log_path: str | Path, meal_id: str) -> bool:
    meal_log_path = Path(meal_log_path)
    meal_log = get_meal_log(meal_log_path)
    filtered_meals = [
        meal for meal in meal_log if str(meal.get("meal_id")) != meal_id
    ]

    if len(filtered_meals) == len(meal_log):
        return False

    save_meal_log(meal_log_path, filtered_meals)
    return True


def set_meal_excluded_status(
    meal_log_path: str | Path, meal_id: str, excluded_from_daily_summary: bool
):
    meal_log_path = Path(meal_log_path)
    meal_log = get_meal_log(meal_log_path)

    for meal in meal_log:
        if str(meal.get("meal_id")) != meal_id:
            continue

        meal["excluded_from_daily_summary"] = excluded_from_daily_summary
        save_meal_log(meal_log_path, meal_log)
        return meal

    return None


def get_local_day_bounds(target_dt: datetime, tz_name: str):
    tz = ZoneInfo(tz_name)

    if target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=ZoneInfo("UTC"))

    local_dt = target_dt.astimezone(tz)
    day_start = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    return day_start, day_end


def sum_nutrients_for_day(meal_log, target_dt, tz_name):
    day_start, day_end = get_local_day_bounds(target_dt, tz_name)
    totals = defaultdict(float)

    for meal in meal_log:
        if meal.get("excluded_from_daily_summary", False):
            continue

        try:
            eaten_at = datetime.fromisoformat(meal["time_stamp"]).astimezone(
                ZoneInfo(tz_name)
            )
        except Exception:
            continue

        if day_start <= eaten_at < day_end:
            for nutrient_id, pct_dv in meal.get("nutrient_exposure", {}).items():
                totals[str(nutrient_id)] += float(pct_dv)

    return dict(totals)


def get_so_far_today(meal_logs, now, tz_name):
    return sum_nutrients_for_day(meal_logs, now, tz_name)


def format_daily_summary(daily_totals):
    summary = []

    for nutrient_id, pct in sorted(
        daily_totals.items(), key=lambda x: x[1], reverse=True
    ):
        nutrient_id_int = int(nutrient_id)
        summary.append(
            {
                "nutrient_id": nutrient_id_int,
                "name": config.NUTRIENT_ID_TO_NAME.get(
                    nutrient_id_int, str(nutrient_id_int)
                ),
                "percent_dv_so_far": round(pct, 1),
                "status": classify_day_contribution(pct, nutrient_id_int),
            }
        )

    return summary


def log_meal(
    processed_meal: dict,
    nutrient_exposure: dict,
    time_stamp: datetime,
    excluded_from_daily_summary: bool = False,
):
    if time_stamp.tzinfo is None:
        time_stamp = time_stamp.replace(tzinfo=ZoneInfo("UTC"))

    nutrient_exposure = normalize_nutrient_exposure(nutrient_exposure)

    log_entry = {
        "meal_id": str(ulid.ulid()),
        "time_stamp": time_stamp.isoformat(),
        "meal_description": processed_meal.get("meal_description"),
        "foods": processed_meal.get("foods", []),
        "nutrient_exposure": nutrient_exposure,
        "excluded_from_daily_summary": excluded_from_daily_summary,
    }

    data = get_meal_log(MEAL_LOG_PATH)
    data.append(log_entry)
    save_meal_log(MEAL_LOG_PATH, data)

    return log_entry
