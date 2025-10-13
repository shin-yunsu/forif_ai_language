# Code-Switching 개선 요약

## 📊 최종 성능
- **성공률**: 71.4% (10/14)
- **이전 대비**: 0~2% → **71.4%** (35배 개선!)

## ✅ 주요 개선 사항

### 1. 프롬프트 완전 재설계
**Before**: 복잡한 규칙, 모호한 지침
**After**: 3단계 명확한 프로세스
- STEP 1: 핵심용어 추출
- STEP 2: Case2-3 (한→영)
- STEP 3: Case4-5 (영→한)

### 2. 의문사 규칙 초강력 강조
```
🚫 절대 금지 목록:
- 한국어: 어디, 어디에서, 언제, 왜, 무엇, 누가, 어떤, 어떻게
- 영어: where, when, why, what, who, which, how

❌ "어디에서" → "where에서" (금지!)
❌ "무엇" → "what" (금지!)
```

### 3. 검증 함수 추가
```python
✅ 의문사 혼입 체크
✅ 차별성 체크 (Case2 ≠ Case3)
✅ 언어 혼합 체크
```

### 4. 문장 길이별 적응형 교체
**짧은 문장 (5~10 단어)**:
- Case2: 2~3개
- Case3: 4~6개
- Case4: 3~4개
- Case5: 5~7개

**긴 문장 (21단어 이상)**:
- Case2: 3~5개
- Case3: 6~9개
- Case4: 4~6개
- Case5: 7~10개

## 📝 개선된 예시

### 과학 용어
```json
{
  "Case2": "두 nucleotides 사이에 covalent bonds는 어디에서 형성되나요",
  "Case3": "두 nucleotides 사이에 covalent bonds는 어디에서 form되나요",
  "Case4": "where do 공유 결합 form between two 뉴클레오타이드",
  "Case5": "where do 공유 결합 형성 between two 뉴클레오타이드"
}
```

### 의문사 보존
```json
{
  "Case2": "제1차 World War는 어디에서 일어났나요?",
  "Case3": "First World War는 어디에서 take place했나요?",
  "Case4": "where did the 제1차 세계 대전 take place?",
  "Case5": "where did the 제1차 세계 대전 일어났나요?"
}
```

## 🎯 핵심 원칙

1. **의문사는 절대 교체하지 않는다**
2. **긴 문장일수록 더 많은 핵심용어 교체**
3. **Case2 < Case3, Case4 < Case5 (단조 증가)**
4. **고유명사만 아니라 일반 명사/동사/형용사도 교체**

## 📂 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/code-switching/gemini.py` | ✅ 프롬프트 재설계<br>✅ 검증 함수<br>✅ 길이 적응형 |
| `src/code-switching/gpt.py` | ✅ 동일한 개선 |
| `src/code-switching/gemini_improved.py` | ✅ 개선판 (테스트용) |

## 🚀 사용 방법

```bash
# Gemini (Case2-5)
python src/code-switching/gemini.py \
  --input data/inputs/test.json \
  --output data/outputs/result.json \
  --model gemini-2.5-flash-lite

# GPT (Case2-4)
python src/code-switching/gpt.py \
  --input data/inputs/test.json \
  --output data/outputs/result.json \
  --model gpt-4o-mini
```

## 📈 성능 지표

| 지표 | 이전 | 개선 후 |
|------|------|---------|
| 성공률 | 0~2% | **71.4%** |
| 의문사 오류 | 매우 많음 | 거의 없음 (7%) |
| 자연스러움 | 낮음 | 높음 |
| 점진적 변화 | 없음 | 명확함 |

## 💡 향후 개선 방향

1. **더 다양한 예시**: 복합 문장, 전문 분야별
2. **동적 난이도 조절**: 문장 복잡도에 따른 자동 조절
3. **문맥 고려**: 이전 문장과의 연결성
4. **품질 점수**: 각 Case별 자연스러움 점수화
