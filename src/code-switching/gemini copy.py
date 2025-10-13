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
    """Generate code-switching (Levels 2/3/4) that preserves Korean syntax and swaps only key content terms into English, with clear anti-awkwardness rules and deduplication guarantees."""
    prompt = f"""다음 문장 쌍에 대해 Level 2, 3, 4의 code-switching 버전을 생성하세요.
목표: **한국어 문장 구조는 그대로 유지**하고, **핵심 용어(내용어: 명사·동사·형용사·부사·전문용어·고유명사)**만 단계적으로 영어로 교체합니다.

---
## 1) 기본 원칙
- 한국어 문장(ko_text)의 **어순·종결어미(평서/의문/명령/청유)**는 유지합니다.
- 영어 문장(en_text)은 **용어 대응(term mapping) 참고용**으로만 사용합니다. 이걸 바탕으로 생성하지 마세요.
- 교체 대상은 **핵심 용어**만입니다. 기능어(숫자, 조사, 접속사 등)는 신경 쓰지 않습니다.

---
## 2) 금지 규칙 (어색한 혼합 방지)
- **영문 어순 전환 금지**: SVO식 재배열 금지. 한국어 어순 유지.
- **문체 일관성**: 존댓말/반말, 의문형/평서형은 ko_text와 동일하게 유지.
- **관용구/복합명사 쪼개기 금지**: 하나의 단위는 통째로 교체(예: "break a leg", "critical word first").

---
## 3) 명명 및 표기 규칙 (고유명사/작품/브랜드)
- **작품 제목**: **공식 영문 제목**(가능하면 대문자 표기) 유지 (예: *The Office*, *The Fly*).  
- **약어**: en_text 기준을 따르되, 이미 널리 쓰이는 표기면 그대로 유지(예: ACC).

> 의미 보존 주의: "파리(Paris)"와 "The Fly(영화)"처럼 **동음/오역 가능성**이 있으면 en_text를 참고해 올바른 고유명사를 선택.

---
## 4) 단계별 전환 규칙 (필수)
**중요**: 각 Case는 **반드시 다른 Case와 구별**되어야 하며, **점진적으로 영어 비율이 증가**해야 합니다.

### Case2 (10~20% 교체)
- **필수**: 교체된 영어 단어가 **최소 1개 이상**
- **우선순위**: 고유명사(인명, 지명, 작품명) → 전문용어
- **검증**: Case1(순수 한국어)과 반드시 달라야 함

### Case3 (33~40% 교체)
- **필수**: Case2에서 교체한 단어 **+ 추가로 1~2개 이상**
- **우선순위**: Case2의 모든 단어 유지 + 핵심 명사/동사 추가
- **검증**: Case2 ⊂ Case3 (Case2의 모든 영어 단어 포함 + 추가 단어 있어야 함)

### Case4 (45~55% 교체)
- **필수**: Case3에서 교체한 단어 **+ 추가로 1~2개 이상**
- **우선순위**: Case3의 모든 단어 유지 + 형용사/부사/동사 추가
- **검증**: Case3 ⊂ Case4 (Case3의 모든 영어 단어 포함 + 추가 단어 있어야 함)

---
## 5) 중복 방지 규칙 (엄격 적용)
**다음 조건을 모두 만족해야 합니다:**

1. **포함 관계**: Case2에 사용된 영어 단어 ⊆ Case3 ⊆ Case4
2. **증가 보장**: 영어 단어 개수가 Case2 < Case3 < Case4 (각각 최소 1개씩 증가)
3. **중복 금지**: Case2 = Case3, Case3 = Case4, Case2 = Case4인 경우 **절대 불가**
4. **검증 실패 시**: 위 조건 중 하나라도 만족 못하면 **Case2, Case3, Case4 모두 null**

---
## 6) `null` 처리 규칙 (필수)
아래 조건 중 **하나라도** 만족하면 **Case2/Case3/Case4는 모두 `null`**을 출력하세요:

- 교체 가능한 **핵심 용어가 2개 미만**
- 한국어 문장이 **너무 짧아서**(5어절 미만) 단계별 전환이 불가능한 경우

---
## 7) 생성 절차(내부 지침)
1) ko_text에서 **교체 가능한 핵심 용어 후보 리스트**를 작성 (최소 4~5개 필요)
2) en_text로 각 후보의 **자연스러운 영어 대응어**를 매핑
3) **Case2**: 후보 중 1~2개 선택 (고유명사/전문용어 우선)
4) **Case3**: Case2의 단어 **+ 추가 1~2개**
5) **Case4**: Case3의 단어 **+ 추가 1~2개**
6) **검증**: Case2 ≠ Case3 ≠ Case4 확인 → 실패 시 **모두 null**
7) 금지 규칙(§2)과 명명 규칙(§3) 위배 여부 **자가 점검**

---
## 8) 출력 형식
- **오직 JSON만** 출력하십시오. 키는 "Case2", "Case3", "Case4"입니다.
- `null`을 출력해야 하는 경우, 세 값 모두 `null`로 설정하세요.
- **설명이나 주석 추가 금지**

---
## Few-shot 예시

### 예제 1
입력:
- 한국어: 스펙트럼에서 ACC 네트워크는 어떤 채널인가요?
- 영어: what channel is the acc network on spectrum
출력:
{{
  "Case2": "스펙트럼에서 ACC network는 어떤 채널인가요?",
  "Case3": "spectrum에서 ACC network는 어떤 채널인가요?",
  "Case4": "spectrum에서 ACC network는 어떤 channel인가요?"
}}

### 예제 2
입력:
- 한국어: 미터법에서 측정 단위는 무엇인가요
- 영어: what are the units of measurement in the metric system

출력:
{{
  "Case2": "metric system에서 측정 단위는 무엇인가요",
  "Case3": "metric system에서 측정 units은 무엇인가요",
  "Case4": "metric system에서 units of measurement는 what 인가요"
}}

### 예제 3
입력:
- 한국어: 미국의 수정 헌법을 보여줘요.
- 영어: show me the amendments of the united states

출력:
{{
  "Case2": "america의 수정 헌법을 보여줘요.",
  "Case3": "america의 amendments를 보여줘요.",
  "Case4": "america의 amendments를 show me"
}}


### 예제 4 (점진적 증가 보장)
입력:
- 한국어: 영화 '보니와 클라이드'에 누가 출연했나요?
- 영어: who starred in the movie bonnie and clyde

출력:
{{
  "Case2": "영화 'Bonnie and Clyde'에 누가 출연했나요?",
  "Case3": "movie 'Bonnie and Clyde'에 누가 출연했나요?",
  "Case4": "movie 'Bonnie and Clyde'에 누가 starred 했나요?"
}}

---
## 실제 입력
- 한국어: {ko_text}
- 영어: {en_text}

## 최종 출력(JSON만):
{{
  "Case2": "Level 2 버전 또는 null",
  "Case3": "Level 3 버전 또는 null",
  "Case4": "Level 4 버전 또는 null"
}}
"""
    return prompt


def generate_code_switched_text(ko_text: str, en_text: str,
                               model_name: str = "gemini-2.5-flash") -> Dict[str, str]:
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
        if not all(result.get(f"Case{i}", "") for i in [2, 3, 4]):
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
        choices=["gemini-2.5-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"],
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
        result["code_switched_versions"]["Case5"] = en_text
        time.sleep(delay)
        return result, False
    
    # Add Case1 (pure Korean) and Case5 (pure English)
    result["code_switched_versions"]["Case1"] = ko_text
    result["code_switched_versions"]["Case2"] = code_switched.get("Case2", None)
    result["code_switched_versions"]["Case3"] = code_switched.get("Case3", None)
    result["code_switched_versions"]["Case4"] = code_switched.get("Case4", None)
    result["code_switched_versions"]["Case5"] = en_text

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