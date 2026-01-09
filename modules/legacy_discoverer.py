"""
과거 특이 제품 자동 발굴 모듈
네이버 검색 API를 활용하여 단종된 화장품 관련 글을 찾고,
브랜드/제품명을 자동 추출합니다.
"""
import re
import time
import requests
from typing import List, Dict, Any, Optional, Callable
from html import unescape

from config import (
    NAVER_CLIENT_ID,
    NAVER_CLIENT_SECRET,
    DISCOVERY_MAX_PRODUCTS,
    DISCOVERY_SEARCH_DELAY,
    DISCOVERY_QUERIES,
    KNOWN_COSMETIC_BRANDS,
    BRAND_ALIASES,
    PRODUCT_TYPE_KEYWORDS,
    COSMETIC_CATEGORY_KEYWORDS,
)


class LegacyDiscoverer:
    """과거 히트상품 자동 발굴 클래스"""

    # 네이버 검색 API 엔드포인트
    API_ENDPOINTS = {
        "blog": "https://openapi.naver.com/v1/search/blog",
        "cafe": "https://openapi.naver.com/v1/search/cafearticle",
        "kin": "https://openapi.naver.com/v1/search/kin",
    }

    # 단종 관련 키워드 (제품 컨텍스트 검증용)
    DISCONTINUATION_KEYWORDS = [
        "단종", "품절", "안나와", "안팔아", "안파나요", "안나오나요",
        "어디서 사", "구할 수", "재출시", "다시 나", "그리워", "아쉬워",
        "예전에", "옛날", "추억", "지금은 없", "더이상",
    ]

    def __init__(self, db_manager=None):
        """
        Args:
            db_manager: DatabaseManager 인스턴스 (중복 체크용)
        """
        self.db = db_manager
        self.session = requests.Session()
        self._setup_headers()

        # 브랜드명 정규화 맵 (config에서 로드)
        self.brand_aliases = BRAND_ALIASES

    def _setup_headers(self):
        """네이버 API 인증 헤더 설정"""
        self.session.headers.update({
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        })

    def discover(
        self,
        sources: List[str] = None,
        max_products: int = None,
        min_mentions: int = 5,
        callback: Callable[[str, int, int], None] = None,
    ) -> List[Dict[str, Any]]:
        """
        과거 제품 자동 발굴 (반복 언급된 제품만 수집)
        target_count개 제품을 찾을 때까지 검색 확장

        Args:
            sources: 검색 소스 리스트 ["blog", "cafe", "kin"]
            max_products: 최대 발굴 개수 (기본값: config.DISCOVERY_MAX_PRODUCTS)
            min_mentions: 최소 언급 횟수 (이 횟수 이상 언급된 제품만 수집)
            callback: 진행 상황 콜백 함수 (message, current, total)

        Returns:
            발굴된 제품 리스트
        """
        if sources is None:
            sources = ["blog", "cafe", "kin"]
        if max_products is None:
            max_products = DISCOVERY_MAX_PRODUCTS

        # 제품별 언급 횟수 카운트
        product_mentions = {}  # key -> {product_data, count, sources}

        # 기존 DB에서 이미 발굴된 제품 가져오기
        existing_keys = set()
        if self.db:
            existing = self.db.get_discovered_products()
            for p in existing:
                existing_keys.add(self._normalize_product_key(p['brand'], p['name']))

        # 검색 확장 설정
        max_pages = 5  # 각 쿼리당 최대 페이지
        max_api_calls = 500  # 안전장치: 최대 API 호출 횟수
        api_call_count = 0

        # 진행 상황 추정 (max_products * 20 API 호출 예상)
        estimated_total = max_products * 20

        def get_qualified_count():
            """min_mentions 이상 언급된 제품 수 계산"""
            return sum(1 for data in product_mentions.values() if data['count'] >= min_mentions)

        # 1단계: 기본 쿼리로 검색 (페이지네이션 포함)
        for page in range(1, max_pages + 1):
            start = (page - 1) * 20 + 1  # 네이버 API start 파라미터

            for query in DISCOVERY_QUERIES:
                for source in sources:
                    # 목표 달성 시 중단
                    if get_qualified_count() >= max_products:
                        break

                    # API 호출 제한 체크
                    if api_call_count >= max_api_calls:
                        break

                    api_call_count += 1
                    if callback:
                        qualified = get_qualified_count()
                        callback(
                            f"검색 중: {query[:15]}... (p{page}, {qualified}/{max_products}개 발굴)",
                            min(api_call_count, estimated_total),
                            estimated_total
                        )

                    # 네이버 API 검색 (페이지네이션)
                    search_results = self._search_naver(query, source, start=start)
                    if not search_results:
                        continue

                    # 검색 결과에서 제품 추출
                    self._process_search_results(
                        search_results, product_mentions, existing_keys, source, query
                    )

                    # API 호출 제한 방지
                    time.sleep(DISCOVERY_SEARCH_DELAY)

                if get_qualified_count() >= max_products or api_call_count >= max_api_calls:
                    break

            if get_qualified_count() >= max_products or api_call_count >= max_api_calls:
                break

        # 2단계: 부족하면 브랜드 + 카테고리 조합 검색
        if get_qualified_count() < max_products and api_call_count < max_api_calls:
            # estimated_total 재계산 (추가 검색 포함)
            estimated_total = max(estimated_total, api_call_count + 150)
            if callback:
                callback(f"추가 검색 중... ({get_qualified_count()}/{max_products}개)", api_call_count, estimated_total)

            # 주요 브랜드 + 카테고리 조합으로 검색
            extra_brands = KNOWN_COSMETIC_BRANDS[:30]  # 상위 30개 브랜드
            main_categories = COSMETIC_CATEGORY_KEYWORDS[:5]  # 주요 카테고리 5개

            for brand in extra_brands:
                if get_qualified_count() >= max_products or api_call_count >= max_api_calls:
                    break

                for category in main_categories:
                    if get_qualified_count() >= max_products or api_call_count >= max_api_calls:
                        break

                    # 브랜드 + 카테고리 + 단종 조합
                    query = f"{brand} {category} 단종"

                    for source in sources:
                        if get_qualified_count() >= max_products or api_call_count >= max_api_calls:
                            break

                        api_call_count += 1
                        if callback:
                            qualified = get_qualified_count()
                            callback(
                                f"검색: {query[:20]}... ({qualified}/{max_products}개)",
                                min(api_call_count, estimated_total),
                                estimated_total
                            )

                        search_results = self._search_naver(query, source)
                        if search_results:
                            self._process_search_results(
                                search_results, product_mentions, existing_keys, source, query
                            )

                        time.sleep(DISCOVERY_SEARCH_DELAY)

        # 3단계: min_mentions 이상 언급된 제품만 필터링
        if callback:
            callback(f"필터링 중... (최소 {min_mentions}회 언급)", api_call_count, api_call_count)

        discovered = []
        # 언급 횟수 내림차순 정렬
        sorted_products = sorted(
            product_mentions.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )

        for product_key, data in sorted_products:
            if data['count'] >= min_mentions:
                product = data['product']
                product['discovery_source'] = ', '.join(data['sources'])
                product['discovery_keyword'] = ', '.join(list(data['keywords'])[:3])
                product['source_url'] = data['urls'][0] if data['urls'] else ''
                product['mention_count'] = data['count']
                discovered.append(product)

                if len(discovered) >= max_products:
                    break

        if callback:
            callback(
                f"발굴 완료: {len(discovered)}개 제품 ({api_call_count}회 API 호출)",
                api_call_count, api_call_count
            )

        return discovered

    def _process_search_results(
        self,
        search_results: List[Dict],
        product_mentions: Dict,
        existing_keys: set,
        source: str,
        query: str
    ):
        """검색 결과 처리 및 제품 카운트 업데이트"""
        for result in search_results:
            products = self._extract_products(result)
            for product in products:
                product_key = self._normalize_product_key(
                    product['brand'], product['name']
                )

                # 이미 DB에 있는 제품 제외
                if product_key in existing_keys:
                    continue

                # 카운트 업데이트
                if product_key not in product_mentions:
                    product_mentions[product_key] = {
                        'product': product,
                        'count': 0,
                        'sources': set(),
                        'keywords': set(),
                        'urls': []
                    }

                product_mentions[product_key]['count'] += 1
                product_mentions[product_key]['sources'].add(source)
                product_mentions[product_key]['keywords'].add(query)
                if result.get('link'):
                    product_mentions[product_key]['urls'].append(result.get('link'))

    def _search_naver(self, query: str, source: str, start: int = 1) -> List[Dict]:
        """
        네이버 검색 API 호출

        Args:
            query: 검색어
            source: 검색 소스 (blog, cafe, kin)
            start: 검색 시작 위치 (1, 21, 41, ...)

        Returns:
            검색 결과 리스트
        """
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            return []

        endpoint = self.API_ENDPOINTS.get(source)
        if not endpoint:
            return []

        try:
            response = self.session.get(
                endpoint,
                params={
                    "query": query,
                    "display": 20,  # 한 번에 20개
                    "start": start,  # 페이지네이션
                    "sort": "date",  # 최신순
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])

        except requests.RequestException as e:
            print(f"네이버 API 오류: {e}")
            return []

    def _extract_products(self, search_result: Dict) -> List[Dict[str, Any]]:
        """
        검색 결과에서 브랜드/제품명 추출

        Args:
            search_result: 네이버 검색 API 응답 항목

        Returns:
            추출된 제품 정보 리스트
        """
        products = []

        # HTML 태그 제거 및 언이스케이프
        title = self._clean_html(search_result.get("title", ""))
        description = self._clean_html(search_result.get("description", ""))
        text = f"{title} {description}"

        # 단종 관련 컨텍스트 확인
        if not self._has_discontinuation_context(text):
            return products

        # 브랜드 + 제품명 추출 시도
        extracted = self._extract_brand_and_product(text)
        if extracted:
            products.append(extracted)

        return products

    def _extract_brand_and_product(self, text: str) -> Optional[Dict[str, Any]]:
        """
        텍스트에서 브랜드와 제품명 추출 (단순화된 버전)

        Args:
            text: 분석할 텍스트

        Returns:
            {"brand": str, "name": str, "context": str} 또는 None
        """
        # 방법 1: 알려진 브랜드명 찾기
        found_brand = None
        for brand in KNOWN_COSMETIC_BRANDS:
            if brand in text:
                found_brand = brand
                break

        # 브랜드 별칭으로도 검색
        if not found_brand:
            for standard_brand, aliases in self.brand_aliases.items():
                for alias in aliases:
                    if alias.lower() in text.lower():
                        found_brand = standard_brand
                        break
                if found_brand:
                    break

        if not found_brand:
            return None

        # 방법 2: 브랜드 주변에서 제품명 추출
        # 브랜드 뒤 2~6단어를 제품명으로 추출
        pattern = rf'{re.escape(found_brand)}\s+([가-힣a-zA-Z0-9\s]{{2,30}})'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            product_name = match.group(1).strip()
            # 너무 짧거나 의미없는 단어 제외
            if len(product_name) >= 2:
                return {
                    "brand": found_brand,
                    "name": self._clean_product_name(product_name),
                    "context": text[:200],
                }

        # 방법 3: 제품 유형 키워드가 있으면 그 앞부분을 제품명으로
        for product_type in PRODUCT_TYPE_KEYWORDS:
            if product_type in text:
                # "XX 크림", "OO 세럼" 등의 패턴
                pattern = rf'([가-힣a-zA-Z0-9\s]{{2,20}}){re.escape(product_type)}'
                match = re.search(pattern, text)
                if match:
                    product_name = f"{match.group(1).strip()} {product_type}"
                    return {
                        "brand": found_brand,
                        "name": self._clean_product_name(product_name),
                        "context": text[:200],
                    }

        # 방법 4: 브랜드만이라도 반환
        return {
            "brand": found_brand,
            "name": "(제품명 미상)",
            "context": text[:200],
        }

    def _contains_product_type(self, text: str) -> bool:
        """제품 유형 키워드 포함 여부 확인"""
        return any(keyword in text for keyword in PRODUCT_TYPE_KEYWORDS)

    def _has_discontinuation_context(self, text: str) -> bool:
        """단종 관련 컨텍스트 포함 여부 확인"""
        return any(keyword in text for keyword in self.DISCONTINUATION_KEYWORDS)

    def _clean_html(self, text: str) -> str:
        """HTML 태그 제거 및 언이스케이프"""
        # HTML 태그 제거
        clean = re.sub(r'<[^>]+>', '', text)
        # HTML 엔티티 언이스케이프
        clean = unescape(clean)
        return clean.strip()

    def _clean_product_name(self, name: str) -> str:
        """제품명 정리"""
        # 불필요한 공백 정리
        name = re.sub(r'\s+', ' ', name).strip()
        # 특수문자 제거 (일부만)
        name = re.sub(r'[^\w\s가-힣]', '', name)
        return name.strip()

    def _normalize_product_key(self, brand: str, name: str) -> str:
        """
        제품 키 정규화 (중복 체크용)
        - 공백, 특수문자, 숫자 모두 제거
        - 한글과 영문 소문자만 남김
        예: "그린티 씨드 세럼" → "그린티씨드세럼"
        """
        # 한글, 영문 소문자만 남기고 모두 제거
        brand_norm = re.sub(r'[^가-힣a-z]', '', brand.lower())
        name_norm = re.sub(r'[^가-힣a-z]', '', name.lower())
        return f"{brand_norm}_{name_norm}"

    def _is_duplicate_in_db(self, brand: str, name: str) -> bool:
        """DB에서 중복 확인"""
        if not self.db:
            return False

        existing = self.db.get_discovered_product_by_name(brand, name)
        return existing is not None

    def validate_api_key(self) -> bool:
        """네이버 API 키 유효성 확인"""
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            return False

        try:
            response = self.session.get(
                self.API_ENDPOINTS["blog"],
                params={"query": "테스트", "display": 1},
                timeout=5,
            )
            return response.status_code == 200
        except:
            return False


def test_discovery():
    """테스트 함수"""
    discoverer = LegacyDiscoverer()

    # API 키 확인
    if not discoverer.validate_api_key():
        print("네이버 API 키가 설정되지 않았습니다.")
        print("config.py 또는 .env 파일에 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET를 설정하세요.")
        return

    def progress_callback(message, current, total):
        print(f"[{current}/{total}] {message}")

    # 발굴 실행
    results = discoverer.discover(
        sources=["blog"],
        max_products=3,
        callback=progress_callback,
    )

    print(f"\n발굴된 제품: {len(results)}개")
    for i, product in enumerate(results, 1):
        print(f"\n{i}. {product['brand']} - {product['name']}")
        print(f"   출처: {product['discovery_source']}")
        print(f"   키워드: {product['discovery_keyword']}")
        print(f"   컨텍스트: {product.get('context', '')[:100]}...")


if __name__ == "__main__":
    test_discovery()
