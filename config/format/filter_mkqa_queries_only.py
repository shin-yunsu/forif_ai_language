#!/usr/bin/env python3
"""
Filter MKQA dataset for entries with long_answer type
Extract only English query and Korean query (no answers needed)
"""
import json

def filter_mkqa_dataset(input_file, output_file):
    """
    Filter MKQA dataset for:
    1. Entries with long_answer type
    2. Extract only query (EN) and queries.ko (Korean query)
    3. No answers needed
    """
    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total original entries: {len(data)}")

    filtered_data = []

    for entry in data:
        # Check if this entry has long_answer type in Korean answers
        has_long_answer = False

        ko_answers = entry.get("answers", {}).get("ko", [])
        for answer in ko_answers:
            if answer.get("type") == "long_answer":
                has_long_answer = True
                break

        # If has long_answer type, extract query and Korean query
        if has_long_answer:
            # Get English query
            en_query = entry.get("query", "")

            # Get Korean query from queries field
            ko_query = entry.get("queries", {}).get("ko", "")

            # Skip if no Korean query
            if not ko_query:
                continue

            # Create simplified entry with only queries
            filtered_entry = {
                "query": en_query,  # English query
                "queries": {
                    "ko": ko_query  # Korean query only
                }
            }

            filtered_data.append(filtered_entry)

    print(f"\nFiltered entries with long_answer type: {len(filtered_data)}")

    # Save filtered data
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(filtered_data)} filtered entries")

    # Show sample entries
    if filtered_data:
        print("\n" + "="*60)
        print("Sample filtered entries (queries only):")
        print("="*60)

        for i in range(min(10, len(filtered_data))):
            sample = filtered_data[i]
            print(f"\nEntry {i+1}:")
            print(f"EN: {sample['query']}")
            print(f"KO: {sample['queries']['ko']}")

    # Also create a simple list format
    simple_list = []
    for entry in filtered_data:
        simple_list.append({
            "en": entry["query"],
            "ko": entry["queries"]["ko"]
        })

    # Save simple list version
    simple_output = output_file.replace(".json", "_simple.json")
    with open(simple_output, 'w', encoding='utf-8') as f:
        json.dump(simple_list, f, ensure_ascii=False, indent=2)

    print(f"\nAlso saved simple list version: {simple_output}")

    return len(filtered_data)

if __name__ == "__main__":
    input_file = "mkqa_dataset.json"
    output_file = "mkqa_formatted.json"

    count = filter_mkqa_dataset(input_file, output_file)
    print(f"\n✅ Filtering complete!")
    print(f"Output file: {output_file}")
    print(f"Total entries: {count}")