#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
import threading
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv

# ================= 설정 =================
MODELS = {
    "qwen_72b": "qwen/qwen-2.5-72b-instruct",
    "qwen_7b":  "qwen/qwen-2.5-7b-instruct",
}
TYPO_TYPES   = ["substitution", "deletion", "insertion", "transposition", "spacing"]
ERROR_LEVELS = ["1_error", "2_errors"]
# =======================================

_thread_local = threading.local()

def get_thread_client() -> OpenAI:
    """스레드별 OpenAI(OpenRouter) 클라이언트 생성/캐시."""
    client = getattr(_thread_local, "client", None)
    if client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set in environment.")
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        _thread_local.client = client
    return client

def chat_once(model_name: str, text: str, timeout: float = 60.0) -> str:
    """단일 API 호출 (예외 안전)."""
    try:
        client = get_thread_client()
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": text}],
            timeout=timeout,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        print(f"[warn] chat_once error model={model_name}: {e}")
        return ""

def chat_with_retry(model_name: str, text: str, max_retries: int = 5) -> str:
    """지수 백오프 + 지터 재시도."""
    delay = 1.0
    for _ in range(max_retries):
        out = chat_once(model_name, text)
        if out:
            return out
        time.sleep(delay * (1.0 + 0.25 * (os.getpid() % 3)))
        delay = min(delay * 2.0, 16.0)
    return ""

def enumerate_text_paths(item: Dict) -> List[Tuple[Tuple[str, ...], str]]:
    """
    하나의 item에서 (path, text) 목록 생성.
    path 예:
      ('responses',)                          -> original
      ('substitution','1_error','responses')  -> typo
    """
    outs = []
    if "original" in item and isinstance(item["original"], str):
        outs.append((("responses",), item["original"]))
    for t in TYPO_TYPES:
        sec = item.get(t)
        if not isinstance(sec, dict):
            continue
        for lvl in ERROR_LEVELS:
            entry = sec.get(lvl)
            if isinstance(entry, dict) and isinstance(entry.get("text"), str):
                outs.append(((t, lvl, "responses"), entry["text"]))
    return outs

def build_results_skeleton(data: List[Dict]) -> List[Dict]:
    """입력 데이터를 보존하면서 responses 슬롯을 비운 결과 스켈레톤 생성."""
    results: List[Dict] = []
    for item in data:
        r = {
            "original": item.get("original", ""),
            "id": item.get("id"),
            "responses": {},  # per-model
        }
        for t in TYPO_TYPES:
            if t in item and isinstance(item[t], dict):
                r[t] = {}
                for lvl in ERROR_LEVELS:
                    if lvl in item[t] and isinstance(item[t][lvl], dict):
                        entry = item[t][lvl]
                        r[t][lvl] = {
                            "text": entry.get("text", ""),
                            "errors": entry.get("errors", []),
                            "responses": {},  # per-model
                        }
        results.append(r)
    return results

def merge_checkpoint_into_results(results: List[Dict], ckpt: List[Dict]) -> None:
    """
    체크포인트 내용을 결과 스켈레톤에 병합(제자리 변경).
    - 길이/ID가 동일하면 인덱스 기준 빠르게 합침
    - 그렇지 않으면 id 매핑으로 안전 병합
    """
    if not isinstance(ckpt, list):
        return

    same_len = len(results) == len(ckpt)
    use_index_merge = same_len and all(
        (results[i].get("id") == ckpt[i].get("id")) for i in range(len(results))
    )

    def copy_responses(dst_node: Dict, src_node: Dict):
        if "responses" in src_node and isinstance(src_node["responses"], dict):
            dst_node.setdefault("responses", {})
            for k, v in src_node["responses"].items():
                if v:  # 빈 문자열이면 넘어감(미완료)
                    dst_node["responses"][k] = v

    if use_index_merge:
        for i in range(len(results)):
            dst, src = results[i], ckpt[i]
            copy_responses(dst, src)
            for t in TYPO_TYPES:
                if t in dst and t in src:
                    for lvl in ERROR_LEVELS:
                        if lvl in dst[t] and lvl in src[t]:
                            copy_responses(dst[t][lvl], src[t][lvl])
    else:
        # id 기반 병합
        idx_by_id = {str(r.get("id")): i for i in range(len(results))}
        for src_item in ckpt:
            key = str(src_item.get("id"))
            if key in idx_by_id:
                i = idx_by_id[key]
                dst = results[i]
                copy_responses(dst, src_item)
                for t in TYPO_TYPES:
                    if t in dst and t in src_item:
                        for lvl in ERROR_LEVELS:
                            if lvl in dst[t] and lvl in src_item[t]:
                                copy_responses(dst[t][lvl], src_item[t][lvl])

