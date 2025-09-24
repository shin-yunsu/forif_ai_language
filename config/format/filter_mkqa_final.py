#!/usr/bin/env python3
"""
Filter MKQA dataset to extract English query with Korean translations
Format: query (en) -> queries: {ko: korean_query}, answers: {ko: korean_answers}
"""
import json

def filter_mkqa_dataset(input_file, output_file):
    """
    Filter MKQA dataset to create:
    - English query as main query
    - Korean query in queries.ko
    - Korean answers in answers.ko
    - Filter for long_answer type (or meaningful answers if long_answer is null)
    """
    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total original entries: {len(data)}")

    filtered_data = []

    # First, we need to understand the structure - MKQA has queries in different languages
    # Let's check if there's a queries field or if we need to extract from another source

    for entry in data:
        # The original query is in English
        en_query = entry.get("query", "")

        # Check if there are Korean answers (which would have Korean queries too)
        if "ko" in entry.get("answers", {}):
            ko_answers = entry["answers"]["ko"]

            # Filter for entries with actual text content
            valid_ko_answers = []
            for answer in ko_answers:
                # Check for long_answer type first
                if answer.get("type") == "long_answer":
                    if answer.get("text") is not None:
                        valid_ko_answers.append(answer)
                # If no long_answer with text, accept other meaningful types
                elif answer.get("text") is not None and answer.get("type") != "unanswerable":
                    # Convert to long_answer format
                    valid_ko_answers.append({
                        "type": "long_answer",
                        "text": answer.get("text"),
                        "original_type": answer.get("type")
                    })

            if valid_ko_answers:
                # Create the filtered entry with the required structure
                filtered_entry = {
                    "query": en_query,  # English query
                    "queries": {
                        "ko": entry.get("queries", {}).get("ko", en_query)  # Korean query if available
                    },
                    "answers": {
                        "ko": valid_ko_answers  # Korean answers
                    }
                }

                filtered_data.append(filtered_entry)

    print(f"\nFiltered entries: {len(filtered_data)}")

    # Since MKQA might not have queries field, let's check the structure
    if len(filtered_data) == 0 or "queries" not in data[0]:
        print("\nNote: MKQA dataset doesn't have separate 'queries' field.")
        print("Creating Korean queries by using the English query as placeholder.")
        print("For actual Korean queries, manual translation or another dataset would be needed.")

        # Re-process without queries field
        filtered_data = []

        for entry in data:
            en_query = entry.get("query", "")

            if "ko" in entry.get("answers", {}):
                ko_answers = entry["answers"]["ko"]

                # Filter for entries with actual text content
                valid_ko_answers = []
                for answer in ko_answers:
                    if answer.get("text") is not None and answer.get("type") != "unanswerable":
                        # Keep original type but mark it
                        valid_ko_answers.append({
                            "type": "long_answer",
                            "text": answer.get("text"),
                            "original_type": answer.get("type")
                        })

                if valid_ko_answers:
                    # Create the filtered entry
                    filtered_entry = {
                        "query": en_query,  # English query
                        "queries": {
                            "ko": en_query  # Using English as placeholder (MKQA doesn't have translated queries)
                        },
                        "answers": {
                            "ko": valid_ko_answers  # Korean answers
                        }
                    }

                    filtered_data.append(filtered_entry)

    print(f"Final filtered entries: {len(filtered_data)}")

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
            print(f"Query (EN): {sample['query']}")
            print(f"Query (KO): {sample['queries']['ko']}")
            if sample['answers']['ko']:
                ko_answer = sample['answers']['ko'][0]
                print(f"Answer (KO): {ko_answer.get('text')} (original type: {ko_answer.get('original_type', 'long_answer')})")
            print("-"*40)

    # Also save a version with just the essential fields
    simple_data = []
    for entry in filtered_data:
        if entry['answers']['ko']:
            simple_entry = {
                "query": entry["query"],
                "query_ko": entry["queries"]["ko"],
                "answer_ko": entry['answers']['ko'][0]['text'],
                "answer_type": entry['answers']['ko'][0].get('original_type', 'long_answer')
            }
            simple_data.append(simple_entry)

    # Save simplified version
    simple_output = output_file.replace(".json", "_simple.json")
    with open(simple_output, 'w', encoding='utf-8') as f:
        json.dump(simple_data, f, ensure_ascii=False, indent=2)

    print(f"\nAlso saved simplified version: {simple_output}")

    return len(filtered_data)

if __name__ == "__main__":
    input_file = "mkqa_dataset.json"
    output_file = "mkqa_formatted.json"

    count = filter_mkqa_dataset(input_file, output_file)
    print(f"\n✅ Filtering complete!")
    print(f"Output file: {output_file}")
    print(f"Total entries: {count}")