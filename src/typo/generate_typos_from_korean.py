#!/usr/bin/env python3
"""
Generate typos from Korean-only text array using korean_typo_generator
"""

import json
import sys
import os
from pathlib import Path

# Add current directory to path for importing
sys.path.append(str(Path(__file__).parent))
from korean_typo_generator import KoreanTypoGenerator

def process_korean_texts(input_file: str, output_file: str):
    """Process Korean text array and generate typos"""

    # Load Korean texts
    print(f"📚 Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        korean_texts = json.load(f)

    print(f"📊 Found {len(korean_texts)} Korean texts")

    # Initialize typo generator
    generator = KoreanTypoGenerator(seed=42)

    # Process all texts
    print(f"🔄 Generating typos for all texts...")
    results = []

    for i, text in enumerate(korean_texts, 1):
        if i % 10 == 0:
            print(f"  Processing {i}/{len(korean_texts)}...")

        # Generate typos for this text
        result = generator.generate_typos(text)
        results.append(result)

    # Save results
    print(f"💾 Saving results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Show statistics
    print(f"\n✅ Successfully generated typos for {len(results)} texts")
    print(f"📄 Output saved to: {output_file}")

    # Show sample result
    if results:
        print("\n📝 Sample output (first entry):")
        sample = results[0]
        print(f"  Original: {sample['original']}")
        for error_type in ['substitution', 'deletion', 'insertion', 'transposition', 'spacing']:
            if error_type in sample:
                print(f"  {error_type}:")
                print(f"    1_error: {sample[error_type]['1_error']}")
                print(f"    2_errors: {sample[error_type]['2_errors']}")

    return len(results)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate typos from Korean text array")
    parser.add_argument("--input", default="../refine/mkqa_korean_only.json",
                        help="Input JSON file with Korean text array")
    parser.add_argument("--output", default="mkqa_korean_with_typos.json",
                        help="Output JSON file with generated typos")

    args = parser.parse_args()

    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        exit(1)

    # Process
    count = process_korean_texts(args.input, args.output)
    print(f"\n✨ Complete! Processed {count} texts")