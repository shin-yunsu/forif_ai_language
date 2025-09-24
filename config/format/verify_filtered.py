#!/usr/bin/env python3
"""
Verify the filtered MKQA dataset
"""
import json

# Load the filtered dataset
with open('mkqa_formatted.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total filtered entries: {len(data)}")
print("\n" + "="*60)
print("Sample entries with actual content:")
print("="*60)

# Show first 5 entries that have non-null text
shown = 0
for i, entry in enumerate(data):
    has_content = False

    # Check if there's actual text content (not null)
    if "en" in entry["answers"]:
        for answer in entry["answers"]["en"]:
            if answer.get("text") is not None:
                has_content = True
                break

    if has_content and shown < 5:
        print(f"\nEntry {i+1}:")
        print(f"Query: {entry['query']}")

        if "en" in entry["answers"]:
            print(f"English answer: {entry['answers']['en'][0]}")

        if "ko" in entry["answers"]:
            print(f"Korean answer: {entry['answers']['ko'][0]}")

        print("-" * 40)
        shown += 1

# Count entries with actual text vs null
null_count = 0
text_count = 0

for entry in data:
    if "en" in entry["answers"]:
        for answer in entry["answers"]["en"]:
            if answer.get("text") is None:
                null_count += 1
            else:
                text_count += 1
            break  # Only check first answer

print(f"\n📊 Statistics:")
print(f"Entries with text content: {text_count}")
print(f"Entries with null content: {null_count}")