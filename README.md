# Korean-English Code-Switching & Typo Dataset Generator

MKQA 데이터셋을 활용한 한국어-영어 코드 스위칭 및 오타 데이터 생성 도구

## 📁 프로젝트 구조

```
forif_ai/
├── code-switching/          # 코드 스위칭 생성
│   └── make_code_switching_gpt.py
├── refine/                  # 한국어 번역 개선
│   └── refine_korean_with_gpt.py
├── typo/                    # 오타 생성
│   ├── generate_typos_with_gpt.py
│   ├── generate_typos_with_gpt_improved.py
│   ├── generate_typos_from_korean.py
│   └── korean_typo_generator.py
├── format/                  # 데이터 형식 변환
│   ├── filter_mkqa_*.py
│   ├── convert_*.py
│   └── analyze_*.py
├── data/                   # 데이터 파일
│   ├── mkqa_refined_full.json    # 정제된 전체 데이터
│   ├── mkqa_filtered.json        # 필터링된 데이터
│   └── mkqa_kr_only.json         # 한국어만 추출
└── ml-mkqa/                 # MKQA 평가 도구
```

## 🚀 설치 및 설정

### 1. 환경 설정
```bash
# 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows

# 패키지 설치
pip install openai tqdm jamo
```

### 2. API 키 설정
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

## 🔧 주요 기능

### 1. 코드 스위칭 데이터 생성

한국어-영어 혼합 문장을 5가지 케이스로 생성합니다.

#### 코드 스위칭 케이스
| Case | 설명 | 예시 |
|------|------|------|
| Case1 | 완전 한국어 | 대한민국의 대통령은 누구인가? |
| Case2 | 키워드 레벨 switch | 대한민국의 president는 누구인가? |
| Case3 | 구조 혼합 | Who is 대한민국 대통령? |
| Case4 | 키워드 레벨 switch(영어) | Who is the 대통령 of Korea? |
| Case5 | 완전 영어 | Who is the President of South Korea? |

#### 실행 방법
```bash
# 기본 실행 (100개 샘플, 5개 스레드)
python code-switching/make_code_switching_gpt.py

# 전체 데이터 처리
python code-switching/make_code_switching_gpt.py \
    --input data/refined/mkqa_refined_full.json \
    --output code_switched_full.json \
    --sample-size -1 \
    --threads 8

# 커스텀 설정
python code-switching/make_code_switching_gpt.py \
    --input data/refined/mkqa_refined_full.json \
    --output custom_output.json \
    --sample-size 500 \
    --model gpt-4o-mini \
    --threads 10 \
    --delay 0.2 \
    --save-interval 20
```

#### 옵션 설명
- `--input`: 입력 JSON 파일 경로 (기본값: ../jsons/mkqa_refined_full.json)
- `--output`: 출력 JSON 파일 경로 (기본값: code_switched_data.json)
- `--sample-size`: 처리할 샘플 수, -1이면 전체 (기본값: 100)
- `--model`: OpenAI 모델 선택 [gpt-4o-mini, gpt-4, gpt-3.5-turbo] (기본값: gpt-4o-mini)
- `--threads`: 병렬 처리 스레드 수 (기본값: 5)
- `--delay`: API 호출 간 지연 시간(초) (기본값: 0.1)
- `--save-interval`: 중간 저장 간격 (기본값: 10)

### 2. 한국어 번역 개선

MKQA 데이터셋의 한국어 번역을 자연스럽게 개선합니다.

```bash
# 기본 실행
python src/refine/refine_korean_with_gpt.py \
    --input data/mkqa_filtered.json \
    --output data/mkqa_refined_full.json

# 테스트 모드 (20개 샘플)
python src/refine/refine_korean_with_gpt.py \
    --test \
    --input data/mkqa_filtered.json \
    --sample-size 20

# 병렬 처리 최적화
python src/refine/refine_korean_with_gpt.py \
    --input jsons/mkqa_filtered.json \
    --output jsons/mkqa_refined_v2.json \
    --batch-size 20 \
    --max-workers 10
```

#### 옵션 설명
- `--input`: 입력 JSON 파일
- `--output`: 출력 JSON 파일
- `--batch-size`: 배치 크기 (기본값: 10)
- `--max-workers`: 병렬 워커 수 (기본값: 5)
- `--test`: 테스트 모드 활성화
- `--sample-size`: 테스트 샘플 크기 (기본값: 20)

### 3. 오타 데이터 생성

한국어 문장에 자연스러운 오타를 생성합니다.

#### 3.1 GPT 기반 오타 생성
```bash
# 기본 실행
python src/typo/generate_typos_with_gpt.py \
    --input data/processed/mkqa_kr_only.json \
    --output korean_with_typos.json

# 개선된 버전 (더 자연스러운 오타)
python src/typo/generate_typos_with_gpt_improved.py \
    --input data/processed/mkqa_kr_only.json \
    --output korean_typos_improved.json \
    --batch-size 15

# 오타 비율 조절
python src/typo/generate_typos_with_gpt.py \
    --input data/processed/mkqa_kr_only.json \
    --output korean_typos_30.json \
    --typo-ratio 0.3
```

