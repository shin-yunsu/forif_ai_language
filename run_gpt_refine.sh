#!/bin/bash

# 가상환경 활성화
source venv/bin/activate

# OpenAI API 키 확인
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY가 설정되지 않았습니다."
    echo "다음 명령어로 API 키를 설정하세요:"
    echo "export OPENAI_API_KEY='your-api-key-here'"
    exit 1
fi

# 스크립트 실행
echo "🚀 GPT를 사용한 한국어 개선 시작..."

# 첫 번째 인자가 'test'면 테스트 모드
if [ "$1" == "test" ]; then
    echo "🧪 테스트 모드로 실행 (20개 샘플)..."
    python3 refine_korean_with_gpt.py --test --sample-size 20
else
    echo "📚 전체 데이터셋 처리 중..."
    python3 refine_korean_with_gpt.py --input mkqa_.json --output mkqa_refined.json
fi

echo "✅ 완료!"