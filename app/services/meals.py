def process_input(user_meal: str, meal_conversion_model: str, assign_portion_classes_model: str):
    meal_conversion_system_prompt = get_prompt(
        "prompts/system_prompts/meal_conversion/meal_conversion_v3.txt",
        "prompts/few_shot_examples/meal_conversion_examples.json",
        want_reasoning=True
    )

    assign_portion_classes_system_prompt = get_prompt(
        "prompts/system_prompts/assign_portion_classes/assign_portion_classes_v2.txt",
        "prompts/few_shot_examples/assign_portion_classes_examples.json",
        want_reasoning=False
    )

    meal_conversion_response = get_gpt_response(
        meal_conversion_model, 
        meal_conversion_system_prompt, 
        user_meal
    )
    
    ingredients, confidence_score = parse_gpt_meal_conversion_response(meal_conversion_response.output_text).values()

    # Assemble input to portion classes model
    portion_classes_input = {}
    portion_classes_input["meal_desc"] = user_meal
    portion_classes_input["foods"] = ingredients

    assign_portion_classes_response = get_gpt_response(assign_portion_classes_model, assign_portion_classes_system_prompt, str(portion_classes_input))

    return parse_gpt_assign_portion_classes_response(assign_portion_classes_response.output_text)


def get_meal_log(meal_log_path: str):
    with open(meal_log_path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []
    return data

def get_local_day_bounds(target_dt: datetime, tz_name: str):
    tz = ZoneInfo(tz_name)
    local_dt = target_dt.astimezone(tz)
    day_start = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    return day_start, day_end


def sum_nutrients_for_day(meal_log, target_dt, tz_name):
    day_start, day_end = get_local_day_bounds(target_dt, tz_name)
    totals = defaultdict(float)

    for meal in meal_log:
        eaten_at = datetime.fromisoformat(meal["time_stamp"]).astimezone(ZoneInfo(tz_name))
        if day_start <= eaten_at < day_end:
            for nutrient_id, pct_dv in meal["nutrient_exposure"].items():
                totals[nutrient_id] += pct_dv

    return dict(totals)

def get_so_far_today(meal_logs, user_id, now, tz_name):
    return sum_nutrients_for_day(meal_logs, user_id, now, tz_name)

def format_daily_summary(daily_totals):
    summary = []

    for nutrient_id, pct in sorted(daily_totals.items(), key=lambda x: x[1], reverse=True):
        summary.append({
            "nutrient_id": nutrient_id,
            "name": config.NUTRIENT_ID_TO_NAME.get(int(nutrient_id), str(nutrient_id)),
            "percent_dv_so_far": round(pct, 1),
            "status": classify_day_contribution(pct),
        })

    return summary

def log_meal(processed_meal: dict, nutrient_exposure: dict, time_stamp: datetime):
    log_entry = {
        "meal_id": str(ulid.ulid()),
        "time_stamp": time_stamp.isoformat(),
        "meal_description": processed_meal["meal_description"],
        "foods": processed_meal["foods"],
        "nutrient_exposure": nutrient_exposure
    }

    file_path = "meal_log.json"

    with open(file_path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []

    # Append new entry
    data.append(log_entry)

    # Write back to file
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)