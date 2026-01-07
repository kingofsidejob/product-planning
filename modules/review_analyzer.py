"""
리뷰 장단점 분석 모듈 (문맥 기반)
- 부정어 처리로 문맥 파악 ("자극 없이" = 긍정)
- 마케팅 포인트 분석 (반복 키워드, 경쟁제품 비교)
"""
import re
from collections import Counter
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass, field


# 부정어 패턴 (키워드 앞에 오면 의미 반전)
NEGATION_PATTERNS = [
    r'없', r'않', r'안\s', r'못\s', r'아니', r'NO', r'no',
    r'전혀', r'별로', r'그다지', r'딱히',
]

# 긍정 수식어 패턴 (이 단어 뒤에 키워드가 오면 긍정)
POSITIVE_MODIFIER_PATTERNS = [
    r'좋은', r'좋아', r'좋고', r'좋음', r'괜찮', r'은은', r'부드러', r'상쾌', r'향긋',
]

# 긍정 키워드 (화장품 관련)
POSITIVE_KEYWORDS = {
    # 효과/결과
    '좋아요': 1.0, '좋아': 1.0, '좋음': 1.0, '최고': 1.2, '대박': 1.2,
    '굿': 1.0, '짱': 1.0, '완전': 0.8, '진짜': 0.6,
    '효과': 0.8, '개선': 1.0, '좋아졌': 1.0, '나아졌': 1.0,
    # 보습/수분
    '촉촉': 1.2, '보습': 1.0, '수분': 0.8, '촉촉해': 1.2, '촉촉하고': 1.2,
    # 흡수
    '흡수': 0.8, '빠른흡수': 1.0, '스며': 0.8, '흡수빠름': 1.0,
    # 순함/자극없음
    '순해요': 1.2, '순하고': 1.2, '순함': 1.2, '무자극': 1.2,
    # 가성비
    '가성비': 1.0, '갓성비': 1.0, '저렴': 0.8, '합리적': 0.8,
    # 사용감
    '발림성': 0.8, '부드러': 1.0, '산뜻': 1.0, '가벼': 0.8,
    '쫀쫀': 0.8, '촉촉함': 1.0,
    # 향
    '향좋아': 1.0, '향이좋': 1.0, '은은': 0.8,
    # 재구매/추천
    '재구매': 1.5, '재구': 1.2, '또사': 1.2, '추천': 1.2, '강추': 1.5,
    '인생템': 1.5, '꿀템': 1.2, '만족': 1.0, '득템': 1.0,
    # 피부상태
    '화장잘': 1.0, '밀착': 0.8, '지속력': 0.8, '커버력': 0.8,
}

# 부정 키워드 (이 키워드가 부정어와 함께 쓰이면 긍정이 됨)
NEGATIVE_KEYWORDS = {
    # 부작용
    '트러블': 1.2, '뾰루지': 1.2, '올라': 0.6, '빨개': 0.8,
    '자극': 1.0, '따가': 1.0, '따끔': 1.0, '화끈': 0.8,
    '가려': 0.8, '간지러': 0.8, '알러지': 1.0, '두드러기': 1.0,
    # 사용감 불만
    '끈적': 1.0, '끈적거': 1.0, '무거': 0.8, '답답': 0.8,
    '기름': 0.6, '번들': 0.8, '유분': 0.6,
    '밀림': 1.0, '밀려': 1.0, '들뜸': 0.8, '각질': 0.6, '뭉침': 0.8,
    # 효과 없음
    '별로': 0.8, '애매': 0.6, '모르겠': 0.6, '효과없': 1.0,
    '기대이하': 1.0, '실망': 1.0, '아쉬': 0.8, '후회': 1.0,
    # 향 불만 (문맥 판단 필요한 것은 CONTEXT_SENSITIVE_KEYWORDS로 이동)
    '향강해': 0.8, '향이강': 0.8, '인공향': 0.8,
    # 가격
    '비싸': 0.8, '비쌈': 0.8,
    # 기타
    '비추': 1.2, '환불': 1.0, '교환': 0.6,
}

# 반전 키워드 (부정어와 함께 쓰이면 의미가 반전됨)
REVERSIBLE_KEYWORDS = {
    '자극', '끈적', '끈적거', '트러블', '뾰루지', '밀림', '밀려',
    '들뜸', '무거', '답답', '기름', '번들', '각질', '뭉침',
    '따가', '가려', '화끈', '흡수안'
}

