#!/usr/bin/env python3
"""
Analyze MKQA dataset structure and create a sample
"""
import json

# Load the dataset
print("Loading MKQA dataset...")
with open('mkqa_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total entries: {len(data)}")

# Get the first entry as a sample
sample_entry = data[0]

# Analyze language coverage
languages = set()
for entry in data[:100]:  # Check first 100 entries
    if 'answers' in entry:
        languages.update(entry['answers'].keys())

print(f"\nLanguages supported: {sorted(languages)}")
print(f"Total languages: {len(languages)}")

# Save a sample file with just 5 entries
sample_data = data[:5]
with open('mkqa_sample.json', 'w', encoding='utf-8') as f:
    json.dump(sample_data, f, ensure_ascii=False, indent=2)

print("\nSample file created: mkqa_sample.json")

# Show structure of first entry
print("\n" + "="*50)
print("Dataset structure (first entry):")
print("="*50)
print(json.dumps(sample_entry, ensure_ascii=False, indent=2)[:2000] + "...")

# Count answer types
answer_types = {}
for entry in data:
    for lang, answers in entry.get('answers', {}).items():
        for answer in answers:
            if 'type' in answer:
                answer_types[answer['type']] = answer_types.get(answer['type'], 0) + 1

print("\n" + "="*50)
print("Answer types distribution:")
print("="*50)
for atype, count in sorted(answer_types.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"{atype}: {count}")