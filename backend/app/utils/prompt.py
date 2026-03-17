import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]


def _resolve_app_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate

    return APP_DIR / candidate

def get_prompt(base_prompt_path: str, examples_path: str, want_reasoning: bool) -> str:
    # Get base prompt
    with _resolve_app_path(base_prompt_path).open("r", encoding="utf-8") as file:
        base_prompt = file.read()

    # Get examples
    with _resolve_app_path(examples_path).open("r", encoding="utf-8") as file:
        examples = json.load(file)

    # Add examples to base prompt 
    base_prompt += "\n\nExamples:\n\n"
    for example in examples["examples"]:
        base_prompt += f"Example {example['id']}\n\n"
        base_prompt += f"Input: {example['input']}\n"
        if want_reasoning:
            base_prompt += f"Reasoning: {example['reasoning']}\n"
        base_prompt += f"Output: {example['output']}\n\n"
    
    return base_prompt
