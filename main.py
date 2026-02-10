from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

client = OpenAI()

def ask_llm(user_prompt: str) -> str:
    response = client.responses.create(
        model="gpt-5.2",
        prompt={
            "id": "pmpt_6986a5d02164819084be45615e1df3d408d1063967f88be9",
            "version": "2"
        },
        input=user_prompt
    )
    return response.output_text

def get_prompt(base_prompt_path: str) -> str:
    # Read the base prompt from the file
    with open(base_prompt_path, "r", encoding="utf-8") as f:
        base_prompt = f.read()

    # Add in examples


if __name__ == "__main__":
    # prompt = "broccoli cheddar soup wiht buttr chicken and garlic cheese naan and potato pierogis"
    # answer = ask_llm(prompt)
    # print(f"Answer: {answer}")

    get_prompt("prompts/system_prompts/meal_conversion_v2.txt")