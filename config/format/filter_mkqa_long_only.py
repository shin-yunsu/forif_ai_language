#!/usr/bin/env python3
"""
Filter MKQA dataset for ONLY entries with type="long_answer"
"""
import json

def filter_mkqa_dataset(input_file, output_file):
    """
    Filter MKQA dataset for:
    1. English query
    2. Korean query in queries.ko
    3. Korean answers with type="long_answer" ONLY
    """
    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total original entries: {len(data)}")

    filtered_data = []
    long_answer_with_text = 0
    long_answer_with_null = 0

    for entry in data:
        # Get English query
        en_query = entry.get("query", "")

        # Get Korean query from queries field
        ko_query = entry.get("queries", {}).get("ko", "")

        # Skip if no Korean query
        if not ko_query:
            continue

        # Get Korean answers
        ko_answers = entry.get("answers", {}).get("ko", [])

        # Filter for ONLY long_answer type
        long_answers = []
        for answer in ko_answers:
            # Check if type is exactly "long_answer"
            if answer.get("type") == "long_answer":
                long_answers.append(answer)

                # Count statistics
                if answer.get("text") is not None:
                    long_answer_with_text += 1
                else:
                    long_answer_with_null += 1

        # Only include if we have long_answer type
        if long_answers:
            filtered_entry = {
                "query": en_query,  # English query
                "queries": {
                    "ko": ko_query  # Korean query
                },
                "answers": {
                    "ko": long_answers  # Korean long_answers only
                }
            }
            filtered_data.append(filtered_entry)

    print(f"\nFiltered entries with long_answer type: {len(filtered_data)}")
    print(f"Long answers with actual text: {long_answer_with_text}")
    print(f"Long answers with null text: {long_answer_with_null}")

    if long_answer_with_text == 0:
        print("\n⚠️  WARNING: All long_answer types have null text!")
        print("The MKQA dataset's long_answer type doesn't contain actual text.")
        print("These are placeholders for questions that would have longer answers.")
        print("\nWould you like to filter for other answer types instead?")
        print("Available types with text: entity, date, number, short_phrase, etc.")

    # Save filtered data anyway
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(filtered_data)} filtered entries")

    # Show sample entries
    if filtered_data:
        print("\n" + "="*60)
        print("Sample filtered entries (long_answer only):")
        print("="*60)

        for i in range(min(5, len(filtered_data))):
            sample = filtered_data[i]
            print(f"\nEntry {i+1}:")
            print(f"Query (EN): {sample['query']}")
            print(f"Query (KO): {sample['queries']['ko']}")

            if sample['answers']['ko']:
                ko_answer = sample['answers']['ko'][0]
                answer_text = ko_answer.get('text')
                print(f"Answer (KO): {answer_text}")
                print(f"Answer type: {ko_answer.get('type')}")
            print("-"*40)

    return len(filtered_data)

if __name__ == "__main__":
    input_file = "mkqa_dataset.json"
    output_file = "mkqa_formatted.json"

    count = filter_mkqa_dataset(input_file, output_file)
    print(f"\n✅ Filtering complete!")
    print(f"Output file: {output_file}")
    print(f"Total entries with long_answer type: {count}")