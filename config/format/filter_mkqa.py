#!/usr/bin/env python3
"""
Filter MKQA dataset for Korean and English long_answer entries
"""
import json

def filter_mkqa_dataset(input_file, output_file):
    """
    Filter MKQA dataset for:
    1. Only Korean (ko) and English (en) languages
    2. Only entries with type "long_answer"
    """
    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total original entries: {len(data)}")

    filtered_data = []

    for entry in data:
        # Create new filtered entry
        filtered_entry = {
            "query": entry["query"],
            "answers": {}
        }

        # Check for Korean and English answers with long_answer type
        has_long_answer = False

        # Check English answers
        if "en" in entry["answers"]:
            en_long_answers = [
                answer for answer in entry["answers"]["en"]
                if answer.get("type") == "long_answer"
            ]
            if en_long_answers:
                filtered_entry["answers"]["en"] = en_long_answers
                has_long_answer = True

        # Check Korean answers
        if "ko" in entry["answers"]:
            ko_long_answers = [
                answer for answer in entry["answers"]["ko"]
                if answer.get("type") == "long_answer"
            ]
            if ko_long_answers:
                filtered_entry["answers"]["ko"] = ko_long_answers
                has_long_answer = True

        # Only add entry if it has at least one long_answer in either language
        if has_long_answer:
            filtered_data.append(filtered_entry)

    print(f"Filtered entries with long_answer: {len(filtered_data)}")

    # Count statistics
    en_count = sum(1 for entry in filtered_data if "en" in entry["answers"])
    ko_count = sum(1 for entry in filtered_data if "ko" in entry["answers"])
    both_count = sum(1 for entry in filtered_data if "en" in entry["answers"] and "ko" in entry["answers"])

    print(f"Entries with English long_answer: {en_count}")
    print(f"Entries with Korean long_answer: {ko_count}")
    print(f"Entries with both languages: {both_count}")

    # Save filtered data
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(filtered_data)} filtered entries")

    # Show sample entry
    if filtered_data:
        print("\n" + "="*50)
        print("Sample filtered entry:")
        print("="*50)
        sample = filtered_data[0]
        print(json.dumps(sample, ensure_ascii=False, indent=2))

    return len(filtered_data)

if __name__ == "__main__":
    input_file = "mkqa_dataset.json"
    output_file = "mkqa_formatted.json"

    count = filter_mkqa_dataset(input_file, output_file)
    print(f"\n✅ Filtering complete!")
    print(f"Output file: {output_file}")
    print(f"Total entries: {count}")