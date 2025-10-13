#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
개선된 Gemini Code-Switching Generator
- Case4-5에서 더 많은 핵심용어 교체
- 새로운 예시 추가
"""

import json
import os
from typing import List, Dict, Tuple
import google.generativeai as genai
from tqdm import tqdm
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
    """Improved prompt with better Case4-5 examples."""
    prompt = f"""당신은 한영 code-switching 전문가입니다. 아래 규칙을 따라 Case2~Case5를 생성하세요.

## 입력
- 한국어: {ko_text}
- 영어: {en_text}

## 핵심 규칙

### 1️⃣ 의문사는 절대 건드리지 마세요!
❌ "어디에서" → "where에서" (금지!)
❌ "무엇" → "what" (금지!)

의문사: 어디, 어디에서, 언제, 왜, 무엇, 누가, 어떤, 어떻게, where, when, why, what, who, which, how

### 2️⃣ 교체 가능한 것
✅ 명사: 사람, 장소, 사물 (예: 병원/hospital, 결합/bond)
✅ 동사: 행동 (예: 먹다/eat, 형성되다/form)
✅ 형용사: 성질 (예: 필수/essential)

### 3️⃣ 생성 방법

**Case2-3: 한국어 문장에서 명사/동사를 영어로**
- Case2: 1~2개 바꾸기
- Case3: 3~4개 바꾸기 (Case2보다 많이!)

**Case4-5: 영어 문장에서 명사/동사를 한국어로**
- Case4: 2~3개 바꾸기
- Case5: 4~5개 바꾸기 (Case4보다 확실히 많이!)
- **중요**: 고유명사만 아니라 일반 명사/동사/형용사도 적극적으로 바꾸세요!

## 예시

### 예시 1: 과학 용어 (핵심!)
입력:
- 한국어: 두 뉴클레오타이드 사이에 공유 결합은 어디에서 형성되나요
- 영어: where do covalent bonds form between two nucleotides

출력:
{{
  "Case2": "두 nucleotides 사이에 covalent bonds는 어디에서 형성되나요",
  "Case3": "두 nucleotides 사이에 covalent bonds는 어디에서 form되나요",
  "Case4": "where do 공유 결합 form between two 뉴클레오타이드",
  "Case5": "where do 공유 결합 형성 between two 뉴클레오타이드"
}}

### 예시 2: 의학 용어
입력:
- 한국어: 인슐린 의존 당뇨병 환자를 위한 계획에서 어떤 요소가 필수인가요?
- 영어: What factors are essential in the plan for insulin-dependent diabetic patients?

출력:
{{
  "Case2": "insulin 의존 diabetes 환자를 위한 plan에서 어떤 요소가 필수인가요?",
  "Case3": "insulin-dependent diabetes patients를 위한 plan에서 어떤 factors가 essential인가요?",
  "Case4": "What factors are 필수 in the 계획 for insulin-dependent 당뇨병 patients?",
  "Case5": "What 요소 are 필수 in the 계획 for insulin-dependent 당뇨병 환자?"
}}

### 예시 3: 역사
입력:
- 한국어: 누가 DDT의 속성에 관한 연구로 노벨상을 받았나요?
- 영어: who won the nobel prize for work on the properties of ddt

출력:
{{
  "Case2": "누가 DDT의 properties에 관한 research로 nobel prize를 받았나요?",
  "Case3": "누가 DDT의 properties에 관한 work로 nobel prize를 won했나요?",
  "Case4": "who won the 노벨상 for work on the 속성 of DDT?",
  "Case5": "who won the 노벨상 for 연구 on the 속성 of DDT?"
}}

### 예시 4: 의문사 보존
입력:
- 한국어: 제1차 세계 대전은 어디에서 일어났나요?
- 영어: where did the first world war take place

출력:
{{
  "Case2": "제1차 World War는 어디에서 일어났나요?",
  "Case3": "First World War는 어디에서 take place했나요?",
  "Case4": "where did the 제1차 세계 대전 take place?",
  "Case5": "where did the 제1차 세계 대전 일어났나요?"
}}

## 실제 작업
JSON만 출력하세요:

