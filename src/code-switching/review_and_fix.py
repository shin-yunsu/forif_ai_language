#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code-switching 결과를 Gemini로 검수하고 수정하는 스크립트
"""

import json
import os
import argparse
import time
from typing import Dict, List, Tuple, Optional
import google.generativeai as genai
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
# Initialize Gemini client
genai.configure(api_key="AIzaSyAMNMMiAa_ILrjBlsymmgugDodY_5J9ue8")

def _fewshot_block() -> str:
    """프롬프트에 삽입할 few-shot 예시 블록 (입력/출력 페어 3개)"""
    return r""" 
# Few-shot Examples (Idle Reference)

## Example 1
ID 146
원문 KO : 살부타몰은 호흡기의 어느 부분에서 작동합니까  
원문 EN : salbutamol works in which area of the respiratory tract

Case 2  : 살부타몰은 respiratory tract의 어느 부분에서 작동합니까?  
Case 3  : 살부타몰은 respiratory tract의 어느 area에서 works 합니까?  
Case 4  : salbutamol은 호흡기의 어느 부분에서 works 합니까?  
Case 5  : salbutamol은 호흡기의 which part에서 works 합니까?  

---

## Example 2
ID 147
원문 KO : 버몬트에서 빨간 불에 우회전할 수 있나요  
원문 EN : can you turn right on a red light in vermont

Case 2  : 버몬트에서 can you turn right on a red light?  
Case 3  : Vermont에서 can you turn right on a red light?  
Case 4  : can you turn right on a 빨간 불 in 버몬트  
Case 5  : can you turn right on a 빨간 불 in vermont  

---

## Example 3
ID 1338
원문 KO : 인슐린 의존 당뇨병 환자를 위한 다이어트 계획에서 어떤 요소가 필수로 고려되나요?  
원문 EN : what factors are considered essential in the diet plan for the insulin dependent diabetic

Case 2  : 인슐린 의존 diabetic 환자를 위한 diet plan에서 어떤 요소가 필수로 고려되나요?  
Case 3  : insulin 의존 diabetic 환자를 위한 diet plan에서 어떤 factors가 essential하게 고려되나요?  
Case 4  : what 요소 are essential in the diet 계획 for the insulin 의존 당뇨병 환자  
Case 5  : what factors are essential in the diet plan for the 인슐린 의존 당뇨병 환자  

"""


def create_review_prompt(item: Dict) -> str:
    """검수 프롬프트 생성 (few-shot 포함)"""
    ko = item['original_ko']
    en = item['original_en']
    versions = item['code_switched_versions']

    case2 = versions.get('Case2', '')
    case3 = versions.get('Case3', '')
    case4 = versions.get('Case4', '')
    case5 = versions.get('Case5', '')

    fewshots = _fewshot_block()

    prompt = f"""당신은 한영 code-switching 품질 검수 전문가입니다.

## 원본
- 한국어: {ko}
- 영어: {en}

## 현재 생성된 결과
- Case2 (한국어 기반, 1~2개 영어): {case2}
- Case3 (한국어 기반, 3~4개 영어): {case3}
- Case4 (영어 기반, 3~4개 한국어): {case4}
- Case5 (영어 기반, 1~2개 한국어): {case5}

## 검수 기준
1. **점진적 변화**: Case2 < Case3 (한국어→영어 비율 증가), Case4 > Case5 (영어→한국어 비율 감소)
2. **Case 차별성**: 각 Case가 명확히 달라야 함
3. **동사 포함(자연스러움 우선)**: Case3, Case4에 동사 변환을 권장하되, *비자연스러운 혼용(ex. "works합니까?")은 금지*
4. **문장 기반**: Case2/3는 **한국어 문장 기반**, Case4/5는 **영어 문장 기반**을 유지
5. **맞춤법/하이픈**: 예) insulin-dependent

## 작업
아래 항목을 검수하고, **문제가 있으면** 수정된 버전을 제시하세요.
**문제가 없으면** "OK"만 출력하세요.

문제가 있는 경우 JSON 형식으로 출력:
{{
  "status": "NEEDS_FIX",
  "problems": ["문제1", "문제2"],
  "fixed": {{
    "Case2": "수정된 Case2",
    "Case3": "수정된 Case3",
    "Case4": "수정된 Case4",
    "Case5": "수정된 Case5"
  }}
}}

문제가 없는 경우:
{{
  "status": "OK"
}}

