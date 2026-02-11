from dotenv import load_dotenv
from openai import OpenAI
import json
import re
from typing import Any, Dict, List, Optional

load_dotenv()

client = OpenAI()

_FENCED_JSON_RE = re.compile(
    r"(?is)```(?:json)?\s*({.*?})\s*```"
)

def _extract_json_object(text: str) -> Dict[str, Any]:
    m = _FENCED_JSON_RE.search(text)
    if m:
        return json.loads(m.group(1))

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in the response.")

    depth = 0
    end: Optional[int] = None
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise ValueError("Found '{' but could not find a matching '}' for JSON object.")

    candidate = text[start:end]
    return json.loads(candidate)

def parse_gpt_meal_conversion_response(text: str) -> Dict[str, Any]:
    """
    Returns:
      {
        "reasoning": str,
        "ingredients": List[str]
        "confidence_score": int
      }
    Raises ValueError if ingredients can't be found.
    """

    payload = _extract_json_object(text)

    ingredients = payload.get("ingredients", None)
    if not isinstance(ingredients, list) or not all(isinstance(x, str) for x in ingredients):
        raise ValueError("Parsed JSON does not contain a valid 'ingredients' list.")

    return {
        "ingredients": ingredients,
        "confidence_score": payload.get("confidence_score"),
    }

def get_gpt_meal_conversion(model: str, system_prompt: str, user_prompt: str) -> str:
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    )
    return response
