import json
import random
import argparse
from typing import List, Dict, Tuple, Set
import re
import copy

# 한글 유니코드 상수
CHOSUNG_BASE = 0x1100
JUNGSUNG_BASE = 0x1161
JONGSUNG_BASE = 0x11A8
HANGUL_BASE = 0xAC00

# 초성, 중성, 종성 리스트
CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
JUNGSUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
JONGSUNG_LIST = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

# 유사 자모 매핑
SIMILAR_CHOSUNG = {
    'ㄱ': ['ㄲ', 'ㅋ'],
    'ㄲ': ['ㄱ', 'ㅋ'],
    'ㄴ': ['ㄹ', 'ㅁ'],
    'ㄷ': ['ㄸ', 'ㅌ', 'ㄹ'],
    'ㄸ': ['ㄷ', 'ㅌ'],
    'ㄹ': ['ㄴ', 'ㄷ'],
    'ㅁ': ['ㄴ', 'ㅂ'],
    'ㅂ': ['ㅃ', 'ㅍ', 'ㅁ'],
    'ㅃ': ['ㅂ', 'ㅍ'],
    'ㅅ': ['ㅆ', 'ㅈ'],
    'ㅆ': ['ㅅ', 'ㅈ'],
    'ㅈ': ['ㅉ', 'ㅊ', 'ㅅ'],
    'ㅉ': ['ㅈ', 'ㅊ'],
    'ㅊ': ['ㅈ', 'ㅉ'],
    'ㅋ': ['ㄱ', 'ㄲ'],
    'ㅌ': ['ㄷ', 'ㄸ'],
    'ㅍ': ['ㅂ', 'ㅃ'],
    'ㅎ': ['ㅇ'],
    'ㅇ': ['ㅎ']
}

SIMILAR_JUNGSUNG = {
    'ㅏ': ['ㅓ', 'ㅑ'],
    'ㅐ': ['ㅔ', 'ㅒ', 'ㅖ'],
    'ㅑ': ['ㅏ', 'ㅕ'],
    'ㅒ': ['ㅐ', 'ㅖ'],
    'ㅓ': ['ㅏ', 'ㅕ'],
    'ㅔ': ['ㅐ', 'ㅖ'],
    'ㅕ': ['ㅓ', 'ㅑ'],
    'ㅖ': ['ㅔ', 'ㅐ', 'ㅒ'],
    'ㅗ': ['ㅜ', 'ㅛ'],
    'ㅘ': ['ㅙ', 'ㅝ'],
    'ㅙ': ['ㅘ', 'ㅞ'],
    'ㅚ': ['ㅟ', 'ㅗ'],
    'ㅛ': ['ㅗ', 'ㅠ'],
    'ㅜ': ['ㅗ', 'ㅠ'],
    'ㅝ': ['ㅘ', 'ㅞ'],
    'ㅞ': ['ㅝ', 'ㅙ'],
    'ㅟ': ['ㅚ', 'ㅜ'],
    'ㅠ': ['ㅜ', 'ㅛ'],
    'ㅡ': ['ㅣ', 'ㅜ'],
    'ㅢ': ['ㅣ', 'ㅡ'],
    'ㅣ': ['ㅡ', 'ㅢ']
}

# 키보드 인접 자모 매핑 (두벌식 기준)
KEYBOARD_ADJACENT_CHOSUNG = {
    'ㅂ': ['ㅈ', 'ㅁ'],
    'ㅈ': ['ㅂ', 'ㄷ', 'ㄴ'],
    'ㄷ': ['ㅈ', 'ㄱ', 'ㅇ'],
    'ㄱ': ['ㄷ', 'ㅅ', 'ㄹ'],
    'ㅅ': ['ㄱ', 'ㅇ', 'ㅎ'],
    'ㅁ': ['ㅂ', 'ㄴ'],
    'ㄴ': ['ㅈ', 'ㅁ', 'ㅇ'],
    'ㅇ': ['ㄷ', 'ㄴ', 'ㅅ', 'ㄹ'],
    'ㄹ': ['ㄱ', 'ㅇ', 'ㅎ'],
    'ㅎ': ['ㅅ', 'ㄹ'],
    'ㅋ': ['ㅌ'],
    'ㅌ': ['ㅋ', 'ㅊ'],
    'ㅊ': ['ㅌ', 'ㅍ'],
    'ㅍ': ['ㅊ']
}

