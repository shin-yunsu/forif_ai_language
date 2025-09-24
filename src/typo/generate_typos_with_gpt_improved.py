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
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue

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
   예시: "인구는?" → "인구ㅡㄴ" (ㄴ 삭제)
   예시: "서울" → "서" (울 삭제)

3. 추가(Insertion): 불필요한 자모나 음절 삽입
   - 음절 중복: "스타벅스" → "스타벅스스" (스 중복)
   - 자모 추가: "나왔나요" → "나왔ㅅ나요" (ㅅ 추가)
   예시: "로고는" → "로고고는" (고 중복)
   예시: "어디" → "어디ㅣ" (ㅣ 추가)

4. 전치(Transposition): 인접한 자모나 음절 순서 바뀜
   - 음절 전치: "스타벅스" → "스벅타스" (타벅 순서 변경)
   - 자모 전치: "서울" → "서ㅜㅇㄹ" (ㅇ,ㅜ 순서 변경)
   예시: "로고는" → "고로는" (로고 순서 변경)
   예시: "나왔나요" → "나왔ㅏㄴ요" (ㄴ,ㅏ 순서 변경)

5. 띄어쓰기 오류(Spacing): 공백 추가/제거
   - 공백 제거: "어디에서 나왔나요" → "어디에서나왔나요"
   - 공백 추가: "스타벅스" → "스타 벅스"
   예시: "그들만의 리그" → "그들만의리그" (공백 제거)
   예시: "라이온킹" → "라이온 킹" (공백 추가)

각 오타 유형별로 2개 버전 생성:
- 1 error: 해당 오타 유형 1번 적용
- 2 errors: 해당 오타 유형 2번 적용 (1 error 버전에 추가하여)

입력 데이터:
{batch_text}

출력 형식:
[{{
  "original": "원본 한국어 텍스트",
  "substitution": {{
    "1_error": "교체 오타 하나",
    "2_errors": "교체 오타 둘"
  }},
  "deletion": {{
    "1_error": "삭제 오타 하나",
    "2_errors": "삭제 오타 둘"
  }},
  "insertion": {{
    "1_error": "추가 오타 하나",
    "2_errors": "추가 오타 둘"
  }},
  "transposition": {{
    "1_error": "전치 오타 하나",
    "2_errors": "전치 오타 둘"
  }},
  "spacing": {{
    "1_error": "띄어쓰기 오타 하나",
    "2_errors": "띄어쓰기 오타 둘"
  }}
}}]

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

def process_dataset(input_file: str, output_file: str, batch_size: int = 5, max_workers: int = 5):
    """데이터셋 처리 및 오타 생성 (멀티스레딩 지원)"""

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

    # 배치 처리를 위한 준비
    all_results = []
    results_lock = threading.Lock()  # Thread-safe 결과 저장을 위한 lock
    error_types = ['substitution', 'deletion', 'insertion', 'transposition', 'spacing']

    print(f"🔄 Processing in batches of {batch_size} with {max_workers} workers...")

    # 배치 작업을 위한 함수
    def process_batch_worker(batch_data, batch_index):
        """개별 배치를 처리하는 워커 함수"""
        try:
            # GPT로 오타 생성
            batch_results = generate_typos_batch(client, batch_data, batch_size)

            # 결과를 그대로 유지 (플랫 변환 없음)
            batch_flat_results = batch_results

            return batch_index, batch_flat_results
        except Exception as e:
            print(f"❌ Error processing batch {batch_index}: {e}")
            return batch_index, []

    # ThreadPoolExecutor를 사용한 병렬 처리
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}

        # 배치 작업 제출
        for i in range(0, len(simple_data), batch_size):
            batch = simple_data[i:i+batch_size]
            batch_index = i // batch_size
            future = executor.submit(process_batch_worker, batch, batch_index)
            futures[future] = batch_index

        # 결과 수집 (순서 보장을 위한 딕셔너리 사용)
        results_dict = {}

        # Progress bar와 함께 결과 수집
        with tqdm(total=len(futures), desc="Processing batches") as pbar:
            for future in as_completed(futures):
                batch_index, batch_results = future.result()
                results_dict[batch_index] = batch_results
                pbar.update(1)

        # 순서대로 결과 병합
        for i in sorted(results_dict.keys()):
            all_results.extend(results_dict[i])

    print(f"\n✅ Generated {len(all_results)} entries")

    # 결과 저장
    print(f"💾 Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # 통계 출력
    print("\n📊 Statistics:")
    print(f"  Original entries: {len(simple_data)}")
    print(f"  Generated entries: {len(all_results)}")

    # 샘플 출력
    if all_results:
        print("\n📝 Sample output:")
        sample = all_results[0]
        print(f"Original: {sample.get('original', '')}")
        for error_type in error_types:
            if error_type in sample:
                print(f"\n{error_type.upper()}:")
                if '1_error' in sample[error_type]:
                    print(f"  1 error: {sample[error_type]['1_error']}")
                if '2_errors' in sample[error_type]:
                    print(f"  2 errors: {sample[error_type]['2_errors']}")

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
    parser.add_argument("--input", default="mkqa_refined_simple.json", help="Input JSON file")
    parser.add_argument("--output", default="mkqa_with_typos_gpt.json", help="Output JSON file")
    parser.add_argument("--batch-size", type=int, default=3, help="Batch size for API calls")
    parser.add_argument("--max-workers", type=int, default=5, help="Maximum number of parallel workers")
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
            batch_size=2,
            max_workers=2
        )
        print(f"\n✅ Test complete! Generated {count} entries")
        print("Check 'mkqa_typo_sample_output.json' for results")
    else:
        # 전체 처리
        count = process_dataset(
            args.input,
            args.output,
            batch_size=args.batch_size,
            max_workers=args.max_workers
        )
        print(f"\n✅ Complete! Generated {count} entries")
        print(f"Output saved to: {args.output}")