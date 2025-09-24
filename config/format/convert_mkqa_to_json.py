#!/usr/bin/env python3
"""
Convert MKQA dataset from JSONL to JSON format
"""
import json
import sys

def convert_jsonl_to_json(input_file, output_file):
    """Convert JSONL file to JSON array format"""
    data = []

    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i % 1000 == 0:
                print(f"Processing entry {i}...")
            try:
                entry = json.loads(line.strip())
                data.append(entry)
            except json.JSONDecodeError as e:
                print(f"Error parsing line {i}: {e}")
                continue

    print(f"Total entries loaded: {len(data)}")

    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Successfully converted {len(data)} entries to JSON format")
    return len(data)

if __name__ == "__main__":
    input_file = "ml-mkqa/dataset/mkqa.jsonl"
    output_file = "mkqa_dataset.json"

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    count = convert_jsonl_to_json(input_file, output_file)
    print(f"\nDataset successfully converted!")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"Total entries: {count}")