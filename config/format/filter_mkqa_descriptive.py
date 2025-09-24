#!/usr/bin/env python3
"""
Filter MKQA dataset for Korean and English entries with descriptive answer types
Focus on entity and short_phrase types which are closest to descriptive answers
"""
import json

def filter_mkqa_dataset(input_file, output_file):
    """
    Filter MKQA dataset for:
    1. Only Korean (ko) and English (en) languages
    2. Only entries with descriptive answer types: entity, short_phrase
    3. Must have actual text content (not null)
    """
    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total original entries: {len(data)}")

    # Descriptive answer types (closest to long answers)
    descriptive_types = {"entity", "short_phrase"}

    filtered_data = []
    type_stats = {}

    for entry in data:
        # Create new filtered entry
        filtered_entry = {
            "query": entry["query"],
            "answers": {}
        }

        has_descriptive_answer = False

        # Process English answers
        if "en" in entry["answers"]:
            en_descriptive = []
            for answer in entry["answers"]["en"]:
                # Include only descriptive types with actual text
                if (answer.get("type") in descriptive_types and
                    answer.get("text") is not None):
                    en_descriptive.append(answer)

                    # Track answer types
                    ans_type = answer.get("type", "unknown")
                    type_stats[ans_type] = type_stats.get(ans_type, 0) + 1

            if en_descriptive:
                filtered_entry["answers"]["en"] = en_descriptive
                has_descriptive_answer = True

        # Process Korean answers
        if "ko" in entry["answers"]:
            ko_descriptive = []
            for answer in entry["answers"]["ko"]:
                # Include only descriptive types with actual text
                if (answer.get("type") in descriptive_types and
                    answer.get("text") is not None):
                    ko_descriptive.append(answer)

            if ko_descriptive:
                filtered_entry["answers"]["ko"] = ko_descriptive
                has_descriptive_answer = True

        # Only add entry if it has descriptive answers in both languages
        if has_descriptive_answer and "en" in filtered_entry["answers"] and "ko" in filtered_entry["answers"]:
            filtered_data.append(filtered_entry)

    print(f"\nFiltered entries with descriptive answers: {len(filtered_data)}")

    # Count statistics
    entity_count = sum(1 for entry in filtered_data
                      for lang in entry["answers"].values()
                      for ans in lang if ans.get("type") == "entity")

    phrase_count = sum(1 for entry in filtered_data
                      for lang in entry["answers"].values()
                      for ans in lang if ans.get("type") == "short_phrase")

    print(f"Total entity answers: {entity_count}")
    print(f"Total short_phrase answers: {phrase_count}")

    # Save filtered data
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(filtered_data)} filtered entries")

    # Show sample entries
    if filtered_data:
        print("\n" + "="*60)
        print("Sample filtered entries (descriptive answers only):")
        print("="*60)

        for i in range(min(5, len(filtered_data))):
            sample = filtered_data[i]
            print(f"\nEntry {i+1}:")
            print(f"Query: {sample['query']}")

            if "en" in sample["answers"]:
                en_ans = sample["answers"]["en"][0]
                text = en_ans.get('text', '')
                if len(text) > 50:
                    text = text[:50] + "..."
                print(f"English: {text} (type: {en_ans.get('type')})")

            if "ko" in sample["answers"]:
                ko_ans = sample["answers"]["ko"][0]
                text = ko_ans.get('text', '')
                if len(text) > 50:
                    text = text[:50] + "..."
                print(f"Korean: {text} (type: {ko_ans.get('type')})")

    # Also create a version that converts these to a "long_answer" format
    # for compatibility with your expected format
    formatted_for_long = []
    for entry in filtered_data:
        new_entry = {
            "query": entry["query"],
            "answers": {}
        }

        # Convert to long_answer format
        if "en" in entry["answers"]:
            en_text = " / ".join([ans.get("text", "") for ans in entry["answers"]["en"]])
            new_entry["answers"]["en"] = [{
                "type": "long_answer",  # Changed to long_answer for consistency
                "text": en_text,
                "original_type": entry["answers"]["en"][0].get("type")
            }]

        if "ko" in entry["answers"]:
            ko_text = " / ".join([ans.get("text", "") for ans in entry["answers"]["ko"]])
            new_entry["answers"]["ko"] = [{
                "type": "long_answer",  # Changed to long_answer for consistency
                "text": ko_text,
                "original_type": entry["answers"]["ko"][0].get("type")
            }]

        formatted_for_long.append(new_entry)

    # Save the reformatted version
    output_long_format = output_file.replace(".json", "_long_format.json")
    with open(output_long_format, 'w', encoding='utf-8') as f:
        json.dump(formatted_for_long, f, ensure_ascii=False, indent=2)

    print(f"\nAlso saved reformatted version as long_answer type:")
    print(f"Output file: {output_long_format}")

    return len(filtered_data)

if __name__ == "__main__":
    input_file = "mkqa_dataset.json"
    output_file = "mkqa_formatted.json"

    count = filter_mkqa_dataset(input_file, output_file)
    print(f"\n✅ Filtering complete!")
    print(f"Primary output: {output_file}")
    print(f"Total entries: {count}")