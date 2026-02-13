from utils.model import get_gpt_response, parse_gpt_meal_conversion_response, parse_gpt_assign_portion_classes_response
from utils.prompt import get_prompt

if __name__ == "__main__":
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

    user_prompt = "Tuna melt on sourdough"

    meal_conversion_response = get_gpt_response("gpt-4.1-nano", meal_conversion_system_prompt, user_prompt)

    ingredients, confidence_score = parse_gpt_meal_conversion_response(meal_conversion_response.output_text).values()

    print(ingredients)

    portion_classes_input = {}
    portion_classes_input["meal_desc"] = "Chipotle chicken burrito with black beans, cilantro-lime rice, fajita veggies, and pico"
    portion_classes_input["foods"] = [
               "flour tortilla",
               "chicken",
               "black beans",
               "rice",
               "cilantro",
               "lime",
               "bell peppers",
               "onion",
               "tomatoes",
               "onion",
               "cilantro",
               "lime"
            ]
         

    assign_portion_classes_response = get_gpt_response("gpt-4o-mini", assign_portion_classes_system_prompt, str(portion_classes_input))

    print(assign_portion_classes_response.output_text)
    print(parse_gpt_assign_portion_classes_response(assign_portion_classes_response.output_text))
    # print(assign_portion_classes_system_prompt)