import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Model configurations
MODELS = {
    "qwen_72b": "qwen/qwen-2.5-72b-instruct",
    "qwen_7b": "qwen/qwen-2.5-7b-instruct"
}

def get_model_response(text: str, model_name: str) -> str:
    """Get response from OpenRouter model for given text"""
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": text
                }
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error getting response for '{text}' with {model_name}: {e}")
        return ""

def process_typo_data(input_file: str, output_file: str, batch_size: int = 5):
    """Process typo data and generate model responses"""

    # Load input data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Limit to batch_size
    data = data[:batch_size]
    print(f"Processing {len(data)} items (batch size: {batch_size})")

    results = []

    for idx, item in enumerate(data):
        print(f"Processing item {idx + 1}/{len(data)}: ID {item['id']}")

        result_item = {
            "original": item["original"],
            "id": item["id"],
            "responses": {}
        }

        # Get responses for original text
        print(f"  Getting responses for original text...")
        for model_key, model_name in MODELS.items():
            result_item["responses"][model_key] = get_model_response(item["original"], model_name)

        # Process each error type
        for error_type in ["substitution", "deletion", "insertion", "transposition", "spacing"]:
            if error_type in item:
                result_item[error_type] = {}

                for error_level in ["1_error", "2_errors"]:
                    if error_level in item[error_type]:
                        print(f"  Processing {error_type} - {error_level}...")

                        typo_text = item[error_type][error_level]["text"]
                        errors = item[error_type][error_level]["errors"]

                        result_item[error_type][error_level] = {
                            "text": typo_text,
                            "errors": errors,
                            "responses": {}
                        }

                        # Get responses for typo text
                        for model_key, model_name in MODELS.items():
                            result_item[error_type][error_level]["responses"][model_key] = get_model_response(typo_text, model_name)

        results.append(result_item)

    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nProcessing complete! Results saved to {output_file}")

if __name__ == "__main__":
    input_file = "data/outputs/typos_data_short.json"
    output_file = "data/outputs/typos_data_with_responses.json"

    process_typo_data(input_file, output_file)