{{
  "Case2": "...",
  "Case3": "...",
  "Case4": "...",
  "Case5": "..."
}}
"""
    return prompt

def validate_code_switching(ko_text: str, en_text: str, result: Dict[str, str]) -> bool:
    """Validate with relaxed rules."""
    if not result:
        return False

    for i in [2, 3, 4, 5]:
        if f"Case{i}" not in result or result[f"Case{i}"] is None:
            return False

    case2, case3, case4, case5 = result["Case2"], result["Case3"], result["Case4"], result["Case5"]

    # Check mixed interrogatives
    en_interrogatives = ["where", "when", "why", "what", "who", "which", "how"]
    for case_text, case_name in [(case2, "Case2"), (case3, "Case3")]:
        for en_int in en_interrogatives:
            if f"{en_int}에서" in case_text.lower() or f"{en_int}인가요" in case_text.lower():
                print(f"❌ {case_name}: '{en_int}' mixed with Korean")
                return False

    # Check uniqueness
    if case2 == case3 or case4 == case5 or case4 == en_text:
        print(f"❌ Cases are identical")
        return False

    # Check Korean presence
    import re
    if not re.search(r'[가-힣]', case4) or not re.search(r'[가-힣]', case5):
        print(f"❌ Case4/5 missing Korean")
        return False

    return True

def generate_code_switched_text(ko_text: str, en_text: str,
                               model_name: str = "gemini-2.5-flash-lite") -> Dict[str, str]:
    """Generate code-switching with validation."""
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

        if not all(result.get(f"Case{i}", "") for i in [2, 3, 4, 5]):
            return None

        if not validate_code_switching(ko_text, en_text, result):
            print(f"⚠️ Validation failed: {ko_text[:50]}...")
            return None

        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def save_results(results: List[Dict], output_file: str):
    """Save results."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(results)} items to {output_file}")

def process_single_item(item_data: tuple, model: str, delay: float) -> Tuple[Dict, bool]:
    """Process single item."""
    idx, item = item_data

    result = {
        "id": idx,
        "original_ko": item['ko'],
        "original_en": item['en'],
        "code_switched_versions": {}
    }

    code_switched = generate_code_switched_text(item['ko'], item['en'], model_name=model)

    if code_switched is None:
        result["code_switched_versions"] = {
            "Case1": item['ko'],
            "Case2": None,
            "Case3": None,
            "Case4": None,
            "Case5": None,
            "Case6": item['en']
        }
        time.sleep(delay)
        return result, False

    result["code_switched_versions"] = {
        "Case1": item['ko'],
        "Case2": code_switched["Case2"],
        "Case3": code_switched["Case3"],
        "Case4": code_switched["Case4"],
        "Case5": code_switched["Case5"],
        "Case6": item['en']
    }

    time.sleep(delay)
    return result, True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--model", type=str, default="gemini-2.5-flash-lite")
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()

    print(f"📋 Loading: {args.input}")
    data = load_mkqa_data(args.input)
    print(f"✅ Loaded {len(data)} items\n")

    results_dict = {}
    removed_dict = {}
    lock = threading.Lock()

    pbar = tqdm(total=len(data), desc="Processing")

    def process_with_progress(item_data):
        result, success = process_single_item(item_data, args.model, args.delay)
        with lock:
            if success:
                results_dict[result['id']] = result
            else:
                removed_dict[result['id']] = result
            pbar.update(1)
            pbar.set_postfix({'✅': len(results_dict), '❌': len(removed_dict)})
        return result, success

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [executor.submit(process_with_progress, (i, item)) for i, item in enumerate(data)]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"❌ Error: {e}")

    pbar.close()

    results = [results_dict[i] for i in sorted(results_dict.keys())]
    removed = [removed_dict[i] for i in sorted(removed_dict.keys())]

    save_results(results, args.output)
    if removed:
        save_results(removed, args.output.replace('.json', '_removed.json'))

    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"{'='*60}")
    print(f"Total: {len(data)}")
    print(f"✅ Success: {len(results)} ({len(results)/len(data)*100:.1f}%)")
    print(f"❌ Failed: {len(removed)}")

if __name__ == "__main__":
    main()
