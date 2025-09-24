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
    """GPT를 사용해서 오타 생성"""

    # 배치 데이터 준비
    batch_text = json.dumps(entries, ensure_ascii=False, indent=2)

    prompt = f"""한국어 문장에 오타를 생성해주세요.

오타 생성 규칙과 예시:

1. 교체(Substitution): 자모나 발음이 비슷한 것끼리 교체
   - 모음 교체: ㅐ↔ㅔ, ㅓ↔ㅏ, ㅗ↔ㅜ, ㅡ↔ㅓ, ㅣ↔ㅡ
   - 자음 교체: ㄹ↔ㄴ, ㅂ↔ㅁ, ㄱ↔ㅋ, ㄷ↔ㅌ, ㅈ↔ㅊ, ㅅ↔ㅆ
   예시: "어디에서" → "어디애서" (ㅔ→ㅐ)
   예시: "나왔나요" → "나왔라요" (ㄴ→ㄹ)

2. 삭제(Deletion): 자모 또는 음절 단위 누락
   - 음절 삭제: "어디에서" → "어디서" (에 삭제)
   - 자모 삭제: "했습니다" → "했습니다" (종성 ㅆ 삭제 → "했스니다")
   예시: "스타벅스" → "스타벅" (스 삭제)
   예시: "그들만의" → "그들의" (만 삭제)

3. 추가(Insertion): 불필요한 자모나 음절 삽입
   - 음절 중복: "스타벅스" → "스타벅벅스" (벅 중복)
   - 자모 추가: "나왔나요" → "나왔었나요" (었 추가)
   예시: "로고는" → "로고고는" (고 중복)
   예시: "어디" → "어디이" (이 추가)

4. 전치(Transposition): 인접한 자모나 음절 순서 바뀜
   - 음절 전치: "스타벅스" → "타스벅스" (스타 순서 변경)
   - 자모 전치: "어디" → "어디" (초성 교환은 어려우므로 음절 단위 권장)
   예시: "로고는" → "고로는" (로고 순서 변경)
   예시: "나왔나요" → "나왔요나" (나요 순서 변경)

5. 띄어쓰기 오류(Spacing): 공백 추가/제거
   - 공백 제거: "어디에서 나왔나요" → "어디에서나왔나요"
   - 공백 추가: "스타벅스" → "스타 벅스"
   예시: "그들만의 리그" → "그들만의리그" (공백 제거)
   예시: "라이온킹" → "라이온 킹" (공백 추가)

각 오타 유형별로 3개 버전 생성:
- 0 errors: 오타 없음 (원본 그대로)
- 1 error: 해당 오타 유형 1번 적용
- 2 errors: 1 error 버전에 추가로 1개 더 적용 (누적)

중요 지침:
- 오타는 명확하게 구분 가능해야 함 (미묘한 변화 X)
- 2개 오타는 1개 오타 버전을 기반으로 추가 (누적 방식)
- 각 단계마다 차이가 확실히 보여야 함
- 예시: "스타벅스 로고는 어디에서 나왔나요"
  - 0 errors: "스타벅스 로고는 어디에서 나왔나요" (원본)
  - 1 error: "스타벅스 로고는 어디애서 나왔나요" (ㅔ→ㅐ)
  - 2 errors: "스터벅스 로고는 어디애서 나왔나요" (1 error 버전에서 ㅏ→ㅓ 추가)

누적 방식 설명:
- 1 error 버전을 먼저 만들고
- 2 errors 버전은 1 error 버전에서 다른 위치에 오타를 하나 더 추가
- 이렇게 하면 오타가 점진적으로 증가하는 것을 볼 수 있음

입력 데이터:
{batch_text}

출력 형식 (각 오타 유형별로 생성):
**반드시 누적 방식으로 생성**
[
  {{
    "en": "영어 질문",
    "ko_original": "원본 한국어",
    "error_type": "substitution",
    "variants": [
      {{"text": "원본 그대로", "num_errors": 0}},
      {{"text": "원본에 교체 오타 1개 적용", "num_errors": 1}},
      {{"text": "위의 1 error 버전에 교체 오타 1개 더 추가", "num_errors": 2}}
    ]
  }},
  {{
    "en": "영어 질문",
    "ko_original": "원본 한국어",
    "error_type": "deletion",
    "variants": [
      {{"text": "원본 그대로", "num_errors": 0}},
      {{"text": "원본에 삭제 오타 1개 적용", "num_errors": 1}},
      {{"text": "위의 1 error 버전에 삭제 오타 1개 더 추가", "num_errors": 2}}
    ]
  }},
  {{
    "en": "영어 질문",
    "ko_original": "원본 한국어",
    "error_type": "insertion",
    "variants": [
      {{"text": "원본 그대로", "num_errors": 0}},
      {{"text": "원본에 추가 오타 1개 적용", "num_errors": 1}},
      {{"text": "위의 1 error 버전에 추가 오타 1개 더 추가", "num_errors": 2}}
    ]
  }},
  {{
    "en": "영어 질문",
    "ko_original": "원본 한국어",
    "error_type": "transposition",
    "variants": [
      {{"text": "원본 그대로", "num_errors": 0}},
      {{"text": "원본에 전치 오타 1개 적용", "num_errors": 1}},
      {{"text": "위의 1 error 버전에 전치 오타 1개 더 추가", "num_errors": 2}}
    ]
  }},
  {{
    "en": "영어 질문",
    "ko_original": "원본 한국어",
    "error_type": "spacing",
    "variants": [
      {{"text": "원본 그대로", "num_errors": 0}},
      {{"text": "원본에 띄어쓰기 오타 1개 적용", "num_errors": 1}},
      {{"text": "위의 1 error 버전에 띄어쓰기 오타 1개 더 추가", "num_errors": 2}}
    ]
  }}
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