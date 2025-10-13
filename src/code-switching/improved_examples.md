# 개선된 Few-Shot 예제 세트

## 설계 원칙
1. **다양성**: 7가지 문장 유형 커버
2. **명확성**: 단계별 변화가 확실히 보임
3. **실용성**: 실제 자주 쓰이는 패턴
4. **엣지 케이스**: null 처리가 필요한 경우들

---

## 예제 1: 전문용어 (의학/과학)
**강점**: 전문용어가 많아 단계별 치환이 명확함

입력:
- 한국어: 인슐린 의존 당뇨병 환자를 위한 다이어트 계획에서 어떤 요소가 필수로 고려되나요?
- 영어: What factors are considered essential in the diet plan for insulin-dependent diabetic patients?

**핵심용어**: 인슐린, 당뇨병, 환자, 다이어트 계획, 요소, 필수

출력:
```json
{
  "Case2": "insulin 의존 diabetes 환자를 위한 diet plan에서 어떤 요소가 필수로 고려되나요?",
  "Case3": "insulin-dependent diabetes patients를 위한 diet plan에서 어떤 factors가 essential하게 고려되나요?",
  "Case4": "What factors are considered essential in the diet plan for 인슐린 의존 당뇨병 환자?",
  "Case5": "What 요소들이 considered essential in the 다이어트 계획 for 인슐린 의존 당뇨병 환자?"
}
```

---

## 예제 2: 역사적 고유명사
**강점**: 고유명사 처리와 문맥 보존이 중요

입력:
- 한국어: 르완다에서 후투와 투치의 분류는 어디에서 유래되었나요?
- 영어: Where did the classification of Hutu and Tutsi in Rwanda originate?

**핵심용어**: 르완다/Rwanda, 후투/Hutu, 투치/Tutsi, 분류/classification, 유래/originate

출력:
```json
{
  "Case2": "Rwanda에서 Hutu와 Tutsi의 분류는 어디에서 유래되었나요?",
  "Case3": "Rwanda에서 Hutu와 Tutsi의 classification은 어디에서 originate되었나요?",
  "Case4": "Where did the classification of Hutu와 Tutsi in 르완다 originate?",
  "Case5": "Where did the 분류 of Hutu와 Tutsi in 르완다 originate?"
}
```

---

## 예제 3: 복합 문장 (두 개의 질문)
**강점**: 복잡한 구조에서도 일관된 패턴 유지

입력:
- 한국어: 누가 DDT의 속성에 관한 연구로 노벨상을 받았나요? 어떤 속성이 그것을 그렇게 가치 있게 만들었나요?
- 영어: who won the nobel prize for work on the properties of ddt what property made it so valuable

**핵심용어**: DDT, 속성/properties, 연구/work, 노벨상/nobel prize, 가치/valuable

출력:
```json
{
  "Case2": "누가 DDT의 properties에 관한 research로 nobel prize를 받았나요? 어떤 property가 그것을 그렇게 valuable하게 만들었나요?",
  "Case3": "누가 DDT의 properties에 관한 work로 nobel prize를 won했나요? 어떤 property가 그것을 그렇게 valuable하게 made했나요?",
  "Case4": "who won the nobel prize for 연구 on the properties of DDT? what property made it so 가치 있게?",
  "Case5": "who won the 노벨상 for 연구 on the 속성 of DDT? what 속성이 made it so 가치 있게?"
}
```

---

## 예제 4: 의문사 보존 (중요!)
**강점**: 의문사는 절대 교체하지 않는 규칙 강조

입력:
- 한국어: 1941년 소련의 침공 이후 어떤 일이 일어났나요?
- 영어: what happened following the invasion of the soviet union in 1941

**핵심용어**: 소련/soviet union, 침공/invasion, 일/event, 일어나다/happen
**주의**: "어떤"은 의문사이므로 교체 금지!

출력:
```json
{
  "Case2": "1941년 Soviet Union의 invasion 이후 어떤 일이 happened?",
  "Case3": "1941년 Soviet Union의 invasion 이후 어떤 event가 happened?",
  "Case4": "what happened following the 침공 of the 소련 in 1941",
  "Case5": "what happened following the 소련 침공 in 1941"
}
```

---

## 예제 5: 동사 중심 문장
**강점**: 하이브리드 동사(영어 동사+한국어 어미) 활용 보여줌

입력:
- 한국어: 아샨티 왕국을 건설하기 위해 누가 금과 노예를 거래했나요?
- 영어: who traded gold and slaves to build the asante kingdom

