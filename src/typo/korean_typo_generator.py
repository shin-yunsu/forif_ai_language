#!/usr/bin/env python3
"""
Korean Typo Generator - 한국어 오타 생성기
Generates realistic Korean typos following specific linguistic rules
"""

import json
import random
from typing import List, Dict, Tuple
try:
    from jamo import h2j, j2h, is_hangul_char
except ImportError:
    print("Installing jamo for Hangul processing...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'jamo'])
    from jamo import h2j, j2h, is_hangul_char

class KoreanTypoGenerator:
    """한국어 오타 생성기"""

    def __init__(self, seed=None):
        """초기화"""
        if seed:
            random.seed(seed)

        # 모음 교체 매핑 (양방향)
        self.vowel_substitutions = {
            'ㅐ': 'ㅔ', 'ㅔ': 'ㅐ',
            'ㅓ': 'ㅏ', 'ㅏ': 'ㅓ',
            'ㅗ': 'ㅜ', 'ㅜ': 'ㅗ',
            'ㅡ': 'ㅓ', 'ㅣ': 'ㅡ'
        }

        # 자음 교체 매핑 (양방향)
        self.consonant_substitutions = {
            'ㄹ': 'ㄴ', 'ㄴ': 'ㄹ',
            'ㅂ': 'ㅁ', 'ㅁ': 'ㅂ',
            'ㄱ': 'ㅋ', 'ㅋ': 'ㄱ',
            'ㄷ': 'ㅌ', 'ㅌ': 'ㄷ',
            'ㅈ': 'ㅊ', 'ㅊ': 'ㅈ',
            'ㅅ': 'ㅆ', 'ㅆ': 'ㅅ'
        }

        # 초성, 중성, 종성 리스트
        self.CHOSUNG = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")
        self.JUNGSUNG = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
        self.JONGSUNG = [''] + list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")

    def decompose_hangul(self, char):
        """한글 문자를 자모로 분해"""
        if not is_hangul_char(char):
            return None

        code = ord(char) - 0xAC00
        jong = code % 28
        jung = ((code - jong) // 28) % 21
        cho = ((code - jong) // 28) // 21

        return (self.CHOSUNG[cho], self.JUNGSUNG[jung], self.JONGSUNG[jong])

    def compose_hangul(self, cho, jung, jong=''):
        """자모를 한글 문자로 조합"""
        try:
            cho_idx = self.CHOSUNG.index(cho) if cho in self.CHOSUNG else 0
            jung_idx = self.JUNGSUNG.index(jung) if jung in self.JUNGSUNG else 0
            jong_idx = self.JONGSUNG.index(jong) if jong in self.JONGSUNG else 0

            code = 0xAC00 + (cho_idx * 21 * 28) + (jung_idx * 28) + jong_idx
            return chr(code)
        except:
            return None

    def apply_substitution(self, text: str, num_errors: int = 1) -> str:
        """교체 오타 적용"""
        result = text
        applied_positions = []

        for _ in range(num_errors):
            chars = list(result)
            hangul_positions = []

            # 한글 문자 위치 찾기
            for i, char in enumerate(chars):
                if is_hangul_char(char) and i not in applied_positions:
                    hangul_positions.append(i)

            if not hangul_positions:
                break

            # 랜덤 위치 선택
            pos = random.choice(hangul_positions)
            applied_positions.append(pos)
            char = chars[pos]

            # 자모 분해
            decomposed = self.decompose_hangul(char)
            if not decomposed:
                continue

            cho, jung, jong = decomposed

            # 50% 확률로 모음 또는 자음 교체
            if random.random() < 0.5:
                # 모음 교체
                if jung in self.vowel_substitutions:
                    jung = self.vowel_substitutions[jung]
            else:
                # 자음 교체 (초성)
                if cho in self.consonant_substitutions:
                    cho = self.consonant_substitutions[cho]

            # 재조합
            new_char = self.compose_hangul(cho, jung, jong)
            if new_char:
                chars[pos] = new_char
                result = ''.join(chars)

        return result

    def apply_deletion(self, text: str, num_errors: int = 1) -> str:
        """삭제 오타 적용"""
        result = text

        for _ in range(num_errors):
            if len(result) <= 1:
                break

            # 50% 확률로 음절 삭제 또는 자모 삭제
            if random.random() < 0.5 and len(result) > 2:
                # 음절 삭제
                pos = random.randint(0, len(result) - 1)
                result = result[:pos] + result[pos+1:]
            else:
                # 자모 삭제 (종성 제거)
                chars = list(result)
                hangul_positions = []

                for i, char in enumerate(chars):
                    if is_hangul_char(char):
                        decomposed = self.decompose_hangul(char)
                        if decomposed and decomposed[2]:  # 종성이 있는 경우
                            hangul_positions.append(i)

                if hangul_positions:
                    pos = random.choice(hangul_positions)
                    char = chars[pos]
                    decomposed = self.decompose_hangul(char)
                    if decomposed:
                        cho, jung, jong = decomposed
                        # 종성 제거
                        new_char = self.compose_hangul(cho, jung, '')
                        if new_char:
                            chars[pos] = new_char
                            result = ''.join(chars)

        return result

    def apply_insertion(self, text: str, num_errors: int = 1) -> str:
        """추가 오타 적용"""
        result = text

        for _ in range(num_errors):
            if len(result) < 1:
                break

            # 50% 확률로 음절 중복 또는 자모 추가
            if random.random() < 0.5:
                # 음절 중복
                if len(result) > 0:
                    pos = random.randint(0, len(result) - 1)
                    char = result[pos]
                    result = result[:pos+1] + char + result[pos+1:]
            else:
                # 자모 추가 (모음 추가)
                chars = list(result)
                if len(chars) > 0:
                    pos = random.randint(0, len(chars))
                    # 랜덤 모음 추가
                    random_vowel = random.choice(['ㅣ', 'ㅡ', 'ㅏ', 'ㅓ', 'ㅗ', 'ㅜ'])
                    result = result[:pos] + random_vowel + result[pos:]

        return result

    def apply_transposition(self, text: str, num_errors: int = 1) -> str:
        """전치 오타 적용"""
        result = text

        for _ in range(num_errors):
            if len(result) < 2:
                break

            # 음절 전치
            chars = list(result)
            if len(chars) >= 2:
                # 인접한 두 문자 위치 선택
                pos = random.randint(0, len(chars) - 2)
                # 두 문자 교환
                chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
                result = ''.join(chars)

        return result

    def apply_spacing(self, text: str, num_errors: int = 1) -> str:
        """띄어쓰기 오타 적용"""
        result = text

        for _ in range(num_errors):
            # 50% 확률로 공백 제거 또는 추가
            if random.random() < 0.5:
                # 공백 제거
                if ' ' in result:
                    spaces = [i for i, c in enumerate(result) if c == ' ']
                    if spaces:
                        pos = random.choice(spaces)
                        result = result[:pos] + result[pos+1:]
            else:
                # 공백 추가
                if len(result) > 2:
                    # 공백이 아닌 위치 선택
                    non_spaces = [i for i in range(1, len(result) - 1) if result[i] != ' ']
                    if non_spaces:
                        pos = random.choice(non_spaces)
                        result = result[:pos] + ' ' + result[pos:]

        return result

    def generate_typos(self, text: str) -> Dict:
        """모든 오타 유형에 대해 1개와 2개 버전 생성"""
        result = {
            "original": text,
            "substitution": {
                "1_error": self.apply_substitution(text, 1),
                "2_errors": self.apply_substitution(text, 2)
            },
            "deletion": {
                "1_error": self.apply_deletion(text, 1),
                "2_errors": self.apply_deletion(text, 2)
            },
            "insertion": {
                "1_error": self.apply_insertion(text, 1),
                "2_errors": self.apply_insertion(text, 2)
            },
            "transposition": {
                "1_error": self.apply_transposition(text, 1),
                "2_errors": self.apply_transposition(text, 2)
            },
            "spacing": {
                "1_error": self.apply_spacing(text, 1),
                "2_errors": self.apply_spacing(text, 2)
            }
        }

        return result

    def process_batch(self, texts: List[str]) -> List[Dict]:
        """배치 처리"""
        results = []
        for text in texts:
            if isinstance(text, dict) and 'ko' in text:
                text = text['ko']
            results.append(self.generate_typos(text))
        return results

# 테스트 코드
if __name__ == "__main__":
    # 생성기 초기화
    generator = KoreanTypoGenerator(seed=42)

    # 테스트 텍스트
    test_texts = [
        "어디에서 나왔나요",
        "스타벅스 로고는",
        "서울의 인구는?",
        "그들만의 리그",
        "라이온킹 영화"
    ]

    print("한국어 오타 생성 테스트")
    print("=" * 60)

    for text in test_texts:
        result = generator.generate_typos(text)
        print(f"\n원본: {result['original']}")
        print("-" * 40)

        for error_type in ['substitution', 'deletion', 'insertion', 'transposition', 'spacing']:
            print(f"\n{error_type.upper()}:")
            print(f"  1 error: {result[error_type]['1_error']}")
            print(f"  2 errors: {result[error_type]['2_errors']}")

    # JSON 출력 예시
    print("\n" + "=" * 60)
    print("JSON 출력 예시:")
    print("=" * 60)

    batch_results = generator.process_batch(["안녕하세요", "한국어 오타 생성"])
    print(json.dumps(batch_results, ensure_ascii=False, indent=2))