KEYBOARD_ADJACENT_JUNGSUNG = {
    'ㅛ': ['ㅕ', 'ㅗ'],
    'ㅕ': ['ㅛ', 'ㅓ', 'ㅗ', 'ㅏ'],
    'ㅗ': ['ㅛ', 'ㅕ', 'ㅓ', 'ㅏ', 'ㅜ'],
    'ㅓ': ['ㅕ', 'ㅗ', 'ㅏ', 'ㅜ', 'ㅡ'],
    'ㅏ': ['ㅕ', 'ㅗ', 'ㅓ', 'ㅜ', 'ㅡ', 'ㅣ'],
    'ㅜ': ['ㅗ', 'ㅓ', 'ㅏ', 'ㅡ', 'ㅣ'],
    'ㅡ': ['ㅓ', 'ㅏ', 'ㅜ', 'ㅣ'],
    'ㅣ': ['ㅏ', 'ㅜ', 'ㅡ']
}

def decompose_hangul(char: str) -> Tuple[int, int, int]:
    """한글 문자를 초성, 중성, 종성으로 분해"""
    if '가' <= char <= '힣':
        code = ord(char) - HANGUL_BASE
        cho = code // 588
        jung = (code % 588) // 28
        jong = code % 28
        return cho, jung, jong
    return -1, -1, -1

def compose_hangul(cho: int, jung: int, jong: int) -> str:
    """초성, 중성, 종성을 한글 문자로 조합"""
    if 0 <= cho < 19 and 0 <= jung < 21 and 0 <= jong < 28:
        code = HANGUL_BASE + (cho * 588) + (jung * 28) + jong
        return chr(code)
    return ''

def is_hangul(char: str) -> bool:
    """한글 음절인지 확인"""
    return '가' <= char <= '힣'

def get_hangul_positions(text: str) -> List[int]:
    """문장에서 한글 문자의 위치를 반환"""
    return [i for i, char in enumerate(text) if is_hangul(char)]

# 1. 교체 (Substitution) 함수들
def apply_substitution(text: str, num_errors: int = 1, used_positions: Set[int] = None) -> Tuple[str, Set[int]]:
    """교체 오타를 적용"""
    text_list = list(text)
    hangul_positions = get_hangul_positions(text)
    
    if not hangul_positions:
        return text, set()
    
    if used_positions:
        available_positions = [pos for pos in hangul_positions if pos not in used_positions]
    else:
        available_positions = hangul_positions
        used_positions = set()
    
    if not available_positions:
        return text, used_positions
    
    num_errors = min(num_errors, len(available_positions))
    selected_positions = random.sample(available_positions, num_errors)
    
    for pos in selected_positions:
        char = text_list[pos]
        substitution_type = random.choice(['similar_jamo', 'keyboard_adjacent', 'phonetic'])
        
        if substitution_type == 'similar_jamo':
            text_list[pos] = substitute_similar_jamo(char)
        elif substitution_type == 'keyboard_adjacent':
            text_list[pos] = substitute_keyboard_adjacent(char)
        else:  # phonetic
            text_list[pos] = substitute_phonetic(char)
        
        used_positions.add(pos)
    
    return ''.join(text_list), used_positions

