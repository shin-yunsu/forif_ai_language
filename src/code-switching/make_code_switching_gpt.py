#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from typing import List, Dict, Tuple
from openai import OpenAI
from tqdm import tqdm
import random
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def load_mkqa_data(file_path: str) -> List[Dict[str, str]]:
    """Load MKQA data from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_code_switching_prompt(ko_text: str, en_text: str, case_type: str) -> str:
    """Create a prompt for GPT to generate code-switched text based on specific case type with few-shot examples."""

    case_prompts = {
        "Case2": f"""Generate Korean sentence with keyword-level English switching.
Replace 1-2 key nouns or verbs with English while keeping Korean sentence structure and particles.

Examples:
Korean original: 미국의 수도는 어디인가?
English original: What is the capital of the United States?
Output: 미국의 capital은 어디인가?

Korean original: 프랑스의 대통령은 누구인가?
English original: Who is the president of France?
Output: France의 대통령은 누구인가?

Korean original: 태양계에서 가장 큰 행성은 무엇인가?
English original: What is the largest planet in the solar system?
Output: solar system에서 가장 큰 planet은 무엇인가?

Now generate:
Korean original: {ko_text}
English original: {en_text}
Output: """,

        "Case3": f"""Generate a mixed structure sentence.
Use English sentence structure for the main clause but keep Korean nouns/phrases.

Examples:
Korean original: 미국의 수도는 어디인가?
English original: What is the capital of the United States?
Output: What is 미국의 수도?

Korean original: 프랑스의 대통령은 누구인가?
English original: Who is the president of France?
Output: Who is 프랑스의 대통령?

Korean original: 태양계에서 가장 큰 행성은 무엇인가?
English original: What is the largest planet in the solar system?
Output: What is 태양계에서 가장 큰 행성?

Now generate:
Korean original: {ko_text}
English original: {en_text}
Output: """,

        "Case4": f"""Generate English sentence with keyword-level Korean switching.
Use English sentence structure but keep 1-2 Korean key terms.

Examples:
Korean original: 미국의 수도는 어디인가?
English original: What is the capital of the United States?
Output: What is the 수도 of the United States?

Korean original: 프랑스의 대통령은 누구인가?
English original: Who is the president of France?
Output: Who is the 대통령 of France?

Korean original: 태양계에서 가장 큰 행성은 무엇인가?
English original: What is the largest planet in the solar system?
Output: What is the largest 행성 in the solar system?

