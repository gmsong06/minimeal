from typing import Any, Dict, List

from pydantic import BaseModel

DEFAULT_TIMEZONE = "America/New_York"


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