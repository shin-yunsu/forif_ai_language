#!/usr/bin/env python3
"""
mkqa_refined.json 파일을 ko, en 형식으로 변환
"""
import json

def convert_format(input_file: str, output_file: str):
    """
    Convert from:
    {
      "query": "영어 질문",
      "queries": {
        "ko": "한국어 질문"
      }
    }

    To:
    {
      "en": "영어 질문",
      "ko": "한국어 질문"
    }
    """

    print(f"📚 Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📊 Total entries: {len(data)}")

    # Convert format
    converted_data = []

    for entry in data:
        # Extract English query
        en_query = entry.get("query", "")

        # Extract Korean query
        ko_query = ""
        if "queries" in entry and "ko" in entry["queries"]:
            ko_query = entry["queries"]["ko"]
        elif "ko" in entry:
            ko_query = entry["ko"]

        # Skip if either is missing
        if not en_query or not ko_query:
            continue

        # Create new format
        converted_entry = {
            "en": en_query,
            "ko": ko_query
        }

        converted_data.append(converted_entry)

    print(f"✅ Converted {len(converted_data)} entries")

    # Save converted data
    print(f"💾 Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Complete! Saved to {output_file}")

    # Show sample
    print("\n📝 Sample entries:")
    for i in range(min(5, len(converted_data))):
        print(f"\nEntry {i+1}:")
        print(f"  EN: {converted_data[i]['en'][:60]}...")
        print(f"  KO: {converted_data[i]['ko'][:60]}...")

    return len(converted_data)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert mkqa_refined to en/ko format")
    parser.add_argument("--input", default="mkqa_refined.json", help="Input JSON file")
    parser.add_argument("--output", default="mkqa_refined_simple.json", help="Output JSON file")

    args = parser.parse_args()

    # Check if input file exists
    import os
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        print("Available files:")
        for file in os.listdir('.'):
            if 'mkqa' in file and file.endswith('.json'):
                print(f"  - {file}")
        exit(1)

    count = convert_format(args.input, args.output)
    print(f"\n📊 Final statistics:")
    print(f"  Input: {args.input}")
    print(f"  Output: {args.output}")
    print(f"  Total entries: {count}")