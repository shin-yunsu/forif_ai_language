#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Case5와 Case6을 교체하는 스크립트
"""

import json
import argparse
import os


def swap_case4_case5(data):
    """Case4와 Case5를 교체"""
    for item in data:
        if "code_switched_versions" in item:
            versions = item["code_switched_versions"]

            # Case4와 Case5 교체
            case4 = versions.get("Case4")
            case5 = versions.get("Case5")

            versions["Case4"] = case5
            versions["Case5"] = case4

    return data


def main():
    parser = argparse.ArgumentParser(
        description="Case4와 Case5를 교체합니다"
    )

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="입력 JSON 파일 경로 (예: data/outputs/f.json)"
    )

    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="출력 JSON 파일 경로 (예: data/outputs/f_swapped.json)"
    )

    args = parser.parse_args()

    # 입력 파일 확인
    if not os.path.exists(args.input):
        print(f"❌ Error: 입력 파일을 찾을 수 없습니다: {args.input}")
        return

    # JSON 읽기
    print(f"📖 Reading: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"   Total items: {len(data)}")

    # Case4 ↔ Case5 교체
    print("🔄 Swapping Case4 ↔ Case5...")
    swapped_data = swap_case4_case5(data)

    # 결과 저장
    print(f"💾 Saving to: {args.output}")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(swapped_data, f, ensure_ascii=False, indent=2)

    print("✅ Done!")

    # 샘플 출력
    print("\n" + "="*60)
    print("Sample result (first item):")
    print("="*60)
    if swapped_data:
        sample = swapped_data[0]
        print(f"ID: {sample['id']}")
        print(f"Original Korean: {sample['original_ko']}")
        print(f"Original English: {sample['original_en']}")
        print("\nCode-switched versions:")
        for case_name in ["Case1", "Case2", "Case3", "Case4", "Case5", "Case6"]:
            value = sample['code_switched_versions'].get(case_name, "N/A")
            print(f"  {case_name}: {value}")


if __name__ == "__main__":
    main()
