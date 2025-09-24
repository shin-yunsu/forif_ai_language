#!/usr/bin/env python3
"""
Use GPT-4-mini to refine Korean translations in MKQA dataset
"""
import json
import os
from openai import OpenAI
from typing import List, Dict, Optional
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Initialize OpenAI client
def initialize_client():
    """Initialize OpenAI client with API key from environment variable"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  Please set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        exit(1)

    client = OpenAI(api_key=api_key)
    return client

def process_batch(client, entries: List[Dict], batch_size: int = 10) -> List[Optional[Dict]]:
    """Process a batch of entries with GPT-4-mini"""

    # Prepare the batch data for GPT
    batch_text = json.dumps(entries, ensure_ascii=False, indent=2)

    prompt = f"""다음은 영어-한국어 질문 쌍입니다.
한국어 번역을 검토해서:
1. 완성되지 않은 한국어 문장은 기존 문장을 바탕으로 완성해주세요.
2. 어색한 한국어 문장을 자연스럽게 고쳐주세요.
3. 한국어에는 영어가 포함되지 않게 바꿔주세요.
4. 의미를 아에 모르겠는 한국어 문장은 null로 고쳐주세요.

입력 형식:
[{{"en": "영어 질문", "ko": "한국어 질문"}}, ...]

출력 형식 (JSON 배열로 반환):
[{{"en": "영어 질문", "ko": "개선된 한국어 또는 null"}}, ...]

입력 데이터:
{batch_text}

JSON 배열 형식으로만 응답해주세요."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using GPT-4-mini (also known as gpt-4o-mini)
            messages=[
                {"role": "system", "content": "당신은 한국어 번역 품질을 개선하는 전문가입니다. JSON 형식으로만 응답합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=2000
        )

        # Parse the response
        result_text = response.choices[0].message.content.strip()

        # Try to extract JSON from the response
        if result_text.startswith("```json"):
            result_text = result_text[7:]  # Remove ```json
        if result_text.startswith("```"):
            result_text = result_text[3:]  # Remove ```
        if result_text.endswith("```"):
            result_text = result_text[:-3]  # Remove ```

        result = json.loads(result_text)
        return result

    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Response: {result_text[:200]}...")
        return entries  # Return original if parsing fails
    except Exception as e:
        print(f"❌ API error: {e}")
        return entries  # Return original if API fails

def refine_korean_translations(input_file: str, output_file: str, batch_size: int = 10, max_workers: int = 5):
    """Main function to refine Korean translations"""

    # Load the data
    print(f"📚 Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if already in simple en/ko format
    if not (isinstance(data[0], dict) and "en" in data[0] and "ko" in data[0]):
        # Convert from structured format to simple format if needed
        if isinstance(data[0], dict) and "query" in data[0]:
            simple_data = []
            for entry in data:
                simple_data.append({
                    "en": entry["query"],
                    "ko": entry["queries"]["ko"]
                })
            data = simple_data
        else:
            print("❌ Unsupported data format. Expected 'en'/'ko' or 'query'/'queries' format")
            return 0

    print(f"📊 Total entries to process: {len(data)}")

    # Initialize OpenAI client
    client = initialize_client()

    # Process in batches with multi-threading
    refined_data = []
    failed_entries = []
    results_lock = threading.Lock()

    print(f"🔄 Processing in batches of {batch_size} with {max_workers} workers...")

    # Worker function for processing batches
    def process_batch_worker(batch_data, batch_index):
        """Process a single batch in a worker thread"""
        try:
            # Process batch with GPT
            refined_batch = process_batch(client, batch_data, batch_size)

            batch_refined = []
            batch_failed = []

            # Check results and filter out nulls
            for j, entry in enumerate(refined_batch):
                if entry and entry.get("ko") is not None:
                    batch_refined.append(entry)
                else:
                    batch_failed.append(batch_data[j] if j < len(batch_data) else None)

            return batch_index, batch_refined, batch_failed
        except Exception as e:
            print(f"❌ Error processing batch {batch_index}: {e}")
            return batch_index, [], batch_data

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}

        # Submit batch jobs
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            batch_index = i // batch_size
            future = executor.submit(process_batch_worker, batch, batch_index)
            futures[future] = batch_index

        # Collect results (maintaining order)
        results_dict = {}
        failed_dict = {}

        # Progress bar with result collection
        with tqdm(total=len(futures), desc="Processing batches") as pbar:
            for future in as_completed(futures):
                batch_index, batch_refined, batch_failed = future.result()
                results_dict[batch_index] = batch_refined
                failed_dict[batch_index] = batch_failed
                pbar.update(1)

        # Combine results in order
        for i in sorted(results_dict.keys()):
            refined_data.extend(results_dict[i])
            failed_entries.extend(failed_dict[i])

    print(f"\n✅ Successfully refined: {len(refined_data)} entries")
    print(f"❌ Discarded (low quality): {len(failed_entries)} entries")

    # Save refined data in simple en/ko format
    print(f"💾 Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(refined_data, f, ensure_ascii=False, indent=2)

    # Save discarded entries for review
    if failed_entries:
        discarded_file = output_file.replace(".json", "_discarded.json")
        with open(discarded_file, 'w', encoding='utf-8') as f:
            json.dump(failed_entries, f, ensure_ascii=False, indent=2)
        print(f"💾 Discarded entries saved to {discarded_file}")

    # Show sample improvements
    print("\n" + "="*60)
    print("Sample improvements:")
    print("="*60)

    for i in range(min(5, len(data), len(refined_data))):
        if i < len(data) and i < len(refined_data):
            print(f"\nEntry {i+1}:")
            print(f"Original KO: {data[i]['ko']}")
            print(f"Refined KO:  {refined_data[i]['ko']}")
            print("-"*40)

    return len(refined_data)

def create_sample_file(input_file: str, sample_file: str, sample_size: int = 20):
    """Create a small sample file for testing"""
    print(f"📝 Creating sample file with {sample_size} entries...")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sample_data = data[:sample_size]

    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Sample file created: {sample_file}")
    return sample_file

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Refine Korean translations using GPT-4-mini")
    parser.add_argument("--input", default="mkqa_short.json", help="Input JSON file")
    parser.add_argument("--output", default="mkqa_refined.json", help="Output JSON file")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for API calls")
    parser.add_argument("--max-workers", type=int, default=5, help="Maximum number of parallel workers")
    parser.add_argument("--test", action="store_true", help="Test with small sample first")
    parser.add_argument("--sample-size", type=int, default=20, help="Sample size for testing")

    args = parser.parse_args()

    if args.test:
        # Create and process a sample file first
        sample_file = "mkqa_short.json"
        create_sample_file(args.input, sample_file, args.sample_size)

        print("\n🧪 Testing with sample file...")
        count = refine_korean_translations(
            sample_file,
            "mkqa_sample_refined.json",
            batch_size=5,
            max_workers=2
        )
        print(f"\n✅ Test complete! Refined {count} entries")
        print("Check 'mkqa_sample_refined.json' for results")
    else:
        # Process full dataset
        count = refine_korean_translations(
            args.input,
            args.output,
            batch_size=args.batch_size,
            max_workers=args.max_workers
        )
        print(f"\n✅ Complete! Refined {count} entries")
        print(f"Output saved to: {args.output}")