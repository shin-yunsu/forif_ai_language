import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

# Load environment variables
load_dotenv()

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# G-Eval judge model
JUDGE_MODEL = "openai/gpt-4o-2024-11-20"

# Cases to compare (excluding Case5)
CASES = ["Case1", "Case2", "Case3", "Case4"]

# Models to evaluate
MODELS = ["qwen_7b", "qwen_72b"]

GEVAL_PROMPT_TEMPLATE = """You will be given one question and two answers.

Your task is to rate the answers on one metric in a pairwise comparison.

Please make sure you read and understand these instructions carefully. Please keep this document open while reviewing, and refer to it as needed.

Evaluation Criteria:

Relevance (1-5) - selection of important content from the question. The response should include only important information and should not contain redundancies or excess information.

Evaluation Steps:

1. Read the question carefully and identify the main topic and key points.
2. Read Answer A and identify how well it covers the key points from the question.
3. Read Answer B and identify how well it covers the key points from the question.
4. Compare the two answers and determine which one is better at covering the key points.
5. Assign a score for Answer A on a scale of 1 to 5, where 1 is the lowest and 5 is the highest based on the Evaluation Criteria.
6. Assign a score for Answer B on a scale of 1 to 5, where 1 is the lowest and 5 is the highest based on the Evaluation Criteria.

Question:

{question}

Answer A (Case {case_a}):

{response_a}

Answer B (Case {case_b}):

{response_b}

Evaluation Form (scores ONLY):

- Relevance (Answer A):
- Relevance (Answer B):
"""

def get_geval_comparison(question: str, case_a: str, response_a: str, case_b: str, response_b: str) -> Dict:
    """Get G-Eval pairwise comparison between two responses"""
    import re
    
    try:
        prompt = GEVAL_PROMPT_TEMPLATE.format(
            question=question,
            case_a=case_a,
            response_a=response_a,
            case_b=case_b,
            response_b=response_b
        )
        
        completion = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0
        )
        
        response = completion.choices[0].message.content
        
        # Parse the response to extract scores
        score_a = None
        score_b = None
        
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if "Relevance (Answer A):" in line or "Relevance(Answer A):" in line:
                # Extract score from the line
                score_text = line.split(':')[-1].strip()
                try:
                    score_a = int(score_text)
                except ValueError:
                    # Try to find a number in the line
                    numbers = re.findall(r'\d+', score_text)
                    if numbers:
                        score_a = int(numbers[0])
            elif "Relevance (Answer B):" in line or "Relevance(Answer B):" in line:
                score_text = line.split(':')[-1].strip()
                try:
                    score_b = int(score_text)
                except ValueError:
                    numbers = re.findall(r'\d+', score_text)
                    if numbers:
                        score_b = int(numbers[0])
        
        winner = None
        if score_a is not None and score_b is not None:
            if score_a > score_b:
                winner = case_a
            elif score_b > score_a:
                winner = case_b
            else:
                winner = "Tie"
        
        return {
            "score_a": score_a,
            "score_b": score_b,
            "winner": winner,
            "full_response": response
        }
    except Exception as e:
        print(f"Error in G-Eval comparison: {e}")
        return {
            "score_a": None,
            "score_b": None,
            "winner": None,
            "full_response": str(e)
        }

