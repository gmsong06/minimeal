import json

def get_prompt(base_prompt_path: str, examples_path: str) -> str:
    # Get base prompt
    with open(base_prompt_path, 'r') as file:
        base_prompt = file.read()

    # Get examples
    with open(examples_path, 'r') as file:
        examples = json.load(file)

    # Add examples to base prompt 
    base_prompt += "\n\nExamples:\n\n"
    for example in examples["examples"]:
        base_prompt += f"Example {example['id']}\n\n"
        base_prompt += f"Input: {example['input']}\n"
        base_prompt += f"Reasoning: {example['reasoning']}\n"
        base_prompt += f"Output: {example['output']}\n\n"
    
    return base_prompt