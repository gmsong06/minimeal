from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

def ask_llm(prompt: str) -> str:
    response = client.responses.create(
        model="gpt-5.2",
        input=prompt
    )
    return response.output_text

if __name__ == "__main__":
    prompt = "What is the capital of France?"
    answer = ask_llm(prompt)
    print(f"Answer: {answer}")