**핵심용어**: 아샨티/asante, 왕국/kingdom, 건설/build, 금/gold, 노예/slaves, 거래/trade

출력:
```json
{
  "Case2": "Asante Kingdom을 건설하기 위해 누가 gold와 slaves를 거래했나요?",
  "Case3": "Asante Kingdom을 build하기 위해 누가 gold와 slaves를 traded했나요?",
  "Case4": "who traded gold and slaves to build the 아샨티 왕국?",
  "Case5": "who traded 금 and 노예 to build the 아샨티 왕국?"
}
```

---

## 예제 6: 비교/대조 구조
**강점**: 복잡한 논리 구조에서의 code-switching

입력:
- 한국어: 왜 어떤 나라들은 자연 증가율을 줄이는 것을 원하지 않을까요?
- 영어: why a country may not want to reduce its rate of natural increase

**핵심용어**: 나라/country, 자연 증가율/rate of natural increase, 줄이다/reduce, 원하다/want

출력:
```json
{
  "Case2": "왜 어떤 countries는 natural increase rate를 줄이는 것을 원하지 않을까요?",
  "Case3": "왜 어떤 countries는 rate of natural increase를 reduce하는 것을 want하지 않을까요?",
  "Case4": "why a country may not want to reduce its 자연 증가율?",
  "Case5": "why a 나라 may not want to 줄이는 its 자연 증가율?"
}
```

---

## 예제 7: null 케이스 (엣지 케이스)
**강점**: 교체할 핵심용어가 없는 경우의 처리

입력:
- 한국어: 자바빈 또는 빈은 자바 클래스입니다.
- 영어: a javabean or bean is a java class that

**분석**:
- 자바빈/javabean (동일)
- 빈/bean (동일)
- 자바/java (동일)
- 클래스/class (동일)
→ 교체 가능한 핵심용어 없음!

출력:
```json
{
  "Case2": null,
  "Case3": null,
  "Case4": null,
  "Case5": null
}
```

---

## 예제 8: 추상 개념 + 구체적 행동
**강점**: 추상/구체 단어 mix 패턴

입력:
- 한국어: 기후 변화가 생태계에 미치는 영향을 어떻게 측정하나요?
- 영어: how do you measure the impact of climate change on ecosystems

**핵심용어**: 기후 변화/climate change, 생태계/ecosystems, 영향/impact, 측정/measure

출력:
```json
{
  "Case2": "climate change가 생태계에 미치는 impact를 어떻게 측정하나요?",
  "Case3": "climate change가 ecosystems에 미치는 impact를 어떻게 measure하나요?",
  "Case4": "how do you measure the impact of 기후 변화 on 생태계?",
  "Case5": "how do you 측정 the 영향 of 기후 변화 on 생태계?"
}
```

---

## 예제 9: null 케이스 2 (짧은 문장)
**강점**: 핵심용어가 부족한 경우

입력:
- 한국어: 미국의 수정 헌법을 보여줘요.
- 영어: show me the amendments of the united states

**분석**:
- 핵심용어: 미국/united states, 수정 헌법/amendments, 보여주다/show
- 3개뿐이라 단계별 증가 어려움

출력:
```json
{
  "Case2": null,
  "Case3": null,
  "Case4": null,
  "Case5": null
}
```

---

## 📋 예제 선택 가이드

### GPT.py (Case2-4)용 - 5개 추천:
1. **예제 1** (전문용어) - 명확한 패턴
2. **예제 4** (의문사 보존) - 중요 규칙
3. **예제 5** (동사 중심) - 하이브리드 동사
4. **예제 6** (비교/대조) - 복잡한 구조
5. **예제 7** (null) - 엣지 케이스

### Gemini.py (Case2-5)용 - 7개 추천:
1. **예제 1** (전문용어)
2. **예제 2** (고유명사)
3. **예제 3** (복합 문장)
4. **예제 4** (의문사 보존)
5. **예제 5** (동사 중심)
6. **예제 8** (추상+구체)
7. **예제 9** (null 케이스 2)

---

## 🎯 개선 포인트

1. **다양성 ↑**: 7가지 문장 유형 (의학, 역사, 복합, 추상 등)
2. **명확성 ↑**: 단계별 변화가 확실히 보임
3. **실용성 ↑**: 실제 자주 쓰이는 패턴들
4. **엣지 케이스 ↑**: 2개의 null 예제로 강화
5. **규칙 강조**: 의문사 보존, 하이브리드 동사 등

이 예제들은 모델이 더 확실하고 창의적인 code-switching을 생성하도록 도와줍니다!
