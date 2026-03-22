from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request

from ..config import AI_RATE_LIMIT_MAX_REQUESTS, AI_RATE_LIMIT_WINDOW_SECONDS
from ..schemas.meal import (
    DailySummaryResponse,
    HealthResponse,
    MealCreateRequest,
    MealCreateResponse,
    MealLogEntry,
)
from ..services.meal_service import (
    DEFAULT_TIMEZONE,
    MEAL_LOG_PATH,
    delete_meal,
    format_daily_summary,
    get_meal_log,
    get_so_far_today,
    log_meal,
    normalize_nutrient_exposure,
    process_input,
)
from ..utils.nutrients import get_nutrient_exposure
from ..utils.rate_limit import get_client_rate_limit_key, rate_limiter

router = APIRouter()


@router.get("/", response_model=HealthResponse)
def root():
    return HealthResponse(status="Minimeal is running")


@router.get("/healthz", response_model=HealthResponse)
def healthcheck():
    return HealthResponse(status="ok")


@router.post("/meals", response_model=MealCreateResponse)
def create_meal(request: MealCreateRequest, http_request: Request):
    try:
        rate_limiter.check(
            key=get_client_rate_limit_key(http_request, scope="post_meals"),
            max_requests=AI_RATE_LIMIT_MAX_REQUESTS,
            window_seconds=AI_RATE_LIMIT_WINDOW_SECONDS,
        )

        processed_meal = process_input(
            request.user_meal,
            request.meal_conversion_model,
            request.assign_portion_classes_model,
        )

        raw_nutrient_exposure = get_nutrient_exposure(processed_meal)
        nutrient_exposure = normalize_nutrient_exposure(raw_nutrient_exposure)

        now = datetime.now(ZoneInfo(request.tz_name))
        log_entry = log_meal(processed_meal, nutrient_exposure, now)

        return MealCreateResponse(
            processed_meal=processed_meal,
            nutrient_exposure=nutrient_exposure,
            log_entry=MealLogEntry(**log_entry),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meals", response_model=list[MealLogEntry])
def read_meals():
    try:
        meal_log = get_meal_log(MEAL_LOG_PATH)
        return [MealLogEntry(**entry) for entry in meal_log]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/meals/{meal_id}")
def remove_meal(meal_id: str):
    try:
        deleted = delete_meal(MEAL_LOG_PATH, meal_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Meal not found")

        return {"status": "deleted", "meal_id": meal_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/today", response_model=DailySummaryResponse)
def get_today_summary(tz_name: str = DEFAULT_TIMEZONE):
    try:
        now = datetime.now(ZoneInfo(tz_name))
        meal_log = get_meal_log(MEAL_LOG_PATH)
        totals = get_so_far_today(meal_log, now, tz_name)
        formatted_summary = format_daily_summary(totals)

        return DailySummaryResponse(
            date=now.date().isoformat(),
            timezone=tz_name,
            nutrient_totals=totals,
            formatted_summary=formatted_summary,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
