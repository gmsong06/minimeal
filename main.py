from utils.model import (
    get_gpt_response, 
    parse_gpt_meal_conversion_response, 
    parse_gpt_assign_portion_classes_response,
    parse_gpt_choose_candidates_response
)

from utils.prompt import get_prompt
import json
import copy
import config

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
        user_prompt
    )
    
    ingredients, confidence_score = parse_gpt_meal_conversion_response(meal_conversion_response.output_text).values()

    # Assemble input to portion classes model
    portion_classes_input = {}
    portion_classes_input["meal_desc"] = user_meal
    portion_classes_input["foods"] = ingredients

    assign_portion_classes_response = get_gpt_response(assign_portion_classes_model, assign_portion_classes_system_prompt, str(portion_classes_input))

    return parse_gpt_assign_portion_classes_response(assign_portion_classes_response.output_text)

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

def determine_significant_exposure(processed_meal: str):
    for food in processed_meal["foods"]:
        significant_exposure = [] # A list of nutrient ids of nutrients the user has been exposed to from the meal
        portion_class = food["portion_class"]

        for nutrient in food["essential_nutrients"]:
            # Per 100g
            unit = nutrient["nutrient"]["unitName"]
            amt = nutrient["amount"]

if __name__ == "__main__":
    user_prompt = "grilled chicken w tomato soup"

    processed_meal = process_input(user_prompt, "gpt-4.1-nano", "gpt-4.1-nano")

    add_usda_candidates(processed_meal)
    input_to_choose_candidate = build_choose_candidate_input(processed_meal)
    
    chosen_candidates = get_chosen_candidates(str(input_to_choose_candidate), "gpt-4.1-nano")

    remove_other_candidates(processed_meal, chosen_candidates)
    extract_essential_nutrients(processed_meal)

    with open("processed_meal.json", "w") as f:
        json.dump(processed_meal, f)

    # print(processed_meal)