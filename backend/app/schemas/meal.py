from typing import Any

from pydantic import BaseModel, Field

DEFAULT_TIMEZONE = "America/New_York"


class HealthResponse(BaseModel):
    status: str


class USDACandidate(BaseModel):
    description: str
    fdcId: int


class FoodItem(BaseModel):
    name: str
    portion_class: str | None = None
    confidence: float | None = None
    usda_candidates: list[USDACandidate] = Field(default_factory=list)


class ProcessedMeal(BaseModel):
    meal_description: str | None = None
    foods: list[FoodItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    confidence_score: float | None = None


class MealLogEntry(BaseModel):
    meal_id: str
    time_stamp: str
    meal_description: str | None = None
    foods: list[FoodItem] = Field(default_factory=list)
    nutrient_exposure: dict[str, float]


class DailySummaryItem(BaseModel):
    nutrient_id: int
    name: str
    percent_dv_so_far: float
    status: str


class MealCreateRequest(BaseModel):
    user_meal: str
    meal_conversion_model: str = "gpt-4.1-nano"
    assign_portion_classes_model: str = "gpt-4.1-nano"
    tz_name: str = DEFAULT_TIMEZONE


class MealCreateResponse(BaseModel):
    processed_meal: dict[str, Any]
    nutrient_exposure: dict[str, float]
    log_entry: MealLogEntry


class DailySummaryResponse(BaseModel):
    date: str
    timezone: str
    nutrient_totals: dict[str, float]
    formatted_summary: list[DailySummaryItem]