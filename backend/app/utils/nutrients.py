import json
import copy
from pathlib import Path

from .. import config
from .model import (
    get_gpt_response,
    parse_gpt_choose_candidates_response
)
from .prompt import get_prompt
from rapidfuzz import fuzz
from .FoodSearcher import FoodSearcher

FOUNDATION_FOODS = []
LEGACY_FOODS = []
BRANDED_FOODS = []
USDA_SEARCHER = None
APP_DIR = Path(__file__).resolve().parents[1]
USDA_DIR = APP_DIR / "usda"

def load_usda_foods():
    global FOUNDATION_FOODS
    global LEGACY_FOODS
    global BRANDED_FOODS
    global USDA_SEARCHER
    
    with (USDA_DIR / "USDA_Foundation_Foods.json").open("r", encoding="utf-8") as file:
        FOUNDATION_FOODS = json.load(file)["FoundationFoods"]

    with (USDA_DIR / "USDA_SR_Legacy_Foods.json").open("r", encoding="utf-8") as file:
        LEGACY_FOODS = json.load(file)["SRLegacyFoods"]

    # with (USDA_DIR / "USDA_Branded_Foods.json").open("r", encoding="utf-8") as file:
    #     BRANDED_FOODS = json.load(file)["BrandedFoods"]
    USDA_SEARCHER = FoodSearcher(FOUNDATION_FOODS, LEGACY_FOODS, BRANDED_FOODS)

def get_foundation_foods(food: str, threshold=70):

    # matches = []

    # for foundation_food in FOUNDATION_FOODS:
    #     desc = foundation_food["description"]
    #     score = fuzz.partial_ratio(food.lower(), desc.lower())

    #     if score >= threshold:
    #         matches.append((score, foundation_food))

    # matches.sort(reverse=True, key=lambda x: x[0])
    # return [m[1] for m in matches]
    if USDA_SEARCHER is None:
        load_usda_foods()

    return USDA_SEARCHER.get_foundation_foods(food, k=5, semantic_k=20)


def get_legacy_foods(food: str, threshold=70):
    # matches = []

    # for legacy_food in LEGACY_FOODS:
    #     desc = legacy_food["description"]
    #     score = fuzz.partial_ratio(food.lower(), desc.lower())

    #     if score >= threshold:
    #         matches.append((score, legacy_food))

    # matches.sort(reverse=True, key=lambda x: x[0])
    # return [m[1] for m in matches]
    
    pass

def get_branded_foods(food: str, max_results: int = 5):
    food_lower = food.lower()
    counter = 0
    results = []
    for branded_food in BRANDED_FOODS:
        if food_lower in branded_food["description"].lower():
            results.append(branded_food)
            counter += 1
            if counter >= max_results:
                break
    
    return results


def add_usda_candidates(processed_meal: dict):
    if USDA_SEARCHER is None:
        load_usda_foods()

    for food in processed_meal["foods"]:
        name = food["name"]

        foundation_candidates = USDA_SEARCHER.get_foundation_foods(
            name, k=5, semantic_k=20
        )
        legacy_candidates = USDA_SEARCHER.get_legacy_foods(
            name, k=5, semantic_k=20
        )
        deduped_candidates = []
        seen_fdc_ids = set()
        for candidate in foundation_candidates + legacy_candidates:
            fdc_id = candidate.get("fdcId")
            if fdc_id in seen_fdc_ids:
                continue
            seen_fdc_ids.add(fdc_id)
            deduped_candidates.append(candidate)

        # if len(candidates) == 0:
        #     candidates = get_legacy_foods(name)

        food["usda_candidates"] = deduped_candidates
        print(f"For {name}, USDA found {len(deduped_candidates)} candidates.")
        

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
    print("Input to choose candidate model:")
    print(input_to_choose_candidate)
    chosen_candidates = get_chosen_candidates(str(input_to_choose_candidate), "gpt-4.1-nano")
    print("Chosen candidates:", chosen_candidates)
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
