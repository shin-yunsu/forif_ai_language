#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from typing import List, Dict, Tuple
import google.generativeai as genai
from tqdm import tqdm
import random
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Initialize Gemini client
genai.configure(api_key="AIzaSyAMNMMiAa_ILrjBlsymmgugDodY_5J9ue8")

def load_mkqa_data(file_path: str) -> List[Dict[str, str]]:
    """Load MKQA data from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
def create_code_switching_prompt(ko_text: str, en_text: str) -> str:
    """Simple, clear code-switching prompt."""
    prompt = f"""당신은 한영 code-switching 전문가입니다. 아래 규칙을 따라 Case2~Case5를 생성하세요.

## 입력
- 한국어: {ko_text}
- 영어: {en_text}

## 핵심 규칙

### 2️⃣ 교체 가능한 것
✅ 명사: 사람, 장소, 사물 (예: 병원/hospital, 학생/student)
✅ 동사: 행동 (예: 먹다/eat, 가다/go)
✅ 고유명사: 이름, 지명 (예: 서울/Seoul)
✅ 형용사: 성질 (예: 빠른/fast, 중요한/important)

### 3️⃣ 생성 방법

**Case2-3: 한국어 문장에서 명사/동사를 영어로 바꾸기**
- Case2: 1~2개 바꾸기
- Case3: 3~4개 바꾸기 - Case2보다 많이!
- 한국어 어순 유지
- 하이브리드 OK: "go하다", "eat했어요"
- **긴 문장일수록 더 많은 단어를 바꾸세요!**

**Case4-5: 영어 문장에서 명사/동사를 한국어로 바꾸기**
- Case4: 1~2개 바꾸기 
- Case5: 3~4개 바꾸기 - Case4보다 많이!
- 영어 어순 유지
- **중요**: 
  - 일반 명사/동사/형용사를 적극적으로 바꾸세요!
  - **동사는 반드시 포함**: happened→일어났, traded→거래했, build→건설
  - **긴 문장일수록 더 많은 단어를 바꾸세요!**

## 예시

### 예시 1
입력:
- 한국어: 스펙트럼에서 ACC 네트워크는 어떤 채널인가요?
- 영어: what channel is the acc network on spectrum

출력:
{{
    "Case2": "스펙트럼에서 ACC network는 어떤 채널인가요?",
    "Case3": "spectrum에서 ACC network는 어떤 채널인가요?",
    "Case4": "what channel is the acc 네트워크 on spectrum",
    "Case5": "what 채널 is the acc 네트워크 on 스펙트럼"
}}


### 예시 2
입력:
- 한국어: 인슐린 의존 당뇨병 환자를 위한 계획에서 어떤 요소가 필수인가요?
- 영어: What factors are essential in the plan for insulin-dependent diabetic patients?

출력:
{{
  "Case2": "insulin 의존 diabetes 환자를 위한 plan에서 어떤 요소가 필수인가요?",
  "Case3": "insulin-dependent diabetes patients를 위한 plan에서 어떤 factors가 essential인가요?",
  "Case4": "What factors are 필수 in the plan for 인슐린 의존 diabetes patients?",
  "Case5": "What factors are 필수 in the 계획 for 인슐린 의존 당뇨병 환자?"
}}

### 예시 3 
입력:
- 한국어: 1941년 소련의 침공 이후 어떤 일이 일어났나요?
- 영어: what happened following the invasion of the soviet union in 1941

출력:
{{
  "Case2": "1941년 Soviet Union의 invasion 이후 어떤 일이 일어났나요?",
  "Case3": "1941년 Soviet Union의 invasion 이후 어떤 events가 happened?",
  "Case4": "what happened following the 침공 of the 소련 in 1941?",
  "Case5": "what happened 이후 the 소련 침공 in 1941?"
}}


## 실제 작업
이제 위 입력에 대해 Case2, Case3, Case4, Case5를 생성하세요.
JSON만 출력하세요 (설명 없이):

{{
  "Case2": "...",
  "Case3": "...",
  "Case4": "...",
  "Case5": "..."
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
    for i in [2, 3, 4, 5]:
        if f"Case{i}" not in result or result[f"Case{i}"] is None:
            return False
    
    # Extract cases
    case2 = result["Case2"]
    case3 = result["Case3"]
    case4 = result["Case4"]
    case5 = result["Case5"]
    
    # 2. Check all cases are different
    if case2 == case3:
        print(f"❌ Validation failed: Case2 == Case3")
        return False
    if case4 == case5:
        print(f"❌ Validation failed: Case4 == Case5")
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
    
    # Case4-5: 매우 느슨한 체크 (한국어가 있기만 하면 OK)
    ko_case4 = count_korean_chars(case4)
    ko_case5 = count_korean_chars(case5)
    
    if ko_case4 == 0 or ko_case5 == 0:
        print(f"❌ Validation failed: Case4 or Case5 has no Korean")
        return False
    
    return True

def generate_code_switched_text(ko_text: str, en_text: str,
                               model_name: str = "gemini-2.5-flash-lite") -> Dict[str, str]:
    """Generate all code-switching levels using Gemini."""

    prompt = create_code_switching_prompt(ko_text, en_text)

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 500,
                "response_mime_type": "application/json"
            }
        )
        
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        
        # 빈 결과가 있으면 실패로 간주
        if not all(result.get(f"Case{i}", "") for i in [2, 3, 4, 5]):
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
        default="gemini-2.5-flash-lite",
        choices=["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-1.5-flash"],
        help="Gemini model to use for generation"
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

    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Please set it using: export GEMINI_API_KEY='your-api-key'")
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
        result["code_switched_versions"]["Case1"] = ko_text
        result["code_switched_versions"]["Case2"] = None
        result["code_switched_versions"]["Case3"] = None
        result["code_switched_versions"]["Case4"] = None
        result["code_switched_versions"]["Case5"] = None
        result["code_switched_versions"]["Case6"] = en_text
        time.sleep(delay)
        return result, False
    
    # Add Case1 (pure Korean) and Case6 (pure English)
    result["code_switched_versions"]["Case1"] = ko_text
    result["code_switched_versions"]["Case2"] = code_switched.get("Case2", None)
    result["code_switched_versions"]["Case3"] = code_switched.get("Case3", None)
    result["code_switched_versions"]["Case4"] = code_switched.get("Case4", None)
    result["code_switched_versions"]["Case5"] = code_switched.get("Case5", None)
    result["code_switched_versions"]["Case6"] = en_text

    time.sleep(delay)

    return result, True

def process_mkqa_data_with_config(data: List[Dict[str, str]],
                                  model: str = "gemini-2.5-flash-lite",
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