# 문맥에 따라 긍정/부정이 달라지는 키워드 (문장 전체 분석)
CONTEXT_SENSITIVE_KEYWORDS = {
    '냄새': {
        'positive_patterns': [
            r'냄새.{0,10}좋', r'좋은.{0,5}냄새', r'냄새.{0,10}괜찮',
            r'냄새.{0,5}(없|안\s*나)', r'냄새.{0,10}은은',
        ],
        'negative_patterns': [
            r'냄새.{0,5}(나요|나서|심해|이상|별로|싫)',
        ],
        'default': 'neutral'
    },
    '향': {
        'positive_patterns': [
            r'향.{0,10}좋', r'좋은.{0,5}향', r'향.{0,10}(은은|부드|상쾌|괜찮|마음에)',
            r'향기.{0,5}(좋|나|롭)',
        ],
        'negative_patterns': [
            r'향.{0,5}(강해|쎄|별로|거부|인공|싫)',
        ],
        'default': 'neutral'
    },
    '트러블': {
        # "평소에 트러블 많은데 이거 쓰고 없어졌다" 같은 패턴 처리
        'positive_patterns': [
            r'트러블.{0,15}(없|안\s*(나|생|올라))',
            r'트러블.{0,5}(이|가)?.{0,10}(없|안)',
            r'(있었는데|많았는데|났었는데).{0,20}(트러블|뾰루지).{0,10}(없|안)',
            r'트러블.{0,20}(사라|줄|좋아|개선|진정)',
            r'(쓰고|바르고|사용하고).{0,20}트러블.{0,10}(없|안)',
        ],
        'negative_patterns': [
            r'트러블.{0,5}(나|생기|올라왔|났)',
            r'(쓰고|바르고|사용하고).{0,10}트러블.{0,5}(나|생)',
        ],
        'default': 'negative'
    },
    '자극': {
        'positive_patterns': [
            r'자극.{0,15}(없|안)',
            r'자극.{0,5}(이|가)?.{0,10}(없|안)',
            r'(무|저)자극',
            r'자극.{0,10}(적|덜)',
            r'(예민|민감).{0,15}(인데|한데).{0,15}자극.{0,10}(없|안|괜찮)',
        ],
        'negative_patterns': [
            r'자극.{0,5}(있|되|느껴|심)',
            r'자극.{0,5}(이|가)?.{0,5}(있|되)',
        ],
        'default': 'negative'
    },
    '끈적': {
        'positive_patterns': [
            r'끈적.{0,15}(없|안)',
            r'끈적.{0,5}(임|거림)?.{0,10}(없|안)',
            r'(생각보다|의외로).{0,10}끈적.{0,10}(없|안)',
        ],
        'negative_patterns': [
            r'끈적.{0,5}(여|거려|해|함|있)',
        ],
        'default': 'negative'
    },
}

# 문장 레벨 긍정 전환 패턴 (과거 부정 → 현재 긍정)
SENTENCE_REVERSAL_PATTERNS = [
    # "평소에 XXX 있는데/많은데 이거 쓰고 없어졌다/안 난다"
    (r'(평소|원래|전에|예전).{0,15}(트러블|뾰루지|자극|각질).{0,15}(있|많|났|생).{0,20}(이거|이\s*제품|사용).{0,20}(없|안|사라|줄|좋아)', 'positive'),
    # "XXX이 있었는데/많았는데 없어졌다/줄었다"
    (r'(트러블|뾰루지|자극|끈적|각질).{0,10}(이|가)?\s*(있었는데|많았는데|났었는데|생겼었는데|심했는데).{0,20}(없|안|사라|줄|진정)', 'positive'),
    # "걱정했는데 XXX 없었다"
    (r'(걱정|염려|불안).{0,15}(트러블|자극|끈적).{0,15}(없|안|괜찮)', 'positive'),
    # "민감한데 XXX 없다"
    (r'(민감|예민|약한).{0,10}(피부|편)?.{0,15}(트러블|자극).{0,15}(없|안|괜찮)', 'positive'),
    # "쓰고/바르고/사용하고 나서 XXX 없다/줄었다"
    (r'(쓰고|바르고|사용하고|발라보니|써보니).{0,20}(트러블|뾰루지|자극|끈적).{0,15}(없|안|사라|줄)', 'positive'),
    # "XXX이 평소에 많은데 이거 쓰고 그런게 없다"
    (r'(트러블|뾰루지|자극).{0,10}(이|가)?\s*평소.{0,10}(있|많).{0,20}(이거|이\s*제품|쓰고).{0,20}(그런\s*게|그런거)?\s*(없|안)', 'positive'),
    # "원래 XXX 잘 나는/생기는 편인데 안 났다"
    (r'(원래|평소).{0,10}(트러블|뾰루지|자극).{0,10}(잘|자주).{0,10}(나|생기|올라).{0,15}(인데|편인데).{0,15}(없|안)', 'positive'),
    # "XXX 많은 편인데 괜찮다/좋다"
    (r'(트러블|뾰루지|자극|끈적).{0,10}(많은|자주|쉬운).{0,10}(편|타입).{0,15}(인데|이지만).{0,15}(괜찮|좋|없|안)', 'positive'),
]