def response_exists(results: List[Dict], item_idx: int, path: Tuple[str, ...], model_key: str) -> bool:
    """해당 path/model 응답이 이미 존재하는지 확인(Resume에서 스킵 용)."""
    target = results[item_idx]
    for key in path[:-1]:
        if key not in target:
            return False
        target = target[key]
    final_key = path[-1]  # 'responses'
    if final_key not in target or not isinstance(target[final_key], dict):
        return False
    val = target[final_key].get(model_key, "")
    return bool(val)

def count_total_calls(data: List[Dict], models: Dict[str, str]) -> int:
    total = 0
    for item in data:
        total += len(enumerate_text_paths(item)) * len(models)
    return total

def process_typo_data(
    input_file: str,
    output_file: str,
    batch_size: Optional[int] = 0,
    workers: int = 20,
    checkpoint_every: int = 0,
    dry_run: bool = False,
):
    # 로드
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Input JSON must be an array of items.")

    if batch_size and batch_size > 0:
        data = data[:batch_size]

    print(f"Items to process: {len(data)} (workers={workers})")

    # 스켈레톤 생성
    results = build_results_skeleton(data)

    # Resume: 기존 체크포인트/완료본 병합
    ckpt_path = output_file + ".ckpt.json"
    resume_loaded = False
    for candidate in [ckpt_path, output_file]:
        if os.path.exists(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as cf:
                    ckpt_results = json.load(cf)
                merge_checkpoint_into_results(results, ckpt_results)
                resume_loaded = True
                print(f"[resume] merged existing results from: {candidate}")
                break
            except Exception as e:
                print(f"[warn] failed to load resume file {candidate}: {e}")

    total_planned = count_total_calls(data, MODELS)
    # 이미 채워진 응답 수 집계
    already_done = 0
    for idx, item in enumerate(data):
        for path, _ in enumerate_text_paths(item):
            for model_key in MODELS:
                if response_exists(results, idx, path, model_key):
                    already_done += 1

    to_do = total_planned - already_done
    print(f"Total API calls (planned): {total_planned}")
    print(f"Already completed (from resume): {already_done}")
    print(f"Remaining to execute: {to_do}")

    if dry_run:
        print("[dry-run] No API calls will be made.")
        return

    # 작업 스케줄링 (이미 완료된 응답은 스킵)
    futures = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for idx, item in enumerate(data):
            for path, text in enumerate_text_paths(item):
                for model_key, model_name in MODELS.items():
                    if response_exists(results, idx, path, model_key):
                        continue
                    fut = executor.submit(chat_with_retry, model_name, text)
                    futures[fut] = (idx, path, model_key)

        scheduled = len(futures)
        print(f"Total API calls scheduled now: {scheduled}")

        completed = 0
        for future in as_completed(futures):
            item_idx, path, model_key = futures[future]
            resp = ""
            try:
                resp = future.result()
            except Exception as e:
                print(f"[warn] future error idx={item_idx}, path={path}, model={model_key}: {e}")
                resp = ""

            # 메인 스레드에서만 결과 쓰기 → 레이스 없음
            target = results[item_idx]
            for key in path[:-1]:
                target = target[key]
            final_key = path[-1]
            target[final_key][model_key] = resp

            completed += 1
            done_total = already_done + completed
            if completed % 10 == 0 or completed == scheduled:
                print(f"Completed {done_total}/{total_planned} total calls")

            if checkpoint_every and (completed % checkpoint_every == 0):
                tmp = ckpt_path
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"[checkpoint] saved: {tmp} (after {done_total} total calls)")

    # 종료 직전 체크포인트 + 최종본 저장
    with open(ckpt_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nDone! Saved to {output_file} (and checkpoint to {ckpt_path})")

if __name__ == "__main__":
    import argparse
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", default="data/outputs/typos/typos_data.json")
    parser.add_argument("--output_file", default="data/outputs/typos/typos_data_with_responses.json")
    parser.add_argument("--batch_size", type=int, default=0, help="0 or <=0 means ALL items")
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--checkpoint_every", type=int, default=0, help="save checkpoint every N *new* calls (0=off)")
    parser.add_argument("--dry_run", action="store_true")
    args = parser.parse_args()

    process_typo_data(
        input_file=args.input_file,
        output_file=args.output_file,
        batch_size=args.batch_size,
        workers=args.workers,
        checkpoint_every=args.checkpoint_every,
        dry_run=args.dry_run,
    )