def process_pairwise_comparisons(input_file: str, output_file: str, max_workers: int = 5):
    """Process all pairwise comparisons for code-switched data"""
    
    # Load input data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Load existing progress if available
    processed_items = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
                for item in existing_results:
                    processed_items[item['id']] = item
                print(f"Resuming from checkpoint: {len(processed_items)} items already processed")
        except Exception as e:
            print(f"Could not load existing progress: {e}")
    
    results = list(processed_items.values())
    
    # Filter unprocessed items
    unprocessed_data = [item for item in data if item['id'] not in processed_items]
    print(f"Processing {len(unprocessed_data)} remaining items")
    
    for idx, item in enumerate(unprocessed_data):
        print(f"\nProcessing item {idx + 1}/{len(unprocessed_data)}: ID {item['id']}")
        
        result_item = {
            "id": item["id"],
            "original_ko": item["original_ko"],
            "original_en": item["original_en"],
            "evaluations": {}
        }
        
        # Process each model separately
        for model in MODELS:
            print(f"  Evaluating model: {model}")
            result_item["evaluations"][model] = {}
            
            # Generate all pairwise combinations
            case_pairs = list(combinations(CASES, 2))
            
            # Prepare tasks for parallel execution
            tasks = []
            for case_a, case_b in case_pairs:
                # Get responses for both cases
                response_a = item["responses"].get(case_a, {}).get(model, "")
                response_b = item["responses"].get(case_b, {}).get(model, "")
                
                # Skip if either response is missing
                if not response_a or not response_b:
                    continue
                
                # Use the code-switched question for the appropriate case
                question = item["code_switched_versions"].get(case_a, item["original_ko"])
                
                tasks.append((question, case_a, response_a, case_b, response_b))
            
            # Execute comparisons in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(get_geval_comparison, q, ca, ra, cb, rb): (ca, cb)
                    for q, ca, ra, cb, rb in tasks
                }
                
                for future in as_completed(futures):
                    case_a, case_b = futures[future]
                    try:
                        comparison = future.result()
                        pair_key = f"{case_a}_vs_{case_b}"
                        result_item["evaluations"][model][pair_key] = comparison
                        print(f"    ✓ {pair_key}: {comparison['winner']}")
                    except Exception as e:
                        print(f"    ✗ {case_a}_vs_{case_b}: Error - {e}")
        
        results.append(result_item)
        
        # Save progress after each item
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  💾 Progress saved ({len(results)} items completed)")
    
    # Calculate summary statistics
    summary = calculate_summary_statistics(results)
    
    # Save final results with summary
    final_output = {
        "results": results,
        "summary": summary
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Processing complete! Results saved to {output_file}")
    print(f"\n📊 Summary Statistics:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

def calculate_summary_statistics(results: List[Dict]) -> Dict:
    """Calculate win rates and average scores for each case across all comparisons"""
    
    summary = {}
    
    for model in MODELS:
        summary[model] = {
            "case_wins": {case: 0 for case in CASES},
            "case_scores": {case: [] for case in CASES},
            "ties": 0,
            "total_comparisons": 0
        }
        
        for item in results:
            if "evaluations" not in item or model not in item["evaluations"]:
                continue
            
            for pair_key, comparison in item["evaluations"][model].items():
                winner = comparison.get("winner")
                score_a = comparison.get("score_a")
                score_b = comparison.get("score_b")
                
                # Extract case names from pair_key (e.g., "Case1_vs_Case2")
                cases = pair_key.replace("_vs_", " ").split()
                if len(cases) == 2:
                    case_a_name = cases[0]
                    case_b_name = cases[1]
                    
                    # Record scores
                    if score_a is not None:
                        summary[model]["case_scores"][case_a_name].append(score_a)
                    if score_b is not None:
                        summary[model]["case_scores"][case_b_name].append(score_b)
                
                summary[model]["total_comparisons"] += 1
                
                if winner == "Tie":
                    summary[model]["ties"] += 1
                elif winner in CASES:
                    summary[model]["case_wins"][winner] += 1
        
        # Calculate win rates and average scores
        total = summary[model]["total_comparisons"]
        if total > 0:
            summary[model]["win_rates"] = {
                case: round(wins / total * 100, 2) 
                for case, wins in summary[model]["case_wins"].items()
            }
            summary[model]["tie_rate"] = round(summary[model]["ties"] / total * 100, 2)
        
        # Calculate average scores
        summary[model]["average_scores"] = {
            case: round(sum(scores) / len(scores), 2) if scores else 0
            for case, scores in summary[model]["case_scores"].items()
        }
        
        # Remove raw scores list from final output
        del summary[model]["case_scores"]
    
    return summary

if __name__ == "__main__":
    input_file = "data/outputs/code_switched_responses.json"
    output_file = "data/outputs/geval_pairwise_results.json"
    
    process_pairwise_comparisons(input_file, output_file, max_workers=5)
