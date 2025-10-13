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
    """Natural code-switching (Levels 2/3/4/5) with strict token-growth rules.
    Multiword proper nouns can be revealed in stages (e.g., 'Boston' → 'Boston 학살' → 'Boston Massacre').
    """
    prompt = f"""다음 문장 쌍에 대해 Case2, Case3, Case4, Case5의 code-switching 버전을 생성하세요.

---
## 핵심 원칙

### Case2-3 (한국어 어순 유지)
1. **한국어 어순·종결어미 유지**
2. **의문사(언제/왜/어디/무엇/어떻게/누구)는 절대 영어로 교체 금지** ← 매우 중요!
3. 영어 동사+한국어 어미 결합 가능 (예: "die하나요", "shot되나요", "fight했나요")
4. 영어 명사/형용사/부사/고유명사로 점진 교체

### Case4-5 (영어 어순 전환)
1. **en_text 기준으로 작업** (같으면 안됨)
2. **Case4 ≠ Case5, Case4 ≠ en_text 필수** (완전히 동일하면 안됨) ← 매우 중요!
3. Case4는 일부 한국어 핵심용어 포함(1~2개), Case5는 Case4에서 + 여러개
4. Case4 -> Case5에서 the 만 붙이는 것 금지


---
## 단계별 진행
- **Case2**: 1~2개 영어 단어로 교체 (Case2 ≠ Case1 필수)
- **Case3**: Case2 + 1~2개 더 추가 (Case3 ≠ Case2 필수)
- **Case4**: 영어 어순 기준으로 + 1~2개 한국어로 교체 (Case4 ≠ en_text 필수)
- **Case5**: Case4에서 한국어 여러개 추가 (Case5 ≠ Case4 필수)

---
## 검증 (자동 실패 조건)
1. **Case2 = Case3** → 실패
2. **Case4 = Case5** → 실패 (완전히 동일하면 안됨)
3. **Case4 = en_text 또는 Case4가 en_text와 대소문자만 다름** → 실패
   - Case4는 반드시 한국어 용어 1~3개 유지 필수 (예: "커틀러 베켓", "변압기", "산들", "나라")
4. 바꿀 핵심용어나 단어가 부족하여 Case들끼리 달라질 수가 없으면 **null**로 출력

---
## Few-shot 보강 예시

### 예시 A (점진적 교체 + 영어 어순 전환)
입력:
- 한국어: 인슐린 의존 당뇨병 환자를 위한 다이어트 계획에서 어떤 요소가 필수로 고려되나요?
- 영어: what factors are considered essential in the diet plan for the insulin dependent diabetic
출력:
{{
  "Case2": "insulin dependent diabetic를 위한 다이어트 계획에서 어떤 요소가 필수로 고려되나요?",
  "Case3": "insulin dependent diabetic를 위한 diet plan에서 어떤 요소가 필수로 고려되나요?",
  "Case4": "what factors are considered essential in the diet plan for the 인슐린 의존 당뇨병 환자",
  "Case5": "what 요소 are considered 필수적 in the 다이어트 계획 for the 인슐린 의존 당뇨병 환자"
}}
# 설명: Case2-3은 한국어 어순 유지, Case4는 영어 어순+ 일부 한국어 핵심 용어, Case5는 영어 어순+ 더 많은 한국어 핵심 용어

### 예시 B 
입력:
- 한국어: 반지의 제왕에서 보르미르는 어디에서 죽나요?
- 영어: where does boromir die in lord of the rings
출력:
{{
  "Case2": "반지의 제왕에서 Boromir는 어디에서 죽나요?",
  "Case3": "반지의 제왕에서 Boromir는 어디에서 die하나요?",
  "Case4": "where does 보르미르 die in Lord of the Rings",
  "Case5": "where does 보르미르 die in the 반지의 제왕"
}}
# 설명 Case2 -> 3 는 점진적으로 영어 증가, Case4 -> 5 는 점진적으로 한국어 증가

### 예시 C (Case4 ≠ Case5 필수)
입력:
- 한국어: 시카고 PD에서 에린 린제이는 어느 에피소드에서 총에 맞나요?
- 영어: what episode does erin lindsay get shot in chicago pd
출력:
{{
  "Case2": "시카고 PD에서 Erin Lindsay는 어느 에피소드에서 총에 맞나요?",
  "Case3": "Chicago PD에서 Erin Lindsay는 어느 episode에서 shot되나요?",
  "Case4": "what episode does Erin Lindsay get shot in 시카고 PD",
  "Case5": "what 에피소드 does 에린 린제이 get shot in 시카고 PD"
}}

### 예시 D (Case4-5는 문법적으로 완전한 영어 문장)
입력:
- 한국어: 고대 그리스 연극에서 코러스의 네 가지 다른 역할은 무엇인가요?
- 영어: four different roles of the chorus in an ancient greek play
출력:
{{
  "Case2": "고대 그리스 연극에서 chorus의 네 가지 다른 역할은 무엇인가요?",
  "Case3": "고대 그리스 연극에서 chorus의 four different roles는 무엇인가요?",
  "Case4": "what are the four different roles of the 코러스 in an ancient 그리스 연극",
  "Case5": "what are the 네 가지 다른 역할 of the 코러스 in an ancient 그리스 연극"
}}

### 예시 E (합성 고유명사 단계적 노출)
입력:
- 한국어: 보스턴 학살에 얼마나 많은 영국 군인이 있었나요?
- 영어: how many redcoats were at the boston massacre
출력:
{{
  "Case2": "보스턴 학살에 얼마나 많은 redcoats가 있었나요?",
  "Case3": "Boston Massacre에 얼마나 많은 redcoats가 있었나요?",
  "Case4": "how many 영국 군인 were at the Boston Massacre",
  "Case5": "how many 영국 군인 were at the 보스턴 학살"
}}
# 설명: Case2-3은 한국어 어순, Case4는 영어 어순+ 일부 한국어 전환, Case5는 더 많은 한국어 전환

### 예시 F (Case5는 반드시 최소 1개 한국어 용어 유지)
입력:
- 한국어: 센터 탭 변압기의 기능은 무엇인가요?
- 영어: what is the function of center tap transformer
출력:
{{
  "Case2": "센터 탭 transformer의 기능은 무엇인가요?",
  "Case3": "센터 탭 transformer의 function은 무엇인가요?",
  "Case4": "what is the function of center tap 변압기",
  "Case5": "what is the 기능 of center tap 변압기"
}}

### 예시 G (형용사 자연스러운 배치 + Case4 ≠ Case5)
입력:
- 한국어: 왜 어떤 나라들은 자연 증가율을 줄이는 것을 원하지 않을까요?
- 영어: why a country may not want to reduce its rate of natural increase
출력:
{{
  "Case2": "어떤 나라들은 natural increase rate를 줄이는 것을 왜 원하지 않을까요?",
  "Case3": "어떤 countries는 natural increase rate를 reduce하는 것을 왜 원하지 않을까요?",
  "Case4": "why a country may not want to reduce its 자연 증가율",
  "Case5": "why a 나라 may not want to reduce its 자연 증가율"
}}

예시 H 
입력:
- 한국어: 휘그당 통치에 반대하기 위해 형성된 민주당의 첫 번째 지도자는 누구였나요?
- 영어: who was the first leader of the democratic party that was formed to oppose the governing whig party
출력:
{{
  "Case2": "휘그당 통치에 반대하기 위해 형성된 Democratic Party의 첫 번째 지도자는 누구였나요?",
  "Case3": "휘그당 통치에 반대하기 위해 formed된 Democratic Party의 first leader는 누구였나요?",
  "Case4": "who was the first leader of the 민주당 that was formed to oppose the governing 휘그당",
  "Case5": "who was the 첫 번째 지도자 of the 민주당 that was formed to oppose the governing 휘그당"
}}

예시 I (null 표기)
입력:
- 한국어: 성 '웰스'는 어디에서 유래했나요?
- 영어: where did the last name wells come from
출력:
{{
  "Case2": null,
  "Case3": null,
  "Case4": null,
  "Case5": null
}}
# 설명: 바꿀 핵심용어가 부족하여 null로 표기.

---
## 실제 입력
- 한국어: {ko_text}
- 영어: {en_text}

## 최종 출력(JSON만):
{{
  "Case2": "Level 2 버전 또는 null",
  "Case3": "Level 3 버전 또는 null",
  "Case4": "Level 4 버전 또는 null",
  "Case5": "Level 5 버전 또는 null"
}}
"""
    return prompt



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