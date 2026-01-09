"""
USP 트리거 키워드 사전 관리 모듈
- JSON 파일에서 트리거 키워드 로드
- USP 후보 문장 추출
- 신규 후보 단어 탐지 및 승인/거절 관리
"""
import json
import os
import re
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime
from collections import Counter
from dataclasses import dataclass


@dataclass
class UspCandidate:
    """USP 후보 문장"""
    sentence: str
    category: str
    trigger_words: List[str]


class UspDictionary:
    """USP 트리거 키워드 사전 관리 클래스"""

    def __init__(self, trigger_path: str, exclusion_path: str, candidate_path: str):
        self.trigger_path = trigger_path
        self.exclusion_path = exclusion_path
        self.candidate_path = candidate_path

        self._trigger_data = {}
        self._exclusion_data = {}
        self._candidate_data = {}

        self._load_all()

    def _load_all(self) -> None:
        """모든 JSON 파일 로드"""
        # 트리거 키워드 로드
        if os.path.exists(self.trigger_path):
            with open(self.trigger_path, 'r', encoding='utf-8') as f:
                self._trigger_data = json.load(f)
        else:
            self._trigger_data = {"categories": {}}

        # 제거 대상 단어 로드
        if os.path.exists(self.exclusion_path):
            with open(self.exclusion_path, 'r', encoding='utf-8') as f:
                self._exclusion_data = json.load(f)
        else:
            self._exclusion_data = {"words": []}

        # 후보 단어 로드
        if os.path.exists(self.candidate_path):
            with open(self.candidate_path, 'r', encoding='utf-8') as f:
                self._candidate_data = json.load(f)
        else:
            self._candidate_data = {"candidates": [], "rejected": []}

    def get_all_trigger_keywords(self) -> Set[str]:
        """모든 트리거 키워드를 Set으로 반환"""
        keywords = set()
        for cat_data in self._trigger_data.get("categories", {}).values():
            keywords.update(cat_data.get("keywords", []))
        return keywords

    def get_keywords_by_category(self, category: str) -> List[str]:
        """카테고리별 키워드 반환"""
        cat_data = self._trigger_data.get("categories", {}).get(category, {})
        return cat_data.get("keywords", [])

    def get_all_categories(self) -> Dict[str, str]:
        """모든 카테고리와 설명 반환"""
        result = {}
        for cat_name, cat_data in self._trigger_data.get("categories", {}).items():
            result[cat_name] = cat_data.get("description", "")
        return result

    def get_exclusion_words(self) -> Set[str]:
        """제거 대상 단어 Set 반환"""
        return set(self._exclusion_data.get("words", []))

    def get_rejected_words(self) -> Set[str]:
        """거절된 단어 Set 반환"""
        rejected = self._candidate_data.get("rejected", [])
        return {item.get("word", "") for item in rejected}

    def find_trigger_words(self, text: str) -> Optional[Dict]:
        """
        텍스트에서 트리거 키워드 찾기

        Returns:
            {'category': str, 'words': List[str]} or None
        """
        matched_words = []
        matched_category = None

        for cat_name, cat_data in self._trigger_data.get("categories", {}).items():
            for keyword in cat_data.get("keywords", []):
                if keyword in text:
                    matched_words.append(keyword)
                    if matched_category is None:
                        matched_category = cat_name

        if matched_words:
            return {
                "category": matched_category,
                "words": matched_words
            }
        return None

    def has_only_exclusion_words(self, text: str) -> bool:
        """제거 대상 단어만 포함된 문장인지 확인"""
        exclusion_words = self.get_exclusion_words()
        trigger_keywords = self.get_all_trigger_keywords()

        # 트리거 키워드가 하나라도 있으면 False
        for keyword in trigger_keywords:
            if keyword in text:
                return False

        # 제거 대상 단어만 있으면 True
        for word in exclusion_words:
            if word in text:
                return True

        return False

    def extract_usp_candidates(self, reviews: List[str]) -> List[UspCandidate]:
        """
        리뷰 리스트에서 USP 후보 문장 추출

        Args:
            reviews: 리뷰 텍스트 리스트

        Returns:
            USP 후보 리스트
        """
        candidates = []
        seen_sentences = set()  # 중복 방지

        for review in reviews:
            # 문장 단위로 분리
            sentences = self._split_into_sentences(review)

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence or len(sentence) < 5:
                    continue

                # 중복 체크 (앞 30자 기준)
                key = sentence[:30]
                if key in seen_sentences:
                    continue

                # 제거 대상 단어만 있으면 스킵
                if self.has_only_exclusion_words(sentence):
                    continue

                # 트리거 키워드 찾기
                matched = self.find_trigger_words(sentence)
                if matched:
                    candidates.append(UspCandidate(
                        sentence=sentence,
                        category=matched["category"],
                        trigger_words=matched["words"]
                    ))
                    seen_sentences.add(key)

        return candidates

    def _split_into_sentences(self, text: str) -> List[str]:
        """텍스트를 문장 단위로 분리"""
        # 마침표, 느낌표, 물음표, 줄바꿈으로 분리
        sentences = re.split(r'[.!?\n]+', text)
        return [s.strip() for s in sentences if s.strip()]

    # === 후보 관리 ===

    def get_pending_candidates(self) -> List[Dict]:
        """승인 대기 중인 후보 목록"""
        return [c for c in self._candidate_data.get("candidates", [])
                if c.get("status") == "pending"]

    def add_candidate(self, word: str, category: str, example_sentences: List[str]) -> bool:
        """새 후보 추가"""
        # 이미 존재하는지 확인
        existing = self.get_all_trigger_keywords()
        rejected = self.get_rejected_words()

        if word in existing or word in rejected:
            return False

        # 이미 후보에 있는지 확인
        for c in self._candidate_data.get("candidates", []):
            if c.get("word") == word:
                return False

        self._candidate_data["candidates"].append({
            "word": word,
            "suggested_category": category,
            "example_sentences": example_sentences[:3],
            "discovered_at": datetime.now().isoformat(),
            "status": "pending"
        })
        return True

    def approve_candidate(self, word: str, category: str) -> bool:
        """후보 승인 → 사전에 추가"""
        # 후보에서 찾기
        candidate = None
        for c in self._candidate_data.get("candidates", []):
            if c.get("word") == word and c.get("status") == "pending":
                candidate = c
                break

        if not candidate:
            return False

        # 트리거 사전에 추가
        if category not in self._trigger_data.get("categories", {}):
            return False

        keywords = self._trigger_data["categories"][category].get("keywords", [])
        if word not in keywords:
            keywords.append(word)
            self._trigger_data["categories"][category]["keywords"] = keywords

        # 후보 상태 변경
        candidate["status"] = "approved"
        candidate["approved_at"] = datetime.now().isoformat()

        return True

    def reject_candidate(self, word: str, reason: str = "") -> bool:
        """후보 거절"""
        # 후보에서 찾기
        candidate = None
        for c in self._candidate_data.get("candidates", []):
            if c.get("word") == word and c.get("status") == "pending":
                candidate = c
                break

        if not candidate:
            return False

        # 후보 상태 변경
        candidate["status"] = "rejected"

        # 거절 목록에 추가
        self._candidate_data["rejected"].append({
            "word": word,
            "rejected_at": datetime.now().isoformat(),
            "reason": reason
        })

        return True

    def add_keyword(self, word: str, category: str) -> bool:
        """키워드 직접 추가"""
        if category not in self._trigger_data.get("categories", {}):
            return False

        keywords = self._trigger_data["categories"][category].get("keywords", [])
        if word not in keywords:
            keywords.append(word)
            self._trigger_data["categories"][category]["keywords"] = keywords
            return True
        return False

    def remove_keyword(self, word: str) -> bool:
        """키워드 삭제"""
        for cat_name, cat_data in self._trigger_data.get("categories", {}).items():
            keywords = cat_data.get("keywords", [])
            if word in keywords:
                keywords.remove(word)
                return True
        return False

    def save_all(self) -> None:
        """모든 변경사항 저장"""
        # 업데이트 시간
        self._trigger_data["updated_at"] = datetime.now().strftime("%Y-%m-%d")
        self._candidate_data["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        # 저장
        with open(self.trigger_path, 'w', encoding='utf-8') as f:
            json.dump(self._trigger_data, f, ensure_ascii=False, indent=2)

        with open(self.candidate_path, 'w', encoding='utf-8') as f:
            json.dump(self._candidate_data, f, ensure_ascii=False, indent=2)


def detect_new_candidates(
    usp_sentences: List[str],
    existing_keywords: Set[str],
    exclusion_words: Set[str],
    rejected_words: Set[str],
    min_length: int = 2,
    max_length: int = 6
) -> List[Tuple[str, int]]:
    """
    USP 후보 문장에서 신규 후보 단어 탐지

    Args:
        usp_sentences: USP 후보 문장 리스트
        existing_keywords: 기존 트리거 키워드
        exclusion_words: 제거 대상 단어
        rejected_words: 거절된 단어
        min_length: 최소 글자 수
        max_length: 최대 글자 수

    Returns:
        [(단어, 출현횟수), ...] 출현횟수 내림차순
    """
    # 모든 문장 합치기
    all_text = " ".join(usp_sentences)

    # 한글 토큰화 (2-6글자)
    tokens = tokenize_korean(all_text, min_length, max_length)

    # 빈도 계산
    counter = Counter(tokens)

    # 필터링
    candidates = []
    skip_words = existing_keywords | exclusion_words | rejected_words

    for word, count in counter.most_common():
        if word in skip_words:
            continue
        if count < 2:  # 최소 2회 이상 출현
            continue
        candidates.append((word, count))

    return candidates[:50]  # 상위 50개만


def tokenize_korean(text: str, min_length: int = 2, max_length: int = 6) -> List[str]:
    """
    간단한 한국어 토큰화 (형태소 분석기 없이)

    - 의성어/의태어 우선 추출 (반복 형태: 쫀쫀, 찰랑찰랑)
    - 2-6글자 한글 단어 추출
    """
    tokens = []

    # 1. 의성어/의태어 패턴 (2-3글자 반복)
    onomatopoeia_pattern = r'([가-힣]{2,3})\1'
    for match in re.finditer(onomatopoeia_pattern, text):
        tokens.append(match.group(0))

    # 2. 일반 한글 단어 (min~max 글자)
    word_pattern = rf'[가-힣]{{{min_length},{max_length}}}'
    for match in re.finditer(word_pattern, text):
        word = match.group(0)
        # 불용어 제외
        if word in {'그리고', '그래서', '하지만', '그런데', '그래도', '때문에', '이거는', '저거는'}:
            continue
        tokens.append(word)

    return tokens


# 싱글톤 인스턴스 (선택적)
_usp_dict_instance = None

def get_usp_dictionary() -> UspDictionary:
    """USP 사전 싱글톤 인스턴스 반환"""
    global _usp_dict_instance
    if _usp_dict_instance is None:
        from config import TRIGGER_KEYWORDS_PATH, EXCLUSION_WORDS_PATH, CANDIDATE_KEYWORDS_PATH
        _usp_dict_instance = UspDictionary(
            TRIGGER_KEYWORDS_PATH,
            EXCLUSION_WORDS_PATH,
            CANDIDATE_KEYWORDS_PATH
        )
    return _usp_dict_instance


def highlight_trigger_words(text: str, color: str = "#e74c3c") -> str:
    """
    텍스트에서 트리거 키워드와 관련어를 하이라이트 처리

    Args:
        text: 원본 텍스트
        color: 하이라이트 색상 (기본: 빨간색)

    Returns:
        HTML 태그가 포함된 하이라이트 텍스트
    """
    usp_dict = get_usp_dictionary()
    keywords = usp_dict.get_all_trigger_keywords()

    if not keywords:
        return text

    matched_spans = []  # (start, end, matched_text) 튜플 리스트

    # 각 키워드에 대해 관련 단어 찾기 (키워드를 포함하는 모든 한글 단어)
    for keyword in keywords:
        # 키워드를 포함하는 한글 단어 패턴 (예: "향" -> "무향", "자스민향" 등)
        pattern = rf'[가-힣]*{re.escape(keyword)}[가-힣]*'

        for match in re.finditer(pattern, text):
            matched_spans.append((match.start(), match.end(), match.group()))

    if not matched_spans:
        return text

    # 중복 제거 및 겹치는 범위 병합 (긴 매치 우선)
    matched_spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    merged = []
    for span in matched_spans:
        if not merged or span[0] >= merged[-1][1]:
            merged.append(span)
        elif span[1] > merged[-1][1]:
            # 겹치지만 더 긴 경우 확장
            merged[-1] = (merged[-1][0], span[1], text[merged[-1][0]:span[1]])

    # 역순으로 교체 (인덱스 변경 방지)
    result = text
    for start, end, matched_text in reversed(merged):
        highlighted_word = f'<span style="color:{color};font-weight:bold">{matched_text}</span>'
        result = result[:start] + highlighted_word + result[end:]

    return result
