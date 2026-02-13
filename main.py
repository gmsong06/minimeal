from utils.model import get_gpt_response, parse_gpt_meal_conversion_response, parse_gpt_assign_portion_classes_response
from utils.prompt import get_prompt

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

if __name__ == "__main__":
    user_prompt = "roasted edamame"

    processed_meal = process_input(user_prompt, "gpt-4.1-nano", "gpt-4.1-nano")
    print(processed_meal)