#### 3.2 규칙 기반 오타 생성
```bash
# 한국어 오타 생성 (5가지 유형)
python src/typo/korean_typo_generator.py \
    --input data/mkqa_kr_only.json \
    --output korean_typos_rule.json

# 한국어 데이터에서 오타 생성
python src/typo/generate_typos_from_korean.py
```

#### 오타 유형
1. **교체(Substitution)**: 자모/발음 유사 문자 교체
2. **삭제(Deletion)**: 자모/음절 누락
3. **추가(Insertion)**: 불필요한 자모/음절 삽입
4. **전치(Transposition)**: 인접 문자 순서 변경
5. **띄어쓰기(Spacing)**: 공백 추가/제거

### 4. 데이터 필터링 및 변환

#### MKQA 데이터 필터링
```bash
# 긴 답변만 필터링
python format/filter_mkqa_long_only.py

# 의미있는 답변만 필터링
python format/filter_mkqa_meaningful.py

# 설명형 답변만 필터링
python format/filter_mkqa_descriptive.py

# 최종 필터링
python format/filter_mkqa_final.py
```

#### 형식 변환
```bash
# MKQA를 JSON으로 변환
python format/convert_mkqa_to_json.py

# 정제된 형식으로 변환
python format/convert_refined_format.py
```

#### 데이터 분석
```bash
# 답변 유형 분석
python format/analyze_answer_types.py

# MKQA 데이터 분석
python format/analyze_mkqa.py
```

## 📊 데이터 형식

### 입력 형식 (MKQA)
```json
[
  {
    "en": "where did the logo for starbucks come from",
    "ko": "스타벅스 로고는 어디에서 유래했나요?"
  }
]
```

### 코드 스위칭 출력 형식
```json
[
  {
    "id": 0,
    "original_ko": "스타벅스 로고는 어디에서 유래했나요?",
    "original_en": "where did the logo for starbucks come from",
    "code_switched_versions": {
      "Case1": "스타벅스 로고는 어디에서 유래했나요?",
      "Case2": "스타벅스 logo는 어디에서 came from했나요?",
      "Case3": "Where did 스타벅스 로고 come from?",
      "Case4": "Where did the 로고 for Starbucks come from?",
      "Case5": "where did the logo for starbucks come from"
    }
  }
]
```

### 오타 출력 형식
```json
{
  "original": "원본 한국어 텍스트",
  "substitution": {
    "1_error": "교체 오타 1개",
    "2_errors": "교체 오타 2개"
  },
  "deletion": { ... },
  "insertion": { ... },
  "transposition": { ... },
  "spacing": { ... }
}
```

## ⚙️ 성능 최적화

### 멀티스레딩
- 코드 스위칭: 5-10개 스레드 권장
- 한국어 개선: 5-10개 워커 권장
- Rate limit 주의: 너무 많은 스레드 사용 시 OpenAI API 제한에 걸릴 수 있음

### 처리 시간 예상
- 100개 항목: 약 1-2분 (5개 스레드)
- 1,000개 항목: 약 10-20분 (8개 스레드)
- 10,000개 항목: 약 2-3시간 (10개 스레드)

## 🔍 문제 해결

### API 키 오류
```bash
export OPENAI_API_KEY="sk-..."  # 올바른 API 키 설정
```

### Rate Limit 오류
- `--delay` 값 증가 (예: 0.5)
- `--threads` 수 감소 (예: 3)

### 메모리 부족
- `--sample-size` 조절하여 배치 처리
- `--save-interval` 감소하여 자주 저장

### 한글 인코딩 문제
```python
# 파일 상단에 추가
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```

## 📝 워크플로우

1. **데이터 준비**
   ```bash
   # MKQA 데이터 필터링
   python format/filter_mkqa_final.py
   ```

2. **한국어 정제**
   ```bash
   # GPT로 한국어 번역 개선
   python refine/refine_korean_with_gpt.py --input mkqa_filtered.json
   ```

3. **코드 스위칭 생성**
   ```bash
   # 5가지 케이스로 코드 스위칭
   python code-switching/make_code_switching_gpt.py --input mkqa_refined.json
   ```

4. **오타 생성**
   ```bash
   # 한국어 오타 추가
   python typo/generate_typos_with_gpt_improved.py --input mkqa_kr_only.json
   ```

## 📄 라이선스

이 프로젝트는 연구 목적으로 제작되었습니다.
MKQA 데이터셋의 라이선스를 따릅니다.

## 🙏 참고

- [MKQA Dataset](https://github.com/apple/ml-mkqa)
- [OpenAI API Documentation](https://platform.openai.com/docs)