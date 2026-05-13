from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Header, Request

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
    build_log_entry,
    compact_processed_meal,
    format_daily_summary,
    get_so_far_today,
    normalize_nutrient_exposure,
    process_input,
)
from ..services.storage import get_storage
from ..utils.nutrients import get_nutrient_exposure
from ..utils.rate_limit import get_client_rate_limit_key, rate_limiter

router = APIRouter()
storage = get_storage()


def _resolve_username(x_minimeal_username: str | None) -> str:
    if not x_minimeal_username:
        raise HTTPException(
            status_code=401,
            detail="Missing X-Minimeal-Username header. Login first.",
        )

    username = x_minimeal_username.strip().lower()
    if not storage.user_exists(username):
        raise HTTPException(status_code=401, detail="Unknown account.")
    return username


def _parse_request_timestamp(
    request_timestamp: str | None, tz_name: str
) -> datetime:
    if not request_timestamp:
        return datetime.now(ZoneInfo(tz_name))

    cleaned_timestamp = request_timestamp.strip()
    if cleaned_timestamp.endswith("Z"):
        cleaned_timestamp = f"{cleaned_timestamp[:-1]}+00:00"

    parsed = datetime.fromisoformat(cleaned_timestamp)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(tz_name))
    return parsed.astimezone(ZoneInfo(tz_name))


@router.get("/", response_model=HealthResponse)
def root():
    return HealthResponse(status="Minimeal is running")


@router.get("/healthz", response_model=HealthResponse)
def healthcheck():
    return HealthResponse(status="ok")


@router.post("/meals", response_model=MealCreateResponse)
def create_meal(
    request: MealCreateRequest,
    http_request: Request,
    x_minimeal_username: str | None = Header(
        default=None, alias="X-Minimeal-Username"
    ),
):
    try:
        username = _resolve_username(x_minimeal_username)
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

        try:
            raw_nutrient_exposure = get_nutrient_exposure(processed_meal)
        except Exception as nutrient_exc:
            processed_meal.setdefault("notes", []).append(
                f"nutrient_pipeline_failed: {nutrient_exc}"
            )
            raw_nutrient_exposure = {}
        nutrient_exposure = normalize_nutrient_exposure(raw_nutrient_exposure)

        time_stamp = _parse_request_timestamp(request.time_stamp, request.tz_name)
        log_entry = build_log_entry(
            processed_meal,
            nutrient_exposure,
            time_stamp,
            excluded_from_daily_summary=request.excluded_from_daily_summary,
        )
        storage.save_meal(username, log_entry)
        response_processed_meal = compact_processed_meal(processed_meal)

        return MealCreateResponse(
            processed_meal=response_processed_meal,
            nutrient_exposure=nutrient_exposure,
            log_entry=MealLogEntry(**log_entry),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meals", response_model=list[MealLogEntry])
def read_meals(
    x_minimeal_username: str | None = Header(
        default=None, alias="X-Minimeal-Username"
    ),
):
    try:
        username = _resolve_username(x_minimeal_username)
        meal_log = storage.get_meals(username)
        return [MealLogEntry(**entry) for entry in meal_log]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/meals/{meal_id}")
def remove_meal(
    meal_id: str,
    x_minimeal_username: str | None = Header(
        default=None, alias="X-Minimeal-Username"
    ),
):
    try:
        username = _resolve_username(x_minimeal_username)
        deleted = storage.delete_meal(username, meal_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Meal not found")

        return {"status": "deleted", "meal_id": meal_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/meals/{meal_id}/exclude", response_model=MealLogEntry)
def update_meal_exclusion(
    meal_id: str,
    excluded_from_daily_summary: bool,
    x_minimeal_username: str | None = Header(
        default=None, alias="X-Minimeal-Username"
    ),
):
    try:
        username = _resolve_username(x_minimeal_username)
        updated_meal = storage.set_meal_excluded_status(
            username, meal_id, excluded_from_daily_summary
        )

        if updated_meal is None:
            raise HTTPException(status_code=404, detail="Meal not found")

        return MealLogEntry(**updated_meal)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/today", response_model=DailySummaryResponse)
def get_today_summary(
    tz_name: str = DEFAULT_TIMEZONE,
    x_minimeal_username: str | None = Header(
        default=None, alias="X-Minimeal-Username"
    ),
):
    try:
        username = _resolve_username(x_minimeal_username)
        now = datetime.now(ZoneInfo(tz_name))
        meal_log = storage.get_meals(username)
        totals = get_so_far_today(meal_log, now, tz_name)
        formatted_summary = format_daily_summary(totals)

        return DailySummaryResponse(
            date=now.date().isoformat(),
            timezone=tz_name,
            nutrient_totals=totals,
            formatted_summary=formatted_summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
