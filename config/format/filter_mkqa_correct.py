#!/usr/bin/env python3
"""
Filter MKQA dataset correctly:
- English query as main query
- Korean query in queries.ko
- Korean answers only
- Filter for meaningful answers (convert to long_answer type)
"""
import json

def filter_mkqa_dataset(input_file, output_file):
    """
    Filter MKQA dataset to create the correct structure
    """
    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total original entries: {len(data)}")

    filtered_data = []
    type_stats = {}

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

        # Filter for entries with actual text content
        valid_ko_answers = []
        for answer in ko_answers:
            # Skip null text and unanswerable
            if answer.get("text") is not None and answer.get("type") != "unanswerable":
                # Convert all to long_answer format as requested
                formatted_answer = {
                    "type": "long_answer",
                    "text": answer.get("text")
                }

                # Track original type for statistics
                original_type = answer.get("type")
                type_stats[original_type] = type_stats.get(original_type, 0) + 1

                # Optionally keep original type as metadata
                if original_type != "long_answer":
                    formatted_answer["original_type"] = original_type

                # Include aliases if they exist
                if "aliases" in answer:
                    formatted_answer["aliases"] = answer["aliases"]

                valid_ko_answers.append(formatted_answer)

        # Only include if we have valid Korean answers
        if valid_ko_answers:
            filtered_entry = {
                "query": en_query,  # English query
                "queries": {
                    "ko": ko_query  # Korean query
                },
                "answers": {
                    "ko": valid_ko_answers  # Korean answers only
                }
            }
            filtered_data.append(filtered_entry)

    print(f"\nFiltered entries: {len(filtered_data)}")

    print(f"\nOriginal answer type distribution:")
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

        for i in range(min(5, len(filtered_data))):
            sample = filtered_data[i]
            print(f"\nEntry {i+1}:")
            print(f"Query (EN): {sample['query']}")
            print(f"Query (KO): {sample['queries']['ko']}")

            if sample['answers']['ko']:
                ko_answer = sample['answers']['ko'][0]
                answer_text = ko_answer.get('text', '')
                if len(answer_text) > 50:
                    answer_text = answer_text[:50] + "..."
                original_type = ko_answer.get('original_type', 'long_answer')
                print(f"Answer (KO): {answer_text} [originally: {original_type}]")
            print("-"*40)

    # Statistics
    print(f"\n📊 Statistics:")
    print(f"Total filtered entries: {len(filtered_data)}")
    print(f"All entries have:")
    print(f"  - English query (query field)")
    print(f"  - Korean query (queries.ko field)")
    print(f"  - Korean answers (answers.ko field)")
    print(f"  - All answers converted to 'long_answer' type")

    return len(filtered_data)

if __name__ == "__main__":
    input_file = "mkqa_dataset.json"
    output_file = "mkqa_formatted.json"

    count = filter_mkqa_dataset(input_file, output_file)
    print(f"\n✅ Filtering complete!")
    print(f"Output file: {output_file}")
    print(f"Total entries: {count}")