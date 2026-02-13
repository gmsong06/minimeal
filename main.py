from utils.model import get_gpt_response, parse_gpt_meal_conversion_response, parse_gpt_assign_portion_classes_response
from utils.prompt import get_prompt
import json

def process_input(user_meal: str, meal_conversion_model: str, assign_portion_classes_model: str):
    meal_conversion_system_prompt = get_prompt(
        "prompts/system_prompts/meal_conversion/meal_conversion_v3.txt",
        "prompts/few_shot_examples/meal_conversion_examples.json",
        True
    )

    assign_portion_classes_system_prompt = get_prompt(
        "prompts/system_prompts/assign_portion_classes/assign_portion_classes_v2.txt",
        "prompts/few_shot_examples/assign_portion_classes_examples.json",
        False
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
    

if __name__ == "__main__":
    user_prompt = "grille cheese w broccoli and tomato soup"

    processed_meal = process_input(user_prompt, "gpt-4.1-nano", "gpt-4.1-nano")
    print(processed_meal)
    add_usda_candidates(processed_meal)
    print(processed_meal["foods"][0]["usda_candidates"])