def has_negation_before(text: str, keyword: str, window: int = 8) -> bool:
    """키워드 앞에 부정어가 있는지 확인 (window 글자 내)"""
    idx = text.find(keyword)
    if idx == -1:
        return False

    # 키워드 앞 window 글자 확인
    start = max(0, idx - window)
    before_text = text[start:idx]

    for neg_pattern in NEGATION_PATTERNS:
        if re.search(neg_pattern, before_text):
            return True

    return False


def analyze_context_sensitive_keyword(text: str, keyword: str) -> str:
    """
    문맥에 따라 감성이 달라지는 키워드 분석

    Returns:
        'positive', 'negative', or 'neutral'
    """
    if keyword not in CONTEXT_SENSITIVE_KEYWORDS:
        return 'neutral'

    config = CONTEXT_SENSITIVE_KEYWORDS[keyword]

    # 긍정 패턴 체크
    for pattern in config['positive_patterns']:
        if re.search(pattern, text):
            return 'positive'

    # 부정 패턴 체크
    for pattern in config['negative_patterns']:
        if re.search(pattern, text):
            return 'negative'

    return config['default']


def analyze_sentiment_with_context(text: str) -> Tuple[str, List[str], List[str], float]:
    """
    문맥 기반 감성 분석 (전체 문장 패턴 우선)

    Returns:
        (sentiment, positive_found, negative_found, score)
    """
    text_clean = text.replace('\n', ' ').strip()

    positive_found = []
    negative_found = []
    score = 0.0

    # 0. 문장 레벨 긍정 전환 패턴 먼저 체크 (가장 우선!)
    # 예: "평소에 트러블 많았는데 이거 쓰고 없어졌다" → 전체가 긍정
    matched_keywords = set()  # 문장 패턴으로 이미 처리된 키워드
    for pattern, sentiment_type in SENTENCE_REVERSAL_PATTERNS:
        match = re.search(pattern, text_clean)
        if match:
            matched_text = match.group(0)
            if sentiment_type == 'positive':
                positive_found.append(f"문맥전환긍정({matched_text[:20]}...)")
                score += 2.0  # 문장 레벨 패턴은 더 높은 점수
                # 해당 문장에서 언급된 부정 키워드들은 처리 완료로 표시
                for kw in ['트러블', '뾰루지', '자극', '끈적', '각질']:
                    if kw in matched_text:
                        matched_keywords.add(kw)

    # 1. 문맥 민감 키워드 체크 (냄새, 향, 트러블, 자극 등)
    # 단, 문장 패턴으로 이미 처리된 키워드는 제외
    for keyword in CONTEXT_SENSITIVE_KEYWORDS:
        if keyword in text_clean and keyword not in matched_keywords:
            context_result = analyze_context_sensitive_keyword(text_clean, keyword)
            if context_result == 'positive':
                positive_found.append(f"{keyword}(긍정)")
                score += 1.0
            elif context_result == 'negative':
                negative_found.append(keyword)
                score -= 1.0
            # neutral은 점수에 반영 안 함

    # 2. 긍정 키워드 체크
    for keyword, weight in POSITIVE_KEYWORDS.items():
        if keyword in text_clean:
            # 긍정 키워드 앞에 부정어가 있으면 무시
            if not has_negation_before(text_clean, keyword):
                positive_found.append(keyword)
                score += weight

    # 3. 부정 키워드 체크 (문맥 고려)
    for keyword, weight in NEGATIVE_KEYWORDS.items():
        # 문맥 민감 키워드는 이미 위에서 처리됨
        if keyword in CONTEXT_SENSITIVE_KEYWORDS:
            continue

        # 문장 패턴으로 이미 처리된 키워드는 제외
        if keyword in matched_keywords:
            continue

        if keyword in text_clean:
            # 반전 가능한 키워드인 경우 부정어 체크
            if keyword in REVERSIBLE_KEYWORDS:
                if has_negation_before(text_clean, keyword):
                    # "자극 없이" → 긍정
                    positive_found.append(f"{keyword}없음")
                    score += weight  # 긍정 점수로 추가
                else:
                    # "자극이 있어" → 부정
                    negative_found.append(keyword)
                    score -= weight
            else:
                negative_found.append(keyword)
                score -= weight

    # 감성 판정 (중립은 긍정으로 분류)
    if score < -0.5:
        sentiment = 'negative'
    else:
        sentiment = 'positive'  # 중립 포함

    return sentiment, positive_found, negative_found, score