{fewshots}
"""
    return prompt

# (선택) 응답 파싱 보강: 빈 response.text 대비
def _safe_parse_json_response(response) -> Dict:
    try:
        if getattr(response, "text", None):
            return json.loads(response.text)
        # fallback: candidates에서 JSON 조각 찾기
        if getattr(response, "candidates", None):
            for cand in response.candidates:
                for part in getattr(cand, "content", {}).parts or []:
                    if getattr(part, "text", None):
                        try:
                            return json.loads(part.text)
                        except Exception:
                            continue
    except Exception:
        pass
    return {"status": "OK"}  # 파싱 실패 시 원본 유지

def review_and_fix_item(item: Dict, model_name: str = "gemini-2.5-flash-lite", delay: float = 0.0) -> Tuple[bool, Dict]:
    """
    단일 항목 검수 및 수정 (스레드 안전)
    Returns: (수정됨 여부, 수정된 항목)
    """
    try:
        prompt = create_review_prompt(item)
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 800,
                "response_mime_type": "application/json",
            },
        )
        response = model.generate_content(prompt)
        result = _safe_parse_json_response(response)

        if result.get("status") == "OK":
            if delay > 0:
                time.sleep(delay)
            return False, item

        elif result.get("status") == "NEEDS_FIX":
            fixed_versions = result.get("fixed", {})
            new_item = item.copy()
            new_versions = new_item["code_switched_versions"].copy()

            for case_name, fixed_value in fixed_versions.items():
                if fixed_value and fixed_value != new_versions.get(case_name):
                    new_versions[case_name] = fixed_value

            new_item["code_switched_versions"] = new_versions

            if delay > 0:
                time.sleep(delay)
            return True, new_item

        else:
            if delay > 0:
                time.sleep(delay)
            return False, item

    except Exception as e:
        print(f"❌ Error reviewing item {item.get('id', '?')}: {e}")
        if delay > 0:
            time.sleep(delay)
        return False, item

def main():
    parser = argparse.ArgumentParser(description="Code-switching 결과를 Gemini로 검수하고 수정합니다")

    parser.add_argument("--input", type=str, required=True, help="입력 JSON 파일 경로 (예: data/outputs/f_swapped.json)")
    parser.add_argument("--output", type=str, required=True, help="출력 JSON 파일 경로 (예: data/outputs/f_reviewed.json)")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash-lite",
                        choices=["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-1.5-flash"],
                        help="사용할 Gemini 모델")
    parser.add_argument("--delay", type=float, default=0.2, help="각 스레드 호출 후 대기 시간(초), rate smoothing용")
    parser.add_argument("--limit", type=int, default=None, help="처리할 항목 수 제한 (테스트용)")
    parser.add_argument("--workers", type=int, default=20, help="동시 스레드 수 (기본: 20)")

    args = parser.parse_args()

    # 입력 파일 확인
    if not os.path.exists(args.input):
        print(f"❌ Error: 입력 파일을 찾을 수 없습니다: {args.input}")
        return

    # JSON 읽기
    print(f"📖 Reading: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    if args.limit:
        data = data[:args.limit]
        print(f"   Limited to first {args.limit} items")

    print(f"   Total items: {len(data)}")
    print(f"   Model: {args.model}")
    print(f"   Workers: {args.workers}")
    print(f"   Per-call delay: {args.delay}s\n")

    # 멀티스레딩 처리: 입력 순서 유지 위해 (index, item)로 제출하고 결과를 same index에 저장
    print("🔍 Reviewing and fixing with multithreading...")
    reviewed_data: List[Optional[Dict]] = [None] * len(data)
    fixed_count = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(review_and_fix_item, item, args.model, args.delay): idx
            for idx, item in enumerate(data)
        }

        for fut in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            idx = futures[fut]
            try:
                was_fixed, reviewed_item = fut.result()
                reviewed_data[idx] = reviewed_item
                if was_fixed:
                    fixed_count += 1
            except Exception as e:
                print(f"❌ Future error at index {idx}: {e}")
                reviewed_data[idx] = data[idx]  # 원본 유지

    # None 방지 (이론상 없어야 하지만 안전망)
    for i, v in enumerate(reviewed_data):
        if v is None:
            reviewed_data[i] = data[i]

    # 결과 저장
    print(f"\n💾 Saving to: {args.output}")
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(reviewed_data, f, ensure_ascii=False, indent=2)

    # 요약
    total = len(data)
    print("\n" + "=" * 60)
    print("Review Summary")
    print("=" * 60)
    print(f"Total items processed: {total}")
    print(f"Items fixed: {fixed_count} ({(fixed_count/total*100 if total else 0):.1f}%)")
    print(f"Items unchanged: {total - fixed_count} ({(((total-fixed_count)/total*100) if total else 0):.1f}%)\n")


if __name__ == "__main__":
    main()