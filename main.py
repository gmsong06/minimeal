from utils.model import get_gpt_meal_conversion, parse_gpt_meal_conversion_response
from utils.prompt import get_prompt

if __name__ == "__main__":
    system_prompt = get_prompt(
        "prompts/system_prompts/meal_conversion/meal_conversion_v3.txt",
        "prompts/few_shot_examples/meal_conversion_examples.json"
    )

    user_prompt = "pbj"

    response = get_gpt_meal_conversion("gpt-4.1-nano", system_prompt, user_prompt)

    ingredients, confidence_score = parse_gpt_meal_conversion_response(response.output_text).values()

    print(f"Ingredients:\n{ingredients}\n")
    print(f"Confidence Score: {confidence_score}\n")