@dataclass
class ReviewAnalysisResult:
    """리뷰 분석 결과"""
    total_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_ratio: float
    strengths: List[str]
    weaknesses: List[str]
    top_positive_keywords: List[Tuple[str, int]]
    top_negative_keywords: List[Tuple[str, int]]
    category_scores: Dict[str, float]
    summary: str


@dataclass
class MarketingPointResult:
    """마케팅 포인트 분석 결과"""
    repeated_keywords: List[Tuple[str, int]]  # 반복 키워드
    unique_features: List[str]  # 특이점/차별점
    competitor_mentions: Dict[str, int]  # 경쟁제품 언급
    comparison_insights: List[str]  # 비교 인사이트
    marketing_suggestions: List[str]  # 마케팅 포인트 제안


# 경쟁제품/브랜드 키워드 (확장 가능)
COMPETITOR_BRANDS = {
    # 스킨케어
    '메디힐', '아누아', '라운드랩', '토리든', '스킨푸드', '이니스프리',
    '클리오', '롬앤', '에뛰드', '미샤', '더페이스샵', '네이처리퍼블릭',
    '코스알엑스', 'cosrx', '넘버즈인', '아이소이', '비플레인', '달바',
    '메노킨', '가쉬', '구달', '바이오더마', '라로슈포제', '아벤느',
    # 메이크업
    '페리페라', '클리오', '투쿨포스쿨', '웨이크메이크', '힌스',
    # 선케어
    '라로슈포제', '아벤느', '스킨아쿠아', '비오레', '아넷사',
}

# 제형/특징 키워드
FEATURE_KEYWORDS = {
    # 제형
    '무스': '제형', '크림': '제형', '젤': '제형', '로션': '제형',
    '에센스': '제형', '세럼': '제형', '오일': '제형', '밤': '제형',
    '스틱': '제형', '쿠션': '제형', '파우더': '제형', '미스트': '제형',
    # 성분
    '히알루론산': '성분', '나이아신아마이드': '성분', '레티놀': '성분',
    '비타민': '성분', '세라마이드': '성분', '판테놀': '성분',
    '시카': '성분', '센텔라': '성분', 'CICA': '성분', 'cica': '성분',
    '프로폴리스': '성분', '녹차': '성분', '병풀': '성분',
    # 특징
    '저자극': '특징', '민감성': '특징', '비건': '특징', '무향': '특징',
    '무알콜': '특징', '무파라벤': '특징', '자연유래': '특징',
    '더블세럼': '특징', '앰플': '특징',
}


def extract_repeated_keywords(reviews: List[Dict], min_count: int = 5) -> List[Tuple[str, int]]:
    """리뷰에서 반복되는 키워드 추출"""
    all_text = ' '.join([r.get('content', '') for r in reviews])

    # 특징/제형/성분 키워드 카운트
    keyword_counts = Counter()

    for keyword in FEATURE_KEYWORDS:
        count = all_text.count(keyword)
        if count >= min_count:
            keyword_counts[keyword] = count

    return keyword_counts.most_common(20)


def find_competitor_mentions(reviews: List[Dict], current_brand: str = '') -> Dict[str, int]:
    """
    리뷰에서 경쟁제품 언급 찾기

    Args:
        reviews: 리뷰 리스트
        current_brand: 현재 제품 브랜드 (제외됨)

    Returns:
        경쟁 브랜드별 언급 횟수
    """
    mentions = Counter()
    current_brand_lower = current_brand.lower().strip() if current_brand else ''

    for review in reviews:
        content = review.get('content', '').lower()
        for brand in COMPETITOR_BRANDS:
            brand_lower = brand.lower()
            # 현재 브랜드는 제외
            if current_brand_lower and brand_lower in current_brand_lower:
                continue
            if current_brand_lower and current_brand_lower in brand_lower:
                continue
            if brand_lower in content:
                mentions[brand] += 1

    return dict(mentions.most_common(10))