def substitute_similar_jamo(char: str) -> str:
    """유사한 자모로 교체"""
    cho, jung, jong = decompose_hangul(char)
    if cho == -1:
        return char
    
    # 초성 또는 중성 중 하나를 랜덤하게 교체
    if random.random() < 0.5:
        # 초성 교체
        cho_char = CHOSUNG_LIST[cho]
        if cho_char in SIMILAR_CHOSUNG:
            new_cho_char = random.choice(SIMILAR_CHOSUNG[cho_char])
            new_cho = CHOSUNG_LIST.index(new_cho_char)
            return compose_hangul(new_cho, jung, jong)
    else:
        # 중성 교체
        jung_char = JUNGSUNG_LIST[jung]
        if jung_char in SIMILAR_JUNGSUNG:
            new_jung_char = random.choice(SIMILAR_JUNGSUNG[jung_char])
            new_jung = JUNGSUNG_LIST.index(new_jung_char)
            return compose_hangul(cho, new_jung, jong)
    
    return char

def substitute_keyboard_adjacent(char: str) -> str:
    """키보드 인접 자모로 교체"""
    cho, jung, jong = decompose_hangul(char)
    if cho == -1:
        return char
    
    # 초성 또는 중성 중 하나를 랜덤하게 교체
    if random.random() < 0.5:
        cho_char = CHOSUNG_LIST[cho]
        if cho_char in KEYBOARD_ADJACENT_CHOSUNG:
            new_cho_char = random.choice(KEYBOARD_ADJACENT_CHOSUNG[cho_char])
            new_cho = CHOSUNG_LIST.index(new_cho_char)
            return compose_hangul(new_cho, jung, jong)
    else:
        jung_char = JUNGSUNG_LIST[jung]
        if jung_char in KEYBOARD_ADJACENT_JUNGSUNG:
            new_jung_char = random.choice(KEYBOARD_ADJACENT_JUNGSUNG[jung_char])
            new_jung = JUNGSUNG_LIST.index(new_jung_char)
            return compose_hangul(cho, new_jung, jong)
    
    return char

def substitute_phonetic(char: str) -> str:
    """음운적으로 유사한 문자로 교체"""
    # 간단한 예시 구현
    phonetic_map = {
        '지': '치', '치': '지',
        '자': '차', '차': '자',
        '즈': '츠', '츠': '즈'
    }
    
    if char in phonetic_map:
        return phonetic_map[char]
    
    # 기본적으로 similar_jamo로 대체
    return substitute_similar_jamo(char)

# 2. 삭제 (Deletion) 함수들
def apply_deletion(text: str, num_errors: int = 1, used_positions: Set[int] = None) -> Tuple[str, Set[int]]:
    """삭제 오타를 적용"""
    text_list = list(text)
    if used_positions is None:
        used_positions = set()
    
    errors_applied = 0
    for _ in range(num_errors):
        if random.random() < 0.5:
            # 자모 삭제
            text_list, new_used = delete_jamo(text_list, used_positions)
            if new_used != used_positions:
                used_positions = new_used
                errors_applied += 1
        else:
            # 음절 삭제
            text_list, new_used = delete_syllable(text_list, used_positions)
            if new_used != used_positions:
                used_positions = new_used
                errors_applied += 1
    
    return ''.join(text_list), used_positions
def delete_jamo(text_list: List[str], used_positions: Set[int]) -> Tuple[List[str], Set[int]]:
    """자모를 삭제"""
    hangul_positions = [i for i, char in enumerate(text_list) if is_hangul(char) and i not in used_positions]
    if not hangul_positions:
        return text_list, used_positions
    
    pos = random.choice(hangul_positions)
    char = text_list[pos]
    cho, jung, jong = decompose_hangul(char)
    
    # 실제 변경이 일어났는지 추적
    original_char = text_list[pos]
    
    if jong != 0:  # 종성이 있으면 종성 삭제
        text_list[pos] = compose_hangul(cho, jung, 0)
    else:
        # 종성이 없는 경우 다양한 삭제 옵션
        options = []
        
        # 옵션 1: 초성 삭제 (분리된 형태로)
        options.append('delete_cho')
        
        # 옵션 2: 전체 글자 삭제
        options.append('delete_char')
        
        if options:
            choice = random.choice(options)
            
            if choice == 'delete_cho':
                # 초성을 삭제하고 중성만 남기기 (분리된 형태)
                text_list[pos] = JUNGSUNG_LIST[jung]
            elif choice == 'delete_char':
                # 전체 글자 삭제
                del text_list[pos]
                # 삭제 후 인덱스 조정
                new_used = set()
                for p in used_positions:
                    if p < pos:
                        new_used.add(p)
                    elif p > pos:
                        new_used.add(p - 1)
                return text_list, new_used
    
    # 실제로 변경이 일어난 경우에만 used_positions에 추가
    if text_list[pos] != original_char:
        used_positions.add(pos)
    
    return text_list, used_positions
