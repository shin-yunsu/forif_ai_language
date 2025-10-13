#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code-switching 결과(Case2~Case5)를 Gemini로 '검수 및 자동수정'하는 스크립트
- 입력: [{id, original_ko, original_en, code_switched_versions{Case2..Case5}} ...] 형태 JSON
- 출력: 수정 반영된 JSON (status OK면 그대로, NEEDS_FIX면 fixed 반영)
- 멀티스레딩 기본 20
- 환경변수: GEMINI_API_KEY
"""

import os
import re
import json
import time
import argparse
import threading
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import google.generativeai as genai
from tqdm import tqdm


# -------------------------------
# Thread-local Gemini model
# -------------------------------
_thread_local = threading.local()

def get_thread_model(model_name: str):
    """스레드별로 초기화된 GenerativeModel 반환 (thread-safe)."""
    key = f"__model_{model_name}"
    mdl = getattr(_thread_local, key, None)
    if mdl is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        genai.configure(api_key=api_key)
        mdl = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 900,
                "response_mime_type": "application/json",
            },
        )
        setattr(_thread_local, key, mdl)
    return mdl


# -------------------------------
# Few-shot (with Ideal Output)
# -------------------------------
def _fewshot_block() -> str:
    """검수자가 따라야 하는 기준을 분명히 학습시키는 입력/이상적 출력 페어."""
    return r"""
# Few-shot Examples (Input → Ideal Output)

## Example 1 (Input)
원본:
- 한국어: 살부타몰은 호흡기의 어느 부분에서 작동합니까
- 영어: salbutamol works in which area of the respiratory tract
현재 생성된 결과:
- Case2: 살부타몰은 respiratory tract의 어느 부분에서 작동합니까?
- Case3: 살부타몰은 respiratory tract의 어느 area에서 works합니까?
- Case4: salbutamol은 호흡기의 어느 부분에서 works합니까?
- Case5: salbutamol은 호흡기의 which part에서 works합니까?

검수 기준 요약:
- Case2/3: 한국어 기반 문장
- Case4/5: 영어 기반 문장
- 동사 변환은 자연스러울 때만. "works합니까?" 같은 혼종 금지
- Case2 < Case3 (영어 비율 증가), Case4 > Case5 (한국어 비율 증가)

### Example 1 (Ideal Output)
{
  "status": "NEEDS_FIX",
  "problems": [
    "Case3, Case4, Case5에서 혼종 동사(works합니까?)",
    "Case4/5가 영어 기반 문장을 충분히 따르지 않음"
  ],
  "fixed": {
    "Case2": "살부타몰은 respiratory tract의 어느 부분에서 작용합니까?",
    "Case3": "살부타몰은 respiratory tract의 어느 region에서 작용하나요?",
    "Case4": "Which part of the respiratory tract does salbutamol act on?",
    "Case5": "In the respiratory tract, which part does salbutamol act on?"
  }
}

---

## Example 2 (Input)
원본:
- 한국어: 버몬트에서 빨간 불에 우회전할 수 있나요
- 영어: can you turn right on a red light in vermont
현재 생성된 결과:
- Case2: 버몬트에서 can you turn right on a red light?
- Case3: Vermont에서 can you turn right on a red light?
- Case4: can you turn right on a 빨간 불 in 버몬트
- Case5: can you turn right on a 빨간 불 in vermont

### Example 2 (Ideal Output)
{
  "status": "NEEDS_FIX",
  "problems": [
    "Case2/3가 한국어 기반 구조를 유지하지 않음",
    "Case4/5의 한국어 삽입은 가능하나 영어 기반 구조를 더 명확히 유지 필요"
  ],
  "fixed": {
    "Case2": "버몬트에서 red light에서 우회전할 수 있나요?",
    "Case3": "Vermont에서 red light에서 right turn이 가능한가요?",
    "Case4": "Can you turn right on a red light in Vermont?",
    "Case5": "Can you turn right on a red light in 버몬트?"
  }
}

---

## Example 3 (Input)
원본:
- 한국어: 인슐린 의존 당뇨병 환자를 위한 다이어트 계획에서 어떤 요소가 필수로 고려되나요?
- 영어: what factors are considered essential in the diet plan for the insulin dependent diabetic
현재 생성된 결과:
- Case2: 인슐린 의존 diabetic 환자를 위한 diet plan에서 어떤 요소가 필수로 고려되나요?
- Case3: insulin 의존 diabetic 환자를 위한 diet plan에서 어떤 factors가 essential하게 고려되나요?
- Case4: what 요소 are essential in the diet 계획 for the insulin 의존 당뇨병 환자
- Case5: what factors are essential in the diet plan for the 인슐린 의존 당뇨병 환자

