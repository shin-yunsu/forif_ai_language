#!/usr/bin/env python3
"""
Filter MKQA dataset for Korean and English entries with meaningful answers
"""
import json

def filter_mkqa_dataset(input_file, output_file):
    """
    Filter MKQA dataset for:
    1. Only Korean (ko) and English (en) languages
    2. Only entries with actual text content (not null)
    3. Exclude "unanswerable" type
    """
    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total original entries: {len(data)}")

    filtered_data = []
    type_stats = {}

    for entry in data:
        # Create new filtered entry
        filtered_entry = {
            "query": entry["query"],
            "answers": {}
        }

        has_valid_answer = False

        # Process English answers
        if "en" in entry["answers"]:
            en_valid_answers = []
            for answer in entry["answers"]["en"]:
                # Include only if it has actual text and is not unanswerable
                if (answer.get("text") is not None and
                    answer.get("type") != "unanswerable"):
                    en_valid_answers.append(answer)

                    # Track answer types
                    ans_type = answer.get("type", "unknown")
                    type_stats[ans_type] = type_stats.get(ans_type, 0) + 1

            if en_valid_answers:
                filtered_entry["answers"]["en"] = en_valid_answers
                has_valid_answer = True

        # Process Korean answers
        if "ko" in entry["answers"]:
            ko_valid_answers = []
            for answer in entry["answers"]["ko"]:
                # Include only if it has actual text and is not unanswerable
                if (answer.get("text") is not None and
                    answer.get("type") != "unanswerable"):
                    ko_valid_answers.append(answer)

            if ko_valid_answers:
                filtered_entry["answers"]["ko"] = ko_valid_answers
                has_valid_answer = True

        # Only add entry if it has at least one valid answer
        if has_valid_answer:
            filtered_data.append(filtered_entry)

    print(f"\nFiltered entries with valid answers: {len(filtered_data)}")

    # Count statistics
    en_count = sum(1 for entry in filtered_data if "en" in entry["answers"])
    ko_count = sum(1 for entry in filtered_data if "ko" in entry["answers"])
    both_count = sum(1 for entry in filtered_data if "en" in entry["answers"] and "ko" in entry["answers"])

    print(f"Entries with English answers: {en_count}")
    print(f"Entries with Korean answers: {ko_count}")
    print(f"Entries with both languages: {both_count}")

    print(f"\nAnswer type distribution:")
    for ans_type, count in sorted(type_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ans_type}: {count}")

    # Save filtered data
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(filtered_data)} filtered entries")

    # Show sample entries
    if filtered_data:
        print("\n" + "="*60)
        print("Sample filtered entries:")
        print("="*60)

        for i in range(min(3, len(filtered_data))):
            sample = filtered_data[i]
            print(f"\nEntry {i+1}:")
            print(f"Query: {sample['query']}")

            if "en" in sample["answers"]:
                en_ans = sample["answers"]["en"][0]
                print(f"English: {en_ans.get('text')} (type: {en_ans.get('type')})")

            if "ko" in sample["answers"]:
                ko_ans = sample["answers"]["ko"][0]
                print(f"Korean: {ko_ans.get('text')} (type: {ko_ans.get('type')})")

    return len(filtered_data)

if __name__ == "__main__":
    input_file = "mkqa_dataset.json"
    output_file = "mkqa_formatted.json"

    count = filter_mkqa_dataset(input_file, output_file)
    print(f"\n✅ Filtering complete!")
    print(f"Output file: {output_file}")
    print(f"Total entries: {count}")