def delete_syllable(text_list: List[str], used_positions: Set[int]) -> Tuple[List[str], Set[int]]:
    """음절을 삭제"""
    if len(text_list) <= 1:
        return text_list, used_positions
    
    hangul_positions = [i for i, char in enumerate(text_list) if is_hangul(char) and i not in used_positions]
    if hangul_positions:
        pos = random.choice(hangul_positions)
        # 삭제할 때는 위치를 추적하기 어려우므로 삭제된 위치 이후 위치를 조정
        del text_list[pos]
        # 삭제 후 인덱스 조정
        new_used = set()
        for p in used_positions:
            if p < pos:
                new_used.add(p)
            elif p > pos:
                new_used.add(p - 1)
        return text_list, new_used
    
    return text_list, used_positions

# 3. 추가 (Insertion) 함수들
def apply_insertion(text: str, num_errors: int = 1, used_positions: Set[int] = None) -> Tuple[str, Set[int]]:
    """추가 오타를 적용"""
    text_list = list(text)
    if used_positions is None:
        used_positions = set()
    
    for _ in range(num_errors):
        if random.random() < 0.5:
            # 자모 추가
            text_list, used_positions = insert_jamo(text_list, used_positions)
        else:
            # 음절 추가
            text_list, used_positions = insert_syllable(text_list, used_positions)
    
    return ''.join(text_list), used_positions

def insert_jamo(text_list: List[str], used_positions: Set[int]) -> Tuple[List[str], Set[int]]:
    """자모를 추가"""
    hangul_positions = [i for i, char in enumerate(text_list) if is_hangul(char) and i not in used_positions]
    if not hangul_positions:
        return text_list, used_positions
    
    pos = random.choice(hangul_positions)
    char = text_list[pos]
    cho, jung, jong = decompose_hangul(char)
    
    if jong == 0:  # 종성이 없으면 종성 추가
        new_jong = random.choice(range(1, 28))
        text_list[pos] = compose_hangul(cho, jung, new_jong)
        used_positions.add(pos)
    else:  # 종성이 있으면
        # 여러 옵션 중 랜덤 선택
        option = random.choice(['double_consonant', 'add_char'])
        
        if option == 'double_consonant':
            # 단자음을 복자음으로 변경 (가능한 경우만)
            double_consonant_map = {
                1: 3,   # ㄱ → ㄳ
                4: 5,   # ㄴ → ㄵ
                4: 6,   # ㄴ → ㄶ
                8: 9,   # ㄹ → ㄺ
                8: 10,  # ㄹ → ㄻ
                8: 11,  # ㄹ → ㄼ
                8: 12,  # ㄹ → ㄽ
                8: 13,  # ㄹ → ㄾ
                8: 14,  # ㄹ → ㄿ
                8: 15,  # ㄹ → ㅀ
                17: 18, # ㅂ → ㅄ
            }
            
            if jong in double_consonant_map:
                text_list[pos] = compose_hangul(cho, jung, double_consonant_map[jong])
            else:
                # 복자음 변경이 불가능하면 자모를 분리된 형태로 추가
                text_list[pos] = char + JONGSUNG_LIST[jong]
        else:
            # 종성을 분리된 형태로 추가
            text_list[pos] = char + JONGSUNG_LIST[jong]
        
        used_positions.add(pos)
    
    return text_list, used_positions