Now generate:
Korean original: {ko_text}
English original: {en_text}
Output: """
    }

    return case_prompts[case_type]

def generate_code_switched_text(ko_text: str, en_text: str, case_type: str,
                               model: str = "gpt-4o-mini") -> str:
    """Generate code-switched text using GPT with few-shot prompting."""

    prompt = create_code_switching_prompt(ko_text, en_text, case_type)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a Korean-English bilingual speaker who naturally code-switches between languages. Follow the pattern shown in the examples exactly. Always maintain the original meaning while creating natural-sounding mixed sentences. Only output the final result without any additional explanation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent pattern following
            max_tokens=200
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error generating code-switched text: {e}")
        return ""


def save_results(results: List[Dict], output_file: str):
    """Save results to JSON file."""
    # If output_file already contains a path, use it as is
    # Otherwise, use current directory
    if os.path.dirname(output_file):
        output_path = output_file
    else:
        output_path = os.path.join(os.path.dirname(__file__) or '.', output_file)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(results)} items to {output_path}")

def validate_code_switching_ratio(text: str, target_range: Tuple[float, float]) -> bool:
    """Validate if the generated text meets the target English ratio."""
    # Simple word-based validation
    words = text.split()
    english_words = sum(1 for word in words if all(ord(c) < 128 for c in word))
    total_words = len(words)

    if total_words == 0:
        return False

    english_ratio = english_words / total_words
    min_ratio, max_ratio = target_range

    return min_ratio <= english_ratio <= max_ratio

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate code-switched Korean-English data from MKQA dataset",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--input",
        type=str,
        default="../jsons/mkqa_refined_full.json",
        help="Path to input MKQA JSON file"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="code_switched_data.json",
        help="Path to output JSON file"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        choices=["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"],
        help="OpenAI model to use for generation"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay between API calls in seconds (to avoid rate limiting)"
    )

    parser.add_argument(
        "--save-interval",
        type=int,
        default=10,
        help="Save intermediate results every N items"
    )

    parser.add_argument(
        "--threads",
        type=int,
        default=5,
        help="Number of threads for parallel processing"
    )

    return parser.parse_args()

def main():
    """Main function to orchestrate the code-switching data generation."""

    # Parse command line arguments
    args = parse_arguments()

    # Configuration from arguments
    input_file = args.input
    output_file = args.output
    model = args.model

    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it using: export OPENAI_API_KEY='your-api-key'")
        return

    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        return

    print(f"Configuration:")
    print(f"  Input file: {input_file}")
    print(f"  Output file: {output_file}")
    print(f"  Model: {model}")
    print(f"  API delay: {args.delay}s")
    print(f"  Save interval: every {args.save_interval} items")
    print(f"  Threads: {args.threads}")
    print()

    print("Loading MKQA data...")
    data = load_mkqa_data(input_file)
    print(f"Loaded {len(data)} question pairs")


    # Modify process_mkqa_data to accept additional parameters
    results = process_mkqa_data_with_config(
        data,
        model=model,
        delay=args.delay,
        save_interval=args.save_interval,
        output_dir=os.path.dirname(output_file) or '.',
        num_threads=args.threads
    )

    print("\nSaving results...")
    save_results(results, output_file)

    # Print sample results
    print("\n" + "="*60)
    print("Sample results:")
    print("="*60)
    if results:
        for i in range(min(3, len(results))):
            sample = results[i]
            print(f"\nExample {i+1}:")
            print(f"  Original Korean:  {sample['original_ko']}")
            print(f"  Original English: {sample['original_en']}")
            print("  Code-switched versions:")
            for case_name, text in sample['code_switched_versions'].items():
                print(f"    [{case_name}]: {text}")

def process_single_item(item_data: tuple, model: str, delay: float) -> Dict:
    """Process a single item for code-switching generation."""
    idx, item = item_data
    ko_text = item['ko']
    en_text = item['en']

    result = {
        "id": idx,
        "original_ko": ko_text,
        "original_en": en_text,
        "code_switched_versions": {}
    }

    # Define code-switching cases
    code_switching_cases = ["Case1", "Case2", "Case3", "Case4", "Case5"]

    # Generate code-switched versions for each case
    for case_name in code_switching_cases:
        if case_name == "Case1":
            # Pure Korean
            result["code_switched_versions"][case_name] = ko_text
        elif case_name == "Case5":
            # Pure English
            result["code_switched_versions"][case_name] = en_text
        else:
            # Generate code-switched version
            code_switched = generate_code_switched_text(ko_text, en_text, case_name, model=model)
            result["code_switched_versions"][case_name] = code_switched

            # Add delay to avoid rate limiting
            time.sleep(delay)

    return result

def process_mkqa_data_with_config(data: List[Dict[str, str]],
                                  model: str = "gpt-4o-mini",
                                  delay: float = 0.1,
                                  save_interval: int = 10,
                                  output_dir: str = '.',
                                  num_threads: int = 5) -> List[Dict]:
    """Process MKQA data with custom configuration using multithreading."""

 
    # Prepare data with indices
    indexed_data = list(enumerate(data))

    # Results dictionary to maintain order
    results_dict = {}
    results_lock = threading.Lock()

    # Progress bar
    pbar = tqdm(total=len(data), desc="Generating code-switched data")

    # Function to process item and update progress
    def process_with_progress(item_data):
        result = process_single_item(item_data, model, delay)

        with results_lock:
            results_dict[result['id']] = result
            pbar.update(1)

            # Save intermediate results at specified interval
            if len(results_dict) % save_interval == 0:
                sorted_results = [results_dict[i] for i in sorted(results_dict.keys())]
                intermediate_file = os.path.join(output_dir, "code_switched_data_intermediate.json")
                save_results(sorted_results, intermediate_file)

        return result

    # Process items in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit all tasks
        futures = [executor.submit(process_with_progress, item) for item in indexed_data]

        # Wait for all tasks to complete
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing item: {e}")

    pbar.close()

    # Sort results by ID to maintain order
    results = [results_dict[i] for i in sorted(results_dict.keys())]

    return results

if __name__ == "__main__":
    main()