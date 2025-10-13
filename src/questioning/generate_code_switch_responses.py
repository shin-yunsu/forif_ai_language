import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple

# Load environment variables
load_dotenv()

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Model configurations
MODELS = {
    "qwen_7b": "qwen/qwen-2.5-7b-instruct",
    "qwen_72b": "qwen/qwen-2.5-72b-instruct"
}

def get_model_response(question: str, model_name: str, model_key: str) -> Tuple[str, str, str]:
    """Get response from OpenAI model for given question"""
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": question
                }
            ],
            temperature=0.7
        )
        response = completion.choices[0].message.content
        return (model_key, question, response)
    except Exception as e:
        print(f"Error getting response for '{question}' with {model_name}: {e}")
        return (model_key, question, "")

def process_code_switch_data(input_file: str, output_file: str, batch_size: int = 50, max_workers: int = 10):
    """Process code-switched data and generate model responses for each case using multiprocessing"""

    # Load existing progress if available
    processed_ids = set()
    results = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
                processed_ids = {item['id'] for item in results}
                print(f"Resuming from checkpoint: {len(processed_ids)} items already processed")
        except Exception as e:
            print(f"Could not load existing progress: {e}")

    # Load input data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Limit to batch_size
    data = data[:batch_size]
    
    # Filter out already processed items
    data = [item for item in data if item['id'] not in processed_ids]
    print(f"Processing {len(data)} remaining items (batch size: {batch_size}, already completed: {len(processed_ids)})")

    for idx, item in enumerate(data):
        print(f"\nProcessing item {idx + 1}/{len(data)}: ID {item['id']}")

        result_item = {
            "id": item["id"],
            "original_ko": item["original_ko"],
            "original_en": item["original_en"],
            "code_switched_versions": item["code_switched_versions"],
            "responses": {}
        }

        # Prepare tasks for parallel execution
        tasks = []
        for case, question in item["code_switched_versions"].items():
            for model_key, model_name in MODELS.items():
                tasks.append((case, question, model_key, model_name))

        # Execute tasks in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(get_model_response, question, model_name, model_key): (case, model_key)
                for case, question, model_key, model_name in tasks
            }

            for future in as_completed(futures):
                case, expected_model_key = futures[future]
                try:
                    model_key, question, response = future.result()

                    # Initialize case dict if not exists
                    if case not in result_item["responses"]:
                        result_item["responses"][case] = {}

                    result_item["responses"][case][model_key] = response
                    print(f"  ✓ {case} - {model_key}: {response[:60]}...")
                except Exception as e:
                    print(f"  ✗ {case} - {expected_model_key}: Error - {e}")

        results.append(result_item)
        
        # Save progress after each item
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  💾 Progress saved ({len(results)} items completed)")

    # Final save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nProcessing complete! Results saved to {output_file}")

if __name__ == "__main__":
    input_file = "data/outputs/code_switched_data_1.json"
    output_file = "data/outputs/code_switched_responses.json"

    process_code_switch_data(input_file, output_file, batch_size=50, max_workers=10)