def insert_syllable(text_list: List[str], used_positions: Set[int]) -> Tuple[List[str], Set[int]]:
    """음절을 추가 (중복)"""
    hangul_positions = [i for i, char in enumerate(text_list) if is_hangul(char) and i not in used_positions]
    if not hangul_positions:
        return text_list, used_positions
    
    pos = random.choice(hangul_positions)
    # 해당 위치의 문자를 중복
    text_list.insert(pos, text_list[pos])
    
    # 삽입 후 인덱스 조정
    new_used = set()
    for p in used_positions:
        if p >= pos:
            new_used.add(p + 1)
        else:
            new_used.add(p)
    new_used.add(pos)  # 삽입된 위치도 사용된 것으로 표시
    
    return text_list, new_used

# 4. 전치 (Transposition) 함수들
def apply_transposition(text: str, num_errors: int = 1, used_positions: Set[int] = None) -> Tuple[str, Set[int]]:
    """전치 오타를 적용"""
    text_list = list(text)
    if used_positions is None:
        used_positions = set()
    
    for _ in range(num_errors):
        if random.random() < 0.3:
            # 자모 전치 (분리된 형태로)
            result = transpose_jamo(text_list, used_positions)
            if result:
                text_list, used_positions = result
        else:
            # 음절 전치
            result = transpose_syllable(text_list, used_positions)
            if result:
                text_list, used_positions = result
    
    return ''.join(text_list), used_positions

def transpose_jamo(text_list: List[str], used_positions: Set[int]) -> Tuple[List[str], Set[int]]:
    """자모 순서를 전치 (분리된 형태로 - 예: 호 → ㅗㅎ)"""
    hangul_positions = [i for i, char in enumerate(text_list) if is_hangul(char) and i not in used_positions]
    if not hangul_positions:
        return None
    
    pos = random.choice(hangul_positions)
    char = text_list[pos]
    cho, jung, jong = decompose_hangul(char)
    
    # 자모를 분리된 형태로 표현
    # 종성이 있는 경우와 없는 경우 구분
    if jong != 0:
        # 종성이 있으면 초성+중성+종성 중에서 순서 바꾸기
        if random.random() < 0.5:
            # 중성을 앞으로
            text_list[pos] = JUNGSUNG_LIST[jung] + CHOSUNG_LIST[cho] + JONGSUNG_LIST[jong]
        else:
            # 초성과 중성 위치 교환, 종성은 그대로
            text_list[pos] = JUNGSUNG_LIST[jung] + CHOSUNG_LIST[cho]
            if jong != 0:
                text_list[pos] += JONGSUNG_LIST[jong]
    else:
        # 종성이 없으면 초성과 중성만 교환 (예: 호 → ㅗㅎ)
        text_list[pos] = JUNGSUNG_LIST[jung] + CHOSUNG_LIST[cho]
    
    used_positions.add(pos)
    return text_list, used_positions

def transpose_syllable(text_list: List[str], used_positions: Set[int]) -> Tuple[List[str], Set[int]]:
    """인접한 음절 순서를 전치"""
    hangul_positions = [i for i, char in enumerate(text_list) if is_hangul(char)]
    
    # 사용되지 않은 연속된 한글 위치 찾기
    for i in range(len(hangul_positions) - 1):
        pos1, pos2 = hangul_positions[i], hangul_positions[i+1]
        if pos2 - pos1 == 1 and pos1 not in used_positions and pos2 not in used_positions:
            text_list[pos1], text_list[pos2] = text_list[pos2], text_list[pos1]
            used_positions.add(pos1)
            used_positions.add(pos2)
            return text_list, used_positions
    
    return None

# 5. 띄어쓰기 오류 (Spacing) 함수들
def apply_spacing_error(text: str, num_errors: int = 1, used_positions: Set[int] = None) -> Tuple[str, Set[int]]:
    """띄어쓰기 오타를 적용"""
    if used_positions is None:
        used_positions = set()
    
    for _ in range(num_errors):
        if ' ' in text and random.random() < 0.5:
            # 공백 삭제
            text, new_pos = remove_space(text, used_positions)
            if new_pos:
                used_positions.update(new_pos)
        else:
            # 공백 추가
            text, new_pos = add_space(text, used_positions)
            if new_pos:
                used_positions.update(new_pos)
    
    return text, used_positions

