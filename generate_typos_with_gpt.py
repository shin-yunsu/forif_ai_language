#!/usr/bin/env python3
"""
GPT-4o-mini를 사용해서 한국어 문장에 오타를 생성하는 스크립트 (개선 버전)
"""
import json
import os
from openai import OpenAI
from typing import List, Dict
import time
from tqdm import tqdm

def initialize_client():
    """Initialize OpenAI client with API key from environment variable"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  Please set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        exit(1)

    client = OpenAI(api_key=api_key)
    return client

def generate_typos_batch(client, entries: List[Dict], batch_size: int = 5) -> List[Dict]:
    """한국어 문장에 오타를 생성해주세요.

오타 생성 규칙:
1. 교체(Substitution): ㅐ↔ㅔ, ㄹ↔ㄴ 등 자모나 발음이 비슷한 것끼리 교체
2. 삭제(Deletion): 자모 또는 음절 단위 누락
3. 추가(Insertion): 불필요한 자모나 음절 삽입
4. 전치(Transposition): 자모나 음절 순서 바뀜
5. 띄어쓰기 오류(Spacing): 불필요한 공백 추가 또는 공백 누락

각 문장에 대해 3개 버전을 생성:
- Case 1: 오타 없음 (원본 그대로)
- Case 2: 오타 1개 (규칙 중 1개 적용)
- Case 3: 오타 2개 (규칙 중 2개 적용)

주의사항:
- 오타는 자연스럽게 발생할 수 있는 실수여야 함
- 문장의 의미는 유추 가능해야 함
- 영어 부분은 그대로 유지

입력 데이터:
{batch_text}

출력 형식 (JSON 배열):
[
  {{
    "en": "영어 질문",
    "ko_original": "원본 한국어",
    "variants": [
      {{"text": "원본 그대로", "num_errors": 0, "error_types": []}},
      {{"text": "오타 1개 버전", "num_errors": 1, "error_types": ["사용된 오타 유형"]}},
      {{"text": "오타 2개 버전", "num_errors": 2, "error_types": ["유형1", "유형2"]}}
    ]
  }},
  …
]

JSON 배열 형식으로만 응답해주세요."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 한국어 오타를 생성하는 전문가입니다. 각 오타 유형별로 명확하고 구분 가능한 오타를 만들어주세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )

        # 응답 파싱
        result_text = response.choices[0].message.content.strip()

        # JSON 추출
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        result = json.loads(result_text)
        return result

    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Response: {result_text[:200]}...")
        return []
    except Exception as e:
        print(f"❌ API error: {e}")
        return []

def process_dataset(input_file: str, output_file: str, batch_size: int = 5):
    """데이터셋 처리 및 오타 생성"""

    print(f"📚 Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 데이터 형식 확인 및 변환
    simple_data = []
    for entry in data:
        if "query" in entry:
            simple_data.append({
                "en": entry["query"],
                "ko": entry["queries"]["ko"]
            })
        else:
            simple_data.append(entry)

    print(f"📊 Total entries to process: {len(simple_data)}")

    # OpenAI 클라이언트 초기화
    client = initialize_client()

    # 배치 처리
    all_results = []
    error_types = ['substitution', 'deletion', 'insertion', 'transposition', 'spacing']

    print(f"🔄 Processing in batches of {batch_size}...")

    for i in tqdm(range(0, len(simple_data), batch_size), desc="Processing batches"):
        batch = simple_data[i:i+batch_size]

        # GPT로 오타 생성
        batch_results = generate_typos_batch(client, batch, batch_size)

        # 결과를 플랫 형식으로 변환
        for entry_group in batch_results:
            en_query = entry_group.get("en", "")
            ko_original = entry_group.get("ko_original", "")
            error_type = entry_group.get("error_type", "")

            for variant in entry_group.get("variants", []):
                flat_entry = {
                    "en": en_query,
                    "ko_original": ko_original,
                    "ko_typo": variant["text"],
                    "error_type": error_type,
                    "num_errors": variant["num_errors"],
                    "applied_errors": [error_type] * variant["num_errors"] if variant["num_errors"] > 0 else []
                }
                all_results.append(flat_entry)

        # Rate limiting
        if i + batch_size < len(simple_data):
            time.sleep(1)

    print(f"\n✅ Generated {len(all_results)} entries")

    # 결과 저장
    print(f"💾 Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # 통계 출력
    print("\n📊 Statistics:")
    print(f"  Original entries: {len(simple_data)}")
    print(f"  Generated entries: {len(all_results)}")

    # 각 오타 유형별 샘플 출력
    print("\n📝 Sample outputs by error type:")
    for error_type in error_types:
        type_entries = [e for e in all_results if e['error_type'] == error_type]
        if len(type_entries) >= 3:
            print(f"\n--- {error_type.upper()} ---")
            print(f"Original: {type_entries[0]['ko_original']}")
            print(f"0 errors: {type_entries[0]['ko_typo']}")
            print(f"1 error:  {type_entries[1]['ko_typo']}")
            print(f"2 errors: {type_entries[2]['ko_typo']}")

    return len(all_results)

def create_test_sample(input_file: str, sample_file: str, sample_size: int = 5):
    """테스트용 샘플 파일 생성"""
    print(f"📝 Creating sample file with {sample_size} entries...")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sample_data = data[:sample_size]

    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Sample file created: {sample_file}")
    return sample_file

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate typos using GPT-4o-mini")
    parser.add_argument("--input", default="mkqa_formatted.json", help="Input JSON file")
    parser.add_argument("--output", default="mkqa_with_typos_gpt.json", help="Output JSON file")
    parser.add_argument("--batch-size", type=int, default=3, help="Batch size for API calls")
    parser.add_argument("--test", action="store_true", help="Test with small sample first")
    parser.add_argument("--sample-size", type=int, default=5, help="Sample size for testing")

    args = parser.parse_args()

    if args.test:
        # 테스트 모드
        sample_file = "mkqa_typo_sample.json"
        create_test_sample(args.input, sample_file, args.sample_size)

        print("\n🧪 Testing with sample file...")
        count = process_dataset(
            sample_file,
            "mkqa_typo_sample_output.json",
            batch_size=2
        )
        print(f"\n✅ Test complete! Generated {count} entries")
        print("Check 'mkqa_typo_sample_output.json' for results")
    else:
        # 전체 처리
        count = process_dataset(
            args.input,
            args.output,
            batch_size=args.batch_size
        )
        print(f"\n✅ Complete! Generated {count} entries")
        print(f"Output saved to: {args.output}")