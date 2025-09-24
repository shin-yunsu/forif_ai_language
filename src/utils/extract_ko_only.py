#!/usr/bin/env python3
"""
Extract only Korean text from mkqa_refined.json and save as array
"""

import json

def extract_korean_only(input_file: str, output_file: str):
    """Extract only Korean text and save as array"""

    # Load the data
    print(f"📚 Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract only Korean text
    korean_texts = []
    for entry in data:
        if isinstance(entry, dict):
            # Check different possible structures
            if 'queries' in entry and 'ko' in entry['queries']:
                korean_texts.append(entry['queries']['ko'])
            elif 'ko' in entry:
                korean_texts.append(entry['ko'])

    # Save as array
    print(f"💾 Saving {len(korean_texts)} Korean texts to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(korean_texts, f, ensure_ascii=False, indent=2)

    # Show sample
    print(f"\n✅ Extracted {len(korean_texts)} Korean texts")
    print("\n📝 Sample (first 5):")
    for i, text in enumerate(korean_texts[:5], 1):
        print(f"  {i}. {text}")

    return len(korean_texts)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract Korean text only")
    parser.add_argument("--input", default="mkqa_refined.json", help="Input JSON file")
    parser.add_argument("--output", default="mkqa_korean_only.json", help="Output JSON file")

    args = parser.parse_args()

    count = extract_korean_only(args.input, args.output)
    print(f"\n✨ Complete! {count} texts saved to {args.output}")