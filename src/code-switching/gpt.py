#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from typing import List, Dict, Tuple
from openai import OpenAI
from tqdm import tqdm
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_mkqa_data(file_path: str) -> List[Dict[str, str]]:
    """Load MKQA data from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
def create_code_switching_prompt(ko_text: str, en_text: str) -> str:
    """Simple, clear code-switching prompt."""
    prompt = f"""당신은 한영 code-switching 전문가입니다. 아래 규칙을 따라 Case2~Case4를 생성하세요.

## 입력
- 한국어: {ko_text}
- 영어: {en_text}

## 핵심 규칙

### 1️⃣ 의문사는 절대 건드리지 마세요!
❌ "어디에서" → "where에서" (금지!)
❌ "무엇" → "what" (금지!)
❌ "언제" → "when" (금지!)

의문사: 어디, 어디에서, 언제, 왜, 무엇, 누가, 어떤, 어떻게, where, when, why, what, who, which, how

### 2️⃣ 교체 가능한 것
✅ 명사: 사람, 장소, 사물 (예: 병원/hospital, 학생/student)
✅ 동사: 행동 (예: 먹다/eat, 가다/go)
✅ 고유명사: 이름, 지명 (예: 서울/Seoul)
✅ 형용사: 성질 (예: 빠른/fast, 중요한/important)

**문장 길이별 핵심용어 추출 개수**:
- 짧은 문장 (5~10 단어): 3~5개
- 중간 문장 (11~20 단어): 5~8개
- 긴 문장 (21단어 이상): 8~12개

### 3️⃣ 생성 방법

**Case2-3: 한국어 문장에서 명사/동사를 영어로 바꾸기**
- Case2: 2~3개 바꾸기 (짧은 문장) / 3~5개 (긴 문장)
- Case3: 4~6개 바꾸기 (짧은 문장) / 6~9개 (긴 문장) - Case2보다 많이!
- 한국어 어순 유지
- 하이브리드 OK: "go하다", "eat했어요"
- **긴 문장일수록 더 많은 단어를 바꾸세요!**

**Case4: 영어 문장에서 명사/동사를 한국어로 바꾸기**
- Case4: 3~5개 바꾸기 (짧은 문장) / 5~8개 (긴 문장)
- 영어 어순 유지
- **중요**: 일반 명사/동사/형용사를 적극적으로 바꾸세요!
- **긴 문장일수록 더 많은 단어를 바꾸세요!**

## 예시

### 예시 1
입력:
- 한국어: 인슐린 의존 당뇨병 환자를 위한 계획에서 어떤 요소가 필수인가요?
- 영어: What factors are essential in the plan for insulin-dependent diabetic patients?

출력:
{{
  "Case2": "insulin 의존 diabetes 환자를 위한 plan에서 어떤 요소가 필수인가요?",
  "Case3": "insulin-dependent diabetes patients를 위한 plan에서 어떤 factors가 essential인가요?",
  "Case4": "What factors are essential in the plan for 인슐린 의존 당뇨병 환자?"
}}

### 예시 2 (의문사 보존!)
입력:
- 한국어: 제1차 세계 대전은 어디에서 일어났나요?
- 영어: where did the first world war take place

출력:
{{
  "Case2": "제1차 World War는 어디에서 일어났나요?",
  "Case3": "First World War는 어디에서 take place했나요?",
  "Case4": "where did the 제1차 세계 대전 take place?"
}}

### 예시 3
입력:
- 한국어: 누가 금과 노예를 거래했나요?
- 영어: who traded gold and slaves

출력:
{{
  "Case2": "누가 gold와 slaves를 거래했나요?",
  "Case3": "누가 gold와 slaves를 traded했나요?",
  "Case4": "who traded 금 and 노예?"
}}

### 예시 4 (바꿀 게 없으면 null)
입력:
- 한국어: 보여줘요.
- 영어: show me

출력:
{{
  "Case2": null,
  "Case3": null,
  "Case4": null
}}

## 실제 작업
이제 위 입력에 대해 Case2, Case3, Case4를 생성하세요.
JSON만 출력하세요 (설명 없이):

