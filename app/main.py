from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
from utils.model import (
    get_gpt_response,
    parse_gpt_meal_conversion_response,
    parse_gpt_assign_portion_classes_response,
)
from utils.nutrients import (
    get_nutrient_exposure,
    classify_day_contribution,
    load_usda_foods,
)
from utils.prompt import get_prompt
import json
import ulid
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import config

app = FastAPI(title="Minimeal")

MEAL_LOG_PATH = Path("meal_log.json")
DEFAULT_TIMEZONE = "America/New_York"


# -----------------------------
# Pydantic request/response models
# -----------------------------
class MealCreateRequest(BaseModel):
    user_meal: str
    meal_conversion_model: str = "gpt-4.1-nano"
    assign_portion_classes_model: str = "gpt-4.1-nano"
    tz_name: str = DEFAULT_TIMEZONE


class MealCreateResponse(BaseModel):
    processed_meal: Dict[str, Any]
    nutrient_exposure: Dict[str, float]
    log_entry: Dict[str, Any]


class DailySummaryResponse(BaseModel):
    date: str
    timezone: str
    nutrient_totals: Dict[str, float]
    formatted_summary: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    status: str


# -----------------------------
# Startup
# -----------------------------
@app.on_event("startup")
def startup_event():
    if not MEAL_LOG_PATH.exists():
        MEAL_LOG_PATH.write_text("[]", encoding="utf-8")

    load_usda_foods()


# -----------------------------
# Helpers
# -----------------------------
def normalize_nutrient_exposure(nutrient_exposure: dict) -> dict[str, float]:
    return {str(k): float(v) for k, v in nutrient_exposure.items()}


# -----------------------------
# Core logic
# -----------------------------
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
                "status": classify_day_contribution(pct),
            }
        )

    return summary


def log_meal(processed_meal: dict, nutrient_exposure: dict, time_stamp: datetime):
    if time_stamp.tzinfo is None:
        time_stamp = time_stamp.replace(tzinfo=ZoneInfo("UTC"))

    nutrient_exposure = normalize_nutrient_exposure(nutrient_exposure)

    log_entry = {
        "meal_id": str(ulid.ulid()),
        "time_stamp": time_stamp.isoformat(),
        "meal_description": processed_meal.get("meal_description"),
        "foods": processed_meal.get("foods", []),
        "nutrient_exposure": nutrient_exposure,
    }

    data = get_meal_log(MEAL_LOG_PATH)
    data.append(log_entry)
    save_meal_log(MEAL_LOG_PATH, data)

    return log_entry


# -----------------------------
# API routes
# -----------------------------
@app.get("/", response_model=HealthResponse)
def root():
    return {"status": "Meal Logger API is running"}


@app.post("/meals", response_model=MealCreateResponse)
def create_meal(request: MealCreateRequest):
    try:
        processed_meal = process_input(
            request.user_meal,
            request.meal_conversion_model,
            request.assign_portion_classes_model,
        )

        raw_nutrient_exposure = get_nutrient_exposure(processed_meal)
        nutrient_exposure = normalize_nutrient_exposure(raw_nutrient_exposure)

        now = datetime.now(ZoneInfo(request.tz_name))
        log_entry = log_meal(processed_meal, nutrient_exposure, now)

        return {
            "processed_meal": processed_meal,
            "nutrient_exposure": nutrient_exposure,
            "log_entry": log_entry,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/meals")
def read_meals():
    try:
        return get_meal_log(MEAL_LOG_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summary/today", response_model=DailySummaryResponse)
def get_today_summary(tz_name: str = DEFAULT_TIMEZONE):
    try:
        now = datetime.now(ZoneInfo(tz_name))
        meal_log = get_meal_log(MEAL_LOG_PATH)
        totals = get_so_far_today(meal_log, now, tz_name)
        formatted_summary = format_daily_summary(totals)

        return {
            "date": now.date().isoformat(),
            "timezone": tz_name,
            "nutrient_totals": totals,
            "formatted_summary": formatted_summary,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))