def remove_space(text: str, used_positions: Set[int]) -> Tuple[str, Set[int]]:
    """공백을 제거"""
    spaces = [i for i, char in enumerate(text) if char == ' ' and i not in used_positions]
    if spaces:
        pos = random.choice(spaces)
        text = text[:pos] + text[pos+1:]
        return text, {pos}
    return text, set()

def add_space(text: str, used_positions: Set[int]) -> Tuple[str, Set[int]]:
    """불필요한 공백을 추가"""
    # 조사 앞에 공백 추가
    particles = ['을', '를', '이', '가', '은', '는', '와', '과', '에', '에서', '으로', '로', '의']
    
    for particle in particles:
        if particle in text:
            # 조사의 위치 찾기
            idx = text.find(particle)
            while idx != -1:
                if idx > 0 and idx not in used_positions and text[idx-1] != ' ':
                    text = text[:idx] + ' ' + text[idx:]
                    return text, {idx}
                idx = text.find(particle, idx + 1)
    
    # 랜덤 위치에 공백 추가
    hangul_positions = get_hangul_positions(text)
    available = [i for i in hangul_positions[1:] if i not in used_positions]
    if available:
        pos = random.choice(available)
        text = text[:pos] + ' ' + text[pos:]
        return text, {pos}
    
    return text, set()

def generate_typos_for_sentence(sentence: str) -> Dict:
    """문장에 대해 모든 타입의 오타를 생성"""
    result = {"original": sentence}
    
    # 1. Substitution - 1_error 먼저 생성하고, 그것을 기반으로 2_errors 생성
    sub_1, used_pos_sub = apply_substitution(sentence, 1)
    sub_2, _ = apply_substitution(sub_1, 1, used_pos_sub)  # 1_error를 기반으로 추가
    result["substitution"] = {
        "1_error": sub_1,
        "2_errors": sub_2
    }
    
    # 2. Deletion - 1_error 먼저 생성하고, 그것을 기반으로 2_errors 생성
    del_1, used_pos_del = apply_deletion(sentence, 1)
    del_2, _ = apply_deletion(del_1, 1, used_pos_del)
    result["deletion"] = {
        "1_error": del_1,
        "2_errors": del_2
    }
    
    # 3. Insertion - 1_error 먼저 생성하고, 그것을 기반으로 2_errors 생성
    ins_1, used_pos_ins = apply_insertion(sentence, 1)
    ins_2, _ = apply_insertion(ins_1, 1, used_pos_ins)
    result["insertion"] = {
        "1_error": ins_1,
        "2_errors": ins_2
    }
    
    # 4. Transposition - 1_error 먼저 생성하고, 그것을 기반으로 2_errors 생성
    trans_1, used_pos_trans = apply_transposition(sentence, 1)
    trans_2, _ = apply_transposition(trans_1, 1, used_pos_trans)
    result["transposition"] = {
        "1_error": trans_1,
        "2_errors": trans_2
    }
    
    # 5. Spacing - 1_error 먼저 생성하고, 그것을 기반으로 2_errors 생성
    space_1, used_pos_space = apply_spacing_error(sentence, 1)
    space_2, _ = apply_spacing_error(space_1, 1, used_pos_space)
    result["spacing"] = {
        "1_error": space_1,
        "2_errors": space_2
    }
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Generate Korean typos from input JSON file')
    parser.add_argument('--input', required=True, help='Input JSON file path')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    
    args = parser.parse_args()
    
    # 입력 파일 읽기
    with open(args.input, 'r', encoding='utf-8') as f:
        input_data = json.load(f)
    
    # 입력이 문자열 리스트인지 확인
    if not isinstance(input_data, list):
        raise ValueError("Input must be a list of strings")
    
    # 각 문장에 대해 오타 생성
    results = []
    for sentence in input_data:
        if isinstance(sentence, str):
            result = generate_typos_for_sentence(sentence)
            results.append(result)
    
    # 결과를 JSON 파일로 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Typo generation complete. Results saved to {args.output}")

if __name__ == "__main__":
    main()