{{
  "Case2": "...",
  "Case3": "...",
  "Case4": "..."
}}
"""
    return prompt



def validate_code_switching(ko_text: str, en_text: str, result: Dict[str, str]) -> bool:
    """Validate code-switching results with relaxed rules.
    
    Returns:
        True if valid, False if should be rejected
    """
    if not result:
        return False
    
    # Check all cases exist and are not None
    for i in [2, 3, 4]:
        if f"Case{i}" not in result or result[f"Case{i}"] is None:
            return False
    
    # Extract cases
    case2 = result["Case2"]
    case3 = result["Case3"]
    case4 = result["Case4"]
    
    # 1. CRITICAL: Check Case2-3 don't have mixed interrogatives (한국어 문장에 영어 의문사 혼입)
    en_interrogatives = ["where", "when", "why", "what", "who", "which", "how"]
    
    # Case2-3: 영어 의문사가 단독으로 나타나면 안됨
    for case_text, case_name in [(case2, "Case2"), (case3, "Case3")]:
        for en_int in en_interrogatives:
            # "where에서", "what인가요" 같은 패턴 체크
            if f"{en_int}에서" in case_text.lower() or f"{en_int}인가요" in case_text.lower():
                print(f"❌ Validation failed: {case_name} has mixed interrogative '{en_int}'")
                return False
    
    # 2. Check all cases are different
    if case2 == case3:
        print(f"❌ Validation failed: Case2 == Case3")
        return False
    if case4 == en_text:
        print(f"❌ Validation failed: Case4 == original English")
        return False
    
    # 3. Basic language mix check (완화된 버전)
    def count_english_words(text):
        """Count approximate number of English words"""
        import re
        english_words = re.findall(r'[a-zA-Z]+', text)
        return len(english_words)
    
    def count_korean_chars(text):
        """Count approximate number of Korean characters"""
        import re
        korean_chars = re.findall(r'[가-힣]+', text)
        return len(korean_chars)
    
    # Very basic check: Case3 should have more English than Case2
    en_case2 = count_english_words(case2)
    en_case3 = count_english_words(case3)
    
    # 완화: 같거나 약간 적어도 OK
    if en_case2 > en_case3:
        print(f"⚠️ Warning: Case2 ({en_case2} EN) > Case3 ({en_case3} EN), but allowing")
    
    # Case4: 한국어가 있기만 하면 OK
    ko_case4 = count_korean_chars(case4)
    
    if ko_case4 == 0:
        print(f"❌ Validation failed: Case4 has no Korean")
        return False
    
    return True

def generate_code_switched_text(ko_text: str, en_text: str,
                               model_name: str = "gpt-5-mini") -> Dict[str, str]:
    """Generate all code-switching levels using GPT-5."""

    prompt = create_code_switching_prompt(ko_text, en_text)

    try:
        response = client.responses.create(
            model=model_name,
            instructions="You are a code-switching expert that generates Korean-English mixed sentences following strict rules.",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt}
                ]
            }],
            max_output_tokens=500,
            text={ "verbosity": "low" },
            reasoning={"effort": "minimal"}
        )
        
        result = json.loads(response.output_text)
        
        # 빈 결과가 있으면 실패로 간주
        if not all(result.get(f"Case{i}", "") for i in [2, 3, 4]):
            return None
        
        # Validate the result
        if not validate_code_switching(ko_text, en_text, result):
            print(f"⚠️ Validation failed for: {ko_text[:50]}...")
            return None
            
        return result

    except Exception as e:
        print(f"Error generating code-switched text: {e}")
        return None


def save_results(results: List[Dict], output_file: str):
    """Save results to JSON file."""
    if os.path.dirname(output_file):
        output_path = output_file
    else:
        output_path = os.path.join(os.path.dirname(__file__) or '.', output_file)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(results)} items to {output_path}")

def save_removed_items(removed_items: List[Dict], output_file: str):
    """Save removed items to a separate JSON file."""
    if os.path.dirname(output_file):
        output_path = output_file
    else:
        output_path = os.path.join(os.path.dirname(__file__) or '.', output_file)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(removed_items, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(removed_items)} removed items to {output_path}")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate code-switched Korean-English data from MKQA dataset",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--input",
        type=str,
        default="../jsons/mkqa_refined_full.json",
        help="Path to input MKQA JSON file"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="code_switched_data.json",
        help="Path to output JSON file"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5-mini",
        choices=["gpt-5-mini", "gpt-5", "gpt-4o-mini"],
        help="GPT model to use for generation"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay between API calls in seconds (to avoid rate limiting)"
    )

    parser.add_argument(
        "--save-interval",
        type=int,
        default=10,
        help="Save intermediate results every N items"
    )

    parser.add_argument(
        "--threads",
        type=int,
        default=5,
        help="Number of threads for parallel processing"
    )

    return parser.parse_args()

def main():
    """Main function to orchestrate the code-switching data generation."""

    args = parse_arguments()

    input_file = args.input
    output_file = args.output
    model = args.model

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it using: export OPENAI_API_KEY='your-api-key'")
        return

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        return

    print(f"Configuration:")
    print(f"  Input file: {input_file}")
    print(f"  Output file: {output_file}")
    print(f"  Model: {model}")
    print(f"  API delay: {args.delay}s")
    print(f"  Save interval: every {args.save_interval} items")
    print(f"  Threads: {args.threads}")
    print()

    print("Loading MKQA data...")
    data = load_mkqa_data(input_file)
    print(f"Loaded {len(data)} question pairs")

    results, removed_items = process_mkqa_data_with_config(
        data,
        model=model,
        delay=args.delay,
        save_interval=args.save_interval,
        output_dir=os.path.dirname(output_file) or '.',
        num_threads=args.threads
    )

    print("\nSaving results...")
    save_results(results, output_file)
    
    # Save removed items
    if removed_items:
        removed_file = output_file.replace('.json', 'code_removed.json')
        save_removed_items(removed_items, removed_file)

    print("\n" + "="*60)
    print("Processing Summary:")
    print("="*60)
    print(f"Total items processed: {len(data)}")
    print(f"Successfully converted: {len(results)}")
    print(f"Failed conversions: {len(removed_items)}")
    print(f"Success rate: {len(results)/len(data)*100:.2f}%")
    
    print("\n" + "="*60)
    print("Sample results:")
    print("="*60)
    if results:
        for i in range(min(3, len(results))):
            sample = results[i]
            print(f"\nExample {i+1}:")
            print(f"  Original Korean:  {sample['original_ko']}")
            print(f"  Original English: {sample['original_en']}")
            print("  Code-switched versions:")
            for key, value in sample['code_switched_versions'].items():
                print(f"    {key}: {value}")

def process_single_item(item_data: tuple, model: str, delay: float) -> Tuple[Dict, bool]:
    """Process a single item for code-switching generation.
    
    Returns:
        Tuple of (result_dict, success_flag)
    """
    idx, item = item_data
    ko_text = item['ko']
    en_text = item['en']

    result = {
        "id": idx,
        "original_ko": ko_text,
        "original_en": en_text,
        "code_switched_versions": {}
    }

    # Generate all code-switching levels at once
    code_switched = generate_code_switched_text(ko_text, en_text, model_name=model)
    
    # Check if generation failed
    if code_switched is None:
        result["code_switched_versions"]["Case0"] = ko_text
        result["code_switched_versions"]["Case1"] = None
        result["code_switched_versions"]["Case2"] = None
        result["code_switched_versions"]["Case3"] = None
        time.sleep(delay)
        return result, False
    
    # Add Case1 (pure Korean) and Case5 (pure English)
    result["code_switched_versions"]["Case1"] = ko_text
    result["code_switched_versions"]["Case2"] = code_switched.get("Case2", None)
    result["code_switched_versions"]["Case3"] = code_switched.get("Case3", None)
    result["code_switched_versions"]["Case4"] = code_switched.get("Case4", None)

    time.sleep(delay)

    return result, True

def process_mkqa_data_with_config(data: List[Dict[str, str]],
                                  model: str = "gpt-5-mini",
                                  delay: float = 0.1,
                                  save_interval: int = 10,
                                  output_dir: str = '.',
                                  num_threads: int = 5) -> Tuple[List[Dict], List[Dict]]:
    """Process MKQA data with custom configuration using multithreading.
    
    Returns:
        Tuple of (successful_results, removed_items)
    """

    indexed_data = list(enumerate(data))

    results_dict = {}
    removed_dict = {}
    results_lock = threading.Lock()

    pbar = tqdm(total=len(data), desc="Generating code-switched data")

    def process_with_progress(item_data):
        result, success = process_single_item(item_data, model, delay)

        with results_lock:
            if success:
                results_dict[result['id']] = result
            else:
                removed_dict[result['id']] = result
                
            pbar.update(1)
            pbar.set_postfix({
                'success': len(results_dict), 
                'failed': len(removed_dict)
            })

            if (len(results_dict) + len(removed_dict)) % save_interval == 0:
                sorted_results = [results_dict[i] for i in sorted(results_dict.keys())]
                sorted_removed = [removed_dict[i] for i in sorted(removed_dict.keys())]
                
                intermediate_file = os.path.join(output_dir, "code_switched_data_intermediate.json")
                removed_file = os.path.join(output_dir, "code_switched_data_removed_intermediate.json")
                
                save_results(sorted_results, intermediate_file)
                if sorted_removed:
                    save_removed_items(sorted_removed, removed_file)

        return result, success

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(process_with_progress, item) for item in indexed_data]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing item: {e}")

    pbar.close()

    results = [results_dict[i] for i in sorted(results_dict.keys())]
    removed_items = [removed_dict[i] for i in sorted(removed_dict.keys())]

    return results, removed_items

if __name__ == "__main__":
    main()