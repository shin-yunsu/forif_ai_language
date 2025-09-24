#!/usr/bin/env python3
"""
Analyze answer types to understand data structure better
"""
import json

# Load the original dataset
with open('mkqa_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Analyzing answer types and their content...")
print("="*60)

# Sample different answer types
answer_samples = {}

for entry in data[:1000]:  # Check first 1000 entries
    for lang in ["en", "ko"]:
        if lang in entry["answers"]:
            for answer in entry["answers"][lang]:
                answer_type = answer.get("type", "unknown")

                # Store a sample for each type if it has actual text
                if answer_type not in answer_samples and answer.get("text") is not None:
                    answer_samples[answer_type] = {
                        "query": entry["query"],
                        "language": lang,
                        "answer": answer
                    }

# Display samples
for ans_type, sample in answer_samples.items():
    print(f"\nType: {ans_type}")
    print(f"Query: {sample['query']}")
    print(f"Language: {sample['language']}")
    print(f"Answer: {sample['answer']}")
    print("-"*40)

# Count long_answer entries with actual content
long_answer_count = 0
long_answer_with_text = 0
long_answer_samples = []

for entry in data:
    for lang in ["en", "ko"]:
        if lang in entry["answers"]:
            for answer in entry["answers"][lang]:
                if answer.get("type") == "long_answer":
                    long_answer_count += 1
                    if answer.get("text") is not None:
                        long_answer_with_text += 1
                        if len(long_answer_samples) < 3:
                            long_answer_samples.append({
                                "query": entry["query"],
                                "lang": lang,
                                "text": answer["text"]
                            })

print(f"\n📊 Long Answer Statistics:")
print(f"Total long_answer entries: {long_answer_count}")
print(f"Long answers with actual text: {long_answer_with_text}")
print(f"Long answers with null text: {long_answer_count - long_answer_with_text}")

if long_answer_samples:
    print(f"\n📝 Long Answer Samples with text:")
    for sample in long_answer_samples:
        print(f"\nQuery: {sample['query']}")
        print(f"Language: {sample['lang']}")
        print(f"Text: {sample['text'][:200]}..." if len(sample['text']) > 200 else f"Text: {sample['text']}")