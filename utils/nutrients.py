import json
import copy
import config
from utils.model import (
    get_gpt_response,
    parse_gpt_choose_candidates_response
)
from utils.prompt import get_prompt

FOUNDATION_FOODS = []
BRANDED_FOODS = []

def load_usda_foods():
    global FOUNDATION_FOODS
    global BRANDED_FOODS
    
    with open("usda/USDA_Foundation_Foods.json", "r") as file:
        FOUNDATION_FOODS = json.load(file)["FoundationFoods"]

    with open("usda/USDA_Branded_Foods.json", "r") as file:
        BRANDED_FOODS = json.load(file)["BrandedFoods"]

def get_foundation_foods(food: str):
    food_lower = food.lower()
    return [
        foundation_food
        for foundation_food in FOUNDATION_FOODS
        if food_lower in foundation_food["description"].lower()
    ]

def get_branded_foods(food: str):
    food_lower = food.lower()
    return [
        branded_food
        for branded_food in BRANDED_FOODS
        if food_lower in branded_food["description"].lower()
    ]


def add_usda_candidates(processed_meal: dict):
    for food in processed_meal["foods"]:
        name = food["name"]

        candidates = get_foundation_foods(name)

        if len(candidates) == 0:
            candidates = get_branded_foods(name)

        food["usda_candidates"] = candidates
        print(f"For {name}, USDA found {len(candidates)} candidates.")
        

def build_choose_candidate_input(processed_meal: dict):
    """
    processed_meal should have already gone through add_usda_candidates
    """

    gpt_input = copy.deepcopy(processed_meal)

    for food in gpt_input["foods"]:
        simplified = []

        for c in food.get("usda_candidates", []):
            simplified.append({
                "description": c.get("description"),
                "fdcId": c.get("fdcId"),
            })

        food["usda_candidates"] = simplified
    
    return gpt_input

def get_chosen_candidates(choose_candidate_input: str, choose_candidate_model: str):
    choose_candidate_system_prompt = get_prompt(
        "prompts/system_prompts/choose_candidate/choose_candidate.txt",
        "prompts/few_shot_examples/choose_candidate_examples.json",
        want_reasoning=False
    )

    choose_candidate_response = get_gpt_response(
        choose_candidate_model, 
        choose_candidate_system_prompt, 
        choose_candidate_input
    )

    return parse_gpt_choose_candidates_response(choose_candidate_response.output_text)


def remove_other_candidates(processed_meal: str, chosen_candidates: dict):
    print("Chosen candidates from GPT:")
    print(chosen_candidates)
    for food in processed_meal["foods"]:
        chosen_candidate = {}
        for c in food["usda_candidates"]:
            if c["fdcId"] == chosen_candidates[food["name"]]:
                chosen_candidate = c
                break

        food["usda_match"] = chosen_candidate
    

def extract_essential_nutrients(processed_meal: str):
    for food in processed_meal["foods"]:
        essential_nutrients = []
        if food["usda_match"] != {}:
            for nutrient in food["usda_match"]["foodNutrients"]:
                if nutrient["nutrient"]["id"] in config.ESSENTIAL_IDS:
                    essential_nutrients.append(nutrient)

        food["essential_nutrients"] = essential_nutrients

def classify_meal_contribution(actual_dv_percent: float) -> str:
    for threshold, label in config.DV_TO_MEAL_CONTRIBUTION:
        if actual_dv_percent >= threshold:
            return label
        
def classify_day_contribution(actual_dv_percent: float) -> str:
    for threshold, label in config.DV_TO_DAY_STATUS:
        if actual_dv_percent >= threshold:
            return label

def get_nutrient_exposure(processed_meal: str):
    # Choose USDA candidate
    add_usda_candidates(processed_meal)
    input_to_choose_candidate = build_choose_candidate_input(processed_meal)
    chosen_candidates = get_chosen_candidates(str(input_to_choose_candidate), "gpt-4.1-nano")
    remove_other_candidates(processed_meal, chosen_candidates)

    # Get nutrients from the candidate
    extract_essential_nutrients(processed_meal)
    
    nutrient_exposure = {}  # nutrient_id -> total_actual_dv (%DV)

    for food in processed_meal["foods"]:

        portion_class = food["portion_class"]

        for nutrient in food["essential_nutrients"]:
            nutrient_id = nutrient["nutrient"]["id"]
            amt_per_100g = nutrient["amount"]

            dv = config.FDA_DAILY_VALUES.get(nutrient_id)
            if dv is None or dv == 0:
                continue 

            percent_dv_per_100g = (amt_per_100g / dv) * 100
            estimated_grams = config.PORTION_CLASS_GRAMS[portion_class]["default"]

            actual_dv = percent_dv_per_100g * (estimated_grams / 100)

            nutrient_exposure[nutrient_id] = nutrient_exposure.get(nutrient_id, 0.0) + actual_dv

    return nutrient_exposure