### Example 3 (Ideal Output)
{
  "status": "NEEDS_FIX",
  "problems": [
    "Case4에서 영어 기반 문장에 한국어 핵심어 과다 혼입",
    "insulin-dependent 하이픈 규칙 불일치"
  ],
  "fixed": {
    "Case2": "인슐린 의존 diabetic 환자를 위한 diet plan에서 어떤 요소가 필수로 고려되나요?",
    "Case3": "insulin-dependent diabetic 환자를 위한 diet plan에서 어떤 factors가 essential하게 고려되나요?",
    "Case4": "What factors are essential in the diet plan for the insulin-dependent diabetic?",
    "Case5": "What factors are essential in the diet plan for the 인슐린 의존 당뇨병 환자?"
  }
}
"""


# -------------------------------
# Prompt Builder (검수 프롬프트)
# -------------------------------
def create_review_prompt(item: Dict) -> str:
    """단일 항목 검수 프롬프트 생성 (few-shot 포함)."""
    ko = item.get("original_ko", "")
    en = item.get("original_en", "")
    versions = item.get("code_switched_versions", {}) or {}

    case2 = versions.get("Case2", "")
    case3 = versions.get("Case3", "")
    case4 = versions.get("Case4", "")
    case5 = versions.get("Case5", "")

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
1. 점진적 변화: Case2 < Case3 (한국어→영어 비율 증가), Case4 > Case5 (영어→한국어 비율 감소)
2. Case 차별성: 각 Case는 명확히 달라야 함
3. 동사 변환은 자연스러울 때만 권장. "works합니까?" 등 혼종 금지
4. 문장 기반: Case2/3는 한국어 문장, Case4/5는 영어 문장 기반 유지
5. 맞춤법/표기: 예) insulin-dependent

## 작업
아래 항목을 검수하고, 문제가 있으면 수정안을 JSON으로 제시하세요.
문제가 없으면 "OK"만 출력하세요.

문제가 있는 경우 JSON 형식:
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


# -------------------------------
# Robust JSON parsing helpers
# -------------------------------
def _try_json_loads(text: Optional[str]) -> Optional[Dict]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None

def parse_model_json(response) -> Optional[Dict]:
    """response.text 우선, 실패 시 candidates.parts에서 JSON 추출."""
    if getattr(response, "text", None):
        obj = _try_json_loads(response.text)
        if obj is not None:
            return obj

    if getattr(response, "candidates", None):
        for cand in response.candidates:
            content = getattr(cand, "content", None)
            if content and getattr(content, "parts", None):
                for part in content.parts:
                    txt = getattr(part, "text", None)
                    obj = _try_json_loads(txt)
                    if obj is not None:
                        return obj

    return None


# -------------------------------
# Apply Fixes
# -------------------------------
def apply_fixes_to_item(item: Dict, fix_payload: Dict) -> Tuple[bool, Dict]:
    """
    fix_payload: {"status": "NEEDS_FIX", "fixed": {...}}
    반환: (was_fixed, new_item)
    """
    if not fix_payload or fix_payload.get("status") != "NEEDS_FIX":
        return False, item

    fixed_versions = (fix_payload.get("fixed") or {})
    new_item = dict(item)
    versions = dict(new_item.get("code_switched_versions", {}) or {})

    changed = False
    for case in ["Case2", "Case3", "Case4", "Case5"]:
        if case in fixed_versions and fixed_versions[case]:
            if versions.get(case) != fixed_versions[case]:
                versions[case] = fixed_versions[case]
                changed = True

    new_item["code_switched_versions"] = versions
    return changed, new_item


# -------------------------------
# Review & Fix (single item, with retry)
# -------------------------------
def review_and_fix_one(item: Dict, model_name: str, per_call_delay: float = 0.1,
                       max_retries: int = 3, backoff: float = 0.6) -> Tuple[bool, Dict, Optional[Dict]]:
    """
    반환: (was_fixed, reviewed_item, raw_result_json)
    """
    prompt = create_review_prompt(item)

    for attempt in range(1, max_retries + 1):
        try:
            model = get_thread_model(model_name)
            resp = model.generate_content(prompt)
            result = parse_model_json(resp)

            if result is None:
                raise ValueError("Model returned non-JSON or empty response.")

            # OK → no change
            if result.get("status") == "OK":
                if per_call_delay > 0:
                    time.sleep(per_call_delay)
                return False, item, {"status": "OK"}

            # NEEDS_FIX → apply
            if result.get("status") == "NEEDS_FIX":
                was_fixed, new_item = apply_fixes_to_item(item, result)
                if per_call_delay > 0:
                    time.sleep(per_call_delay)
                return was_fixed, new_item, result

            # Unexpected → no-op
            if per_call_delay > 0:
                time.sleep(per_call_delay)
            return False, item, result

        except Exception as e:
            if attempt == max_retries:
                print(f"❌ Error reviewing id={item.get('id','?')}: {e}")
                if per_call_delay > 0:
                    time.sleep(per_call_delay)
                return False, item, None

            # backoff
            time.sleep(backoff * attempt)

    return False, item, None


# -------------------------------
# IO Helpers
# -------------------------------
def load_items(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(obj, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


# -------------------------------
# Runner (multithreaded)
# -------------------------------
def review_dataset(input_path: str,
                   output_path: str,
                   model_name: str = "gemini-2.5-flash-lite",
                   workers: int = 20,
                   limit: Optional[int] = None,
                   per_call_delay: float = 0.1,
                   save_intermediate_every: int = 50,
                   intermediate_dir: Optional[str] = None) -> Dict:
    """
    입력 JSON: [{id, original_ko, original_en, code_switched_versions{Case2..Case5}} ...]
    출력 JSON: 수정 반영된 동일 구조 리스트
    """
    items = load_items(input_path)
    if limit:
        items = items[:limit]

    total = len(items)
    print(f"Loaded {total} items")

    results: List[Optional[Dict]] = [None] * total
    fix_count = 0
    ok_count = 0
    err_count = 0

    if intermediate_dir is None:
        intermediate_dir = os.path.dirname(output_path) or "."

    def _task(idx_item: Tuple[int, Dict]):
        idx, item = idx_item
        was_fixed, new_item, raw = review_and_fix_one(
            item, model_name, per_call_delay=per_call_delay
        )
        return idx, was_fixed, new_item, raw

    with ThreadPoolExecutor(max_workers=workers) as exe:
        futures = [exe.submit(_task, (i, it)) for i, it in enumerate(items)]

        for i, fut in enumerate(tqdm(as_completed(futures), total=total, desc="Reviewing")):
            try:
                idx, was_fixed, new_item, raw = fut.result()
                results[idx] = new_item
                if raw is None:
                    err_count += 1
                else:
                    if raw.get("status") == "OK":
                        ok_count += 1
                    elif raw.get("status") == "NEEDS_FIX" and was_fixed:
                        fix_count += 1
            except Exception as e:
                print(f"❌ Future error: {e}")
                err_count += 1
                # 안전망: 원본 유지
                # (idx를 모르면 채울 수 없으니 skip)

            # 중간 저장
            done = i + 1
            if save_intermediate_every and (done % save_intermediate_every == 0 or done == total):
                tmp_out = os.path.join(intermediate_dir, "review_intermediate.json")
                partial = [r if r is not None else items[j] for j, r in enumerate(results)]
                save_json(partial, tmp_out)

    # 최종 저장
    final = [r if r is not None else items[i] for i, r in enumerate(results)]
    save_json(final, output_path)

    return {
        "total": total,
        "ok": ok_count,
        "fixed": fix_count,
        "errors": err_count,
        "output_path": output_path,
    }


# -------------------------------
# CLI
# -------------------------------
def parse_args():
    p = argparse.ArgumentParser(
        description="Review and auto-fix code-switched Cases (2~5) using Gemini",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input", required=True, help="입력 JSON 경로")
    p.add_argument("--output", required=True, help="출력 JSON 경로")
    p.add_argument("--model", default="gemini-2.5-flash-lite",
                   choices=["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-1.5-flash"],
                   help="Gemini 모델")
    p.add_argument("--workers", type=int, default=20, help="동시 스레드 수")
    p.add_argument("--limit", type=int, default=None, help="처리할 항목 수 제한")
    p.add_argument("--delay", type=float, default=0.1, help="API 호출 후 대기(초)")
    p.add_argument("--save-every", type=int, default=50, help="중간 저장 주기")
    p.add_argument("--intermediate-dir", type=str, default=None, help="중간 저장 디렉토리")
    return p.parse_args()


def main():
    args = parse_args()

    # 사전 체크
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY is not set.")
        return
    if not os.path.exists(args.input):
        print(f"Error: input file not found: {args.input}")
        return

    print("Configuration")
    print(f"  input  = {args.input}")
    print(f"  output = {args.output}")
    print(f"  model  = {args.model}")
    print(f"  workers= {args.workers}")
    print(f"  limit  = {args.limit}")
    print(f"  delay  = {args.delay}s")
    print(f"  save-every = {args.save_every}")
    print()

    summary = review_dataset(
        input_path=args.input,
        output_path=args.output,
        model_name=args.model,
        workers=args.workers,
        limit=args.limit,
        per_call_delay=args.delay,
        save_intermediate_every=args.save_every,
        intermediate_dir=args.intermediate_dir,
    )

    print("\nSummary")
    print("-------")
    print(f"Total: {summary['total']}")
    print(f"OK: {summary['ok']}")
    print(f"Fixed: {summary['fixed']}")
    print(f"Errors: {summary['errors']}")
    print(f"Saved: {summary['output_path']}")


if __name__ == "__main__":
    main()