def extract_comparison_sentences(reviews: List[Dict]) -> List[str]:
    """비교 문장 추출"""
    comparison_patterns = [
        r'.{0,20}(보다|대비|비해|비교|달리|차이|vs|VS).{0,30}',
        r'.{0,20}(이전|전에|원래|기존).{0,20}(쓰던|썼던|사용하던).{0,30}',
        r'.{0,20}(갈아탔|바꿨|교체).{0,30}',
    ]

    comparisons = []
    seen = set()

    for review in reviews:
        content = review.get('content', '')
        for pattern in comparison_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    match = ' '.join(match)
                sentence = match.strip()
                if len(sentence) > 10 and sentence not in seen:
                    seen.add(sentence)
                    comparisons.append(sentence)

    return comparisons[:20]


def extract_unique_features(reviews: List[Dict], product_name: str = '') -> List[str]:
    """
    제품의 유니크한 특징 추출 (구체적 내용 필수)
    - 제형, 질감, 디자인, 사용감 등 구체적인 차별점
    - 빈도가 낮아도 유니크한 내용이면 추출
    """
    unique_mentions = []

    # 유니크 포인트 추출 패턴 (구체적 내용 포함)
    # 각 패턴은 (regex, category, description) 형태
    unique_patterns = [
        # 제형/텍스처 관련
        (r'(제형|텍스처|질감|발림성).{0,5}(이|가|도)?.{0,30}(특이|독특|신기|처음|새로|다르)', '제형'),
        (r'(처음|첨).{0,10}(보는|써보는|사용해보는|만나는).{0,30}(제형|텍스처|질감|타입|형태)', '제형'),
        (r'(젤|크림|로션|오일|무스|밤|에센스|세럼).{0,5}(타입|형태|제형).{0,20}(특이|신기|독특|처음)', '제형'),
        (r'(이런|이렇게).{0,10}(제형|텍스처|질감|발림).{0,20}(처음|첨|없)', '제형'),

        # 디자인/패키지 관련
        (r'(디자인|패키지|패키징|용기|뚜껑|펌프).{0,30}(특이|독특|예쁘|신기|편리|처음)', '디자인'),
        (r'(특이|독특|신기).{0,10}(디자인|패키지|패키징|용기)', '디자인'),

        # 향/냄새 관련 (긍정적 유니크)
        (r'(향|냄새|향기).{0,5}(이|가)?.{0,20}(특이|독특|신기|처음|새로)', '향'),
        (r'(이런|이렇게).{0,5}(향|냄새).{0,15}(처음|첨|없)', '향'),

        # 성분/효과 관련
        (r'(성분|원료|추출물).{0,30}(특이|독특|처음|새로|희귀)', '성분'),
        (r'(효과|기능).{0,5}(가|이)?.{0,25}(특이|독특|신기|다르)', '효과'),

        # 사용감/경험 관련
        (r'(사용감|느낌|감촉).{0,5}(이|가)?.{0,25}(특이|독특|신기|처음|새로)', '사용감'),
        (r'(바르|사용하).{0,5}(면|자마자|는\s*순간).{0,30}(특이|독특|신기)', '사용감'),

        # 일반 유니크 표현 (구체적 내용 포함)
        (r'(다른|타).{0,5}(제품|브랜드).{0,5}(에|과|와|이랑)?.{0,5}(없는|다른|차별).{0,40}', '차별점'),
        (r'(처음|첨|생전).{0,5}(보|써|사용|경험|만나).{0,40}', '신규경험'),
        (r'(여기|이\s*제품|이거).{0,5}(만|에서만|밖에).{0,30}', '독점'),
        (r'(유일|유일하게).{0,40}', '유일'),
    ]

    for review in reviews:
        content = review.get('content', '')
        if not content:
            continue

        for pattern, category in unique_patterns:
            # 패턴 매치 찾기
            if re.search(pattern, content):
                # 매칭된 키워드가 있으면 리뷰 전체 내용을 저장 (자르지 않음)
                unique_mentions.append({
                    'category': category,
                    'text': content,  # 리뷰 전체 저장
                    'matched': pattern
                })
                break  # 한 리뷰에서 하나의 카테고리만 추출

    # 카테고리별로 그룹화하고 중복 제거
    category_features = {}
    seen_texts = set()

    for mention in unique_mentions:
        cat = mention['category']
        text = mention['text']

        # 유사한 텍스트 중복 제거
        text_key = text[:30]  # 앞 30자로 중복 체크
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)

        if cat not in category_features:
            category_features[cat] = []
        category_features[cat].append(text)

    # 결과 정리 (카테고리별로 최대 2개씩)
    result = []
    priority_categories = ['제형', '디자인', '사용감', '향', '성분', '차별점', '신규경험', '유일', '독점', '효과']

    for cat in priority_categories:
        if cat in category_features:
            for text in category_features[cat][:2]:  # 카테고리당 최대 2개
                result.append(f"[{cat}] {text}")

    return result[:10]  # 최대 10개


