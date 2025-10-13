import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def load_data(file_path):
    """Load JSON data from file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def ask_gpt(question):
    """Send question to GPT-4o-mini and get response"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": question}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def process_questions(data, batch_size=5):
    """Process all questions from the data and collect answers"""
    # Limit to batch_size
    data = data[:batch_size]
    print(f"Processing {len(data)} items (batch size: {batch_size})")
    
    results = []

    for item in data:
        item_id = item['id']
        code_switched = item['code_switched_versions']

        # Create answer dictionary for this item
        answers = {}

        print(f"\nProcessing ID: {item_id}")

        # Ask each case question
        for case, question in code_switched.items():
            print(f"  {case}: {question}")
            answer = ask_gpt(question)
            answers[case] = answer
            print(f"  Answer: {answer[:100]}...")  # Print first 100 chars

        # Add to results
        result = {
            "id": item_id,
            "original_ko": item['original_ko'],
            "original_en": item['original_en'],
            "code_switched_versions": code_switched,
            "answers": answers
        }
        results.append(result)

    return results

def save_results(results, output_path):
    """Save results to JSON file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, indent=2, ensure_ascii=False, fp=f)
    print(f"\nResults saved to: {output_path}")

def main():
    # File paths
    input_file = "/Users/yunsu/Documents/study/ai/forif_ai/data/outputs/data_simple.json"
    output_file = "/Users/yunsu/Documents/study/ai/forif_ai/data/outputs/question_answers.json"

    # Load data
    print("Loading data...")
    data = load_data(input_file)
    print(f"Loaded {len(data)} items")

    # Process questions
    print("\nProcessing questions...")
    results = process_questions(data, batch_size=5)

    # Save results
    save_results(results, output_file)
    print("\nDone!")

if __name__ == "__main__":
    main()
