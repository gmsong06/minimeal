from dotenv import load_dotenv
from openai import OpenAI

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

if __name__ == "__main__":
    prompt = "broccoli cheddar soup wiht buttr chicken and garlic cheese naan and potato pierogis"
    answer = ask_llm(prompt)
    print(f"Answer: {answer}")