def generate_marketing_suggestions(
    repeated_keywords: List[Tuple[str, int]],
    competitor_mentions: Dict[str, int],
    unique_features: List[str],
    strengths: List[str]
) -> List[str]:
    """마케팅 포인트 제안 생성 (유니크 포인트 중심)"""
    suggestions = []

    # 1. 유니크 포인트 우선 (가장 중요!)
    if unique_features:
        suggestions.append("━━━ 🎯 유니크 포인트 (차별화 요소) ━━━")
        for feature in unique_features[:5]:
            # [카테고리] 내용 형태로 되어 있음
            suggestions.append(f"• {feature}")

    # 2. 경쟁제품 비교 기반
    if competitor_mentions:
        suggestions.append("━━━ 🆚 경쟁제품 비교 ━━━")
        for comp, count in list(competitor_mentions.items())[:3]:
            suggestions.append(f"• '{comp}' 대비 차별점 강조 ({count}회 비교 언급)")

    # 3. 핵심 강점 (빈출 키워드 기반)
    if repeated_keywords:
        suggestions.append("━━━ 💪 핵심 강점 ━━━")
        for keyword, count in repeated_keywords[:3]:
            category = FEATURE_KEYWORDS.get(keyword, '')
            if category:
                suggestions.append(f"• '{keyword}' ({category}) - {count}회 언급")

    # 4. 마케팅 활용 제안
    if strengths:
        suggestions.append("━━━ 📢 마케팅 활용 제안 ━━━")
        for strength in strengths[:3]:
            suggestions.append(f"• {strength}")

    return suggestions


def analyze_marketing_points(
    reviews: List[Dict],
    product_name: str = '',
    brand: str = ''
) -> MarketingPointResult:
    """
    마케팅 포인트 분석

    Args:
        reviews: 리뷰 리스트
        product_name: 상품명
        brand: 브랜드명

    Returns:
        MarketingPointResult
    """
    if not reviews:
        return MarketingPointResult(
            repeated_keywords=[],
            unique_features=[],
            competitor_mentions={},
            comparison_insights=[],
            marketing_suggestions=["분석할 리뷰가 없습니다."]
        )

    # 분석 수행
    repeated_keywords = extract_repeated_keywords(reviews)
    competitor_mentions = find_competitor_mentions(reviews, current_brand=brand)
    comparisons = extract_comparison_sentences(reviews)
    unique_features = extract_unique_features(reviews, product_name)

    # 기본 리뷰 분석 (장점 추출용)
    analysis = analyze_reviews(reviews)

    # 마케팅 제안 생성
    suggestions = generate_marketing_suggestions(
        repeated_keywords,
        competitor_mentions,
        unique_features,
        analysis.strengths
    )

    # 비교 인사이트 생성
    comparison_insights = []
    if competitor_mentions:
        for comp, count in list(competitor_mentions.items())[:3]:
            comparison_insights.append(f"'{comp}'와 {count}회 비교됨")

    return MarketingPointResult(
        repeated_keywords=repeated_keywords,
        unique_features=unique_features,
        competitor_mentions=competitor_mentions,
        comparison_insights=comparison_insights,
        marketing_suggestions=suggestions
    )


# 카테고리별 분석 키워드
CATEGORY_KEYWORDS = {
    '보습': ['촉촉', '보습', '수분', '건조', '당김', '촉촉해', '촉촉하'],
    '흡수': ['흡수', '스며', '빠르게', '금방', '바로'],
    '자극': ['자극', '순해', '순하', '따가', '화끈', '트러블', '예민', '민감'],
    '향': ['향', '냄새', '향기', '은은', '강해', '인공'],
    '발림성': ['발림', '부드럽', '산뜻', '가볍', '무겁', '끈적'],
    '지속력': ['지속', '오래', '유지', '밀림', '들뜸'],
    '가성비': ['가성비', '가격', '비싸', '저렴', '합리', '양'],
    '효과': ['효과', '개선', '좋아졌', '변화', '달라'],
}


