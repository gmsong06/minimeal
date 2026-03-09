import json
import copy
import config
from utils.model import (
    get_gpt_response,
    parse_gpt_choose_candidates_response
)
from utils.prompt import get_prompt

def get_foundation_foods(food: str):
    # print(f"Function received {food}.")
    candidates = []

    with open("usda/USDA_Foundation_Foods.json", "r") as file:
        foundation_foods = json.load(file)
    counter = 1
    for foundation_food in foundation_foods["FoundationFoods"]:
        # print(f'{counter}. {foundation_food["description"]}')
        if food.lower() in foundation_food["description"].lower():
            candidates.append(foundation_food)
        counter += 1
    # print()
    return candidates

def add_usda_candidates(processed_meal: dict):
    for food in processed_meal["foods"]:
        name = food["name"]
        portion_class = food["portion_class"]

        # Search for the name of the food in USDA
        # Only foundation foods for now
        candidates = get_foundation_foods(name)

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