def analyze_reviews(reviews: List[Dict]) -> ReviewAnalysisResult:
    """
    리뷰 리스트 분석 (문맥 기반)
    """
    if not reviews:
        return ReviewAnalysisResult(
            total_count=0, positive_count=0, negative_count=0, neutral_count=0,
            positive_ratio=0, strengths=[], weaknesses=[],
            top_positive_keywords=[], top_negative_keywords=[],
            category_scores={}, summary="분석할 리뷰가 없습니다."
        )

    positive_count = 0
    negative_count = 0
    neutral_count = 0

    all_positive_keywords = []
    all_negative_keywords = []
    category_sentiment = {cat: {'pos': 0, 'neg': 0} for cat in CATEGORY_KEYWORDS}

    for review in reviews:
        content = review.get('content', '')
        rating = review.get('rating', 0)

        # 문맥 기반 감성 분석
        sentiment, pos_found, neg_found, score = analyze_sentiment_with_context(content)

        # 평점이 있으면 참고 (하지만 내용 분석 우선)
        if rating >= 4 and sentiment != 'negative':
            sentiment = 'positive'
        elif rating <= 2 and rating > 0 and sentiment != 'positive':
            sentiment = 'negative'

        if sentiment == 'positive':
            positive_count += 1
        elif sentiment == 'negative':
            negative_count += 1
        else:
            neutral_count += 1

        all_positive_keywords.extend(pos_found)
        all_negative_keywords.extend(neg_found)

        # 카테고리별 분석
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in content:
                    if sentiment == 'positive':
                        category_sentiment[cat]['pos'] += 1
                    elif sentiment == 'negative':
                        category_sentiment[cat]['neg'] += 1

    # 통계
    total = len(reviews)
    positive_ratio = positive_count / total if total > 0 else 0

    top_positive = Counter(all_positive_keywords).most_common(10)
    top_negative = Counter(all_negative_keywords).most_common(10)

    # 카테고리별 긍정률
    category_scores = {}
    for cat in CATEGORY_KEYWORDS:
        pos = category_sentiment[cat]['pos']
        neg = category_sentiment[cat]['neg']
        total_cat = pos + neg
        if total_cat > 0:
            category_scores[cat] = round(pos / total_cat * 100, 1)

    # 장단점 추출
    strengths = _extract_strengths(top_positive, category_scores)
    weaknesses = _extract_weaknesses(top_negative, category_scores)

    # 요약
    summary = _generate_summary(total, positive_count, negative_count, strengths, weaknesses, positive_ratio)

    return ReviewAnalysisResult(
        total_count=total,
        positive_count=positive_count,
        negative_count=negative_count,
        neutral_count=neutral_count,
        positive_ratio=round(positive_ratio * 100, 1),
        strengths=strengths,
        weaknesses=weaknesses,
        top_positive_keywords=top_positive,
        top_negative_keywords=top_negative,
        category_scores=category_scores,
        summary=summary
    )


def _extract_strengths(top_positive: List[Tuple[str, int]], category_scores: Dict) -> List[str]:
    """장점 문장 생성"""
    strengths = []
    top_keywords = [kw for kw, _ in top_positive[:7]]

    keyword_groups = {
        '보습': (['촉촉', '보습', '수분', '촉촉해'], "보습력이 좋고 촉촉함이 오래 유지됨"),
        '흡수': (['흡수', '빠른흡수', '스며', '흡수빠름'], "흡수가 빠르고 끈적임이 없음"),
        '순함': (['순해', '순하', '자극없음', '무자극', '끈적없음'], "자극 없이 순하게 사용 가능"),
        '발림성': (['발림', '부드러', '산뜻'], "발림성이 부드럽고 산뜻함"),
        '가성비': (['가성비', '저렴', '합리'], "가격 대비 만족도가 높음"),
        '재구매': (['재구매', '재구', '또사', '추천', '강추'], "재구매 의향이 높은 제품"),
    }

    for group_name, (keywords, description) in keyword_groups.items():
        if any(kw in top_keywords for kw in keywords):
            strengths.append(description)

    return strengths[:5]


def _extract_weaknesses(top_negative: List[Tuple[str, int]], category_scores: Dict) -> List[str]:
    """단점 문장 생성"""
    weaknesses = []
    top_keywords = [kw for kw, _ in top_negative[:7]]

    keyword_groups = {
        '끈적임': (['끈적', '끈적거', '무거'], "끈적임이 있어 불편하다는 의견"),
        '자극': (['트러블', '뾰루지', '자극', '따가'], "일부 사용자에게 자극이나 트러블 발생"),
        '향': (['향강', '인공향', '냄새'], "향이 강하거나 인공적이라는 평가"),
        '가격': (['비싸', '비쌈'], "가격이 비싸다는 의견"),
        '효과부족': (['효과없', '별로', '모르겠'], "효과를 체감하기 어렵다는 평가"),
    }

    for group_name, (keywords, description) in keyword_groups.items():
        if any(kw in top_keywords for kw in keywords):
            weaknesses.append(description)

    return weaknesses[:5]


def _generate_summary(total, positive, negative, strengths, weaknesses, positive_ratio) -> str:
    """요약문 생성"""
    parts = []

    ratio_pct = positive_ratio * 100

    if ratio_pct >= 80:
        parts.append(f"총 {total}개 리뷰 중 {ratio_pct:.0f}%가 긍정적으로, 매우 호평받는 제품입니다.")
    elif ratio_pct >= 60:
        parts.append(f"총 {total}개 리뷰 중 {ratio_pct:.0f}%가 긍정적으로, 대체로 좋은 평가를 받고 있습니다.")
    elif ratio_pct >= 40:
        parts.append(f"총 {total}개 리뷰 중 긍정/부정 비율이 비슷하여 호불호가 갈리는 제품입니다.")
    else:
        parts.append(f"총 {total}개 리뷰 중 부정적 의견이 많아 주의가 필요한 제품입니다.")

    if strengths:
        parts.append(f"주요 장점: {strengths[0]}")
    if weaknesses:
        parts.append(f"주의사항: {weaknesses[0]}")

    return " ".join(parts)


def quick_analyze(reviews: List[Dict]) -> Dict:
    """간편 분석"""
    result = analyze_reviews(reviews)
    return {
        'total': result.total_count,
        'positive_ratio': result.positive_ratio,
        'positive_count': result.positive_count,
        'negative_count': result.negative_count,
        'strengths': result.strengths,
        'weaknesses': result.weaknesses,
        'top_positive': result.top_positive_keywords[:5],
        'top_negative': result.top_negative_keywords[:5],
        'category_scores': result.category_scores,
        'summary': result.summary
    }


def quick_marketing_analysis(reviews: List[Dict], product_name: str = '', brand: str = '') -> Dict:
    """간편 마케팅 포인트 분석"""
    result = analyze_marketing_points(reviews, product_name, brand)
    return {
        'repeated_keywords': result.repeated_keywords[:10],
        'unique_features': result.unique_features,
        'competitor_mentions': result.competitor_mentions,
        'comparison_insights': result.comparison_insights,
        'marketing_suggestions': result.marketing_suggestions
    }


# 테스트
if __name__ == "__main__":
    sample_reviews = [
        {'content': '자극이 없고 순해서 좋아요! 재구매 의사 있습니다.', 'rating': 5},
        {'content': '끈적임 없이 촉촉하게 흡수돼요', 'rating': 5},
        {'content': '트러블 없이 잘 사용하고 있어요', 'rating': 4},
        {'content': '향이 너무 강해서 별로예요. 자극도 있고...', 'rating': 2},
        {'content': '메디힐보다 더 촉촉한 것 같아요', 'rating': 5},
        {'content': '가성비 좋고 순해서 민감피부도 사용 가능해요', 'rating': 4},
        {'content': '히알루론산 성분이라 그런지 보습이 좋아요', 'rating': 5},
    ]

    print("=== 문맥 기반 리뷰 분석 테스트 ===\n")

    result = quick_analyze(sample_reviews)
    print(f"총 리뷰: {result['total']}개")
    print(f"긍정 비율: {result['positive_ratio']}%")
    print(f"\n장점:")
    for s in result['strengths']:
        print(f"  - {s}")
    print(f"\n단점:")
    for w in result['weaknesses']:
        print(f"  - {w}")

    print("\n=== 마케팅 포인트 분석 테스트 ===\n")

    marketing = quick_marketing_analysis(sample_reviews)
    print("경쟁제품 언급:", marketing['competitor_mentions'])
    print("반복 키워드:", marketing['repeated_keywords'][:5])
    print("\n마케팅 제안:")
    for s in marketing['marketing_suggestions']:
        print(f"  - {s}")
