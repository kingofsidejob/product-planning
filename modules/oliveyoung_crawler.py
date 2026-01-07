"""
올리브영 베스트 상품 크롤러
"""
import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict, Optional
from datetime import datetime


class OliveyoungCrawler:
    """올리브영 베스트 상품 크롤러"""

    BASE_URL = "https://www.oliveyoung.co.kr"
    BEST_URL = "https://www.oliveyoung.co.kr/store/main/getBestList.do"

    # 올리브영 카테고리 코드 (2026년 기준)
    CATEGORIES = {
        # 스킨케어
        "스킨케어": "10000010001",
        "스킨/토너": "10000010001010001",
        "에센스/세럼/앰플": "10000010001010002",
        "크림": "10000010001010003",
        "로션": "10000010001010004",
        "미스트/오일": "10000010001010005",
        # 마스크팩
        "마스크팩": "10000010009",
        "시트팩": "10000010009010001",
        "패드": "10000010009010002",
        "페이셜팩": "10000010009010003",
        "코팩": "10000010009010004",
        "패치": "10000010009010005",
        # 클렌징
        "클렌징": "10000010010",
        "클렌징폼/젤": "10000010010010001",
        "오일/밤": "10000010010010002",
        "워터/밀크": "10000010010010003",
        "필링&스크럽": "10000010010010004",
        # 선케어
        "선케어": "10000010011",
        "선크림": "10000010011010001",
        "선스틱": "10000010011010002",
        "선쿠션": "10000010011010003",
        # 메이크업
        "메이크업": "10000010002",
        "립메이크업": "10000010002010001",
        "베이스메이크업": "10000010002010002",
        "아이메이크업": "10000010002010003",
        "메이크업툴": "10000010002010004",
        # 더모코스메틱
        "더모코스메틱": "10000010012",
        # 맨즈케어
        "맨즈케어": "10000010003",
        # 헤어케어
        "헤어케어": "10000010004",
        "샴푸/린스": "10000010004010001",
        "트리트먼트/팩": "10000010004010002",
        "헤어에센스": "10000010004010004",
        "스타일링": "10000010004010007",
        # 바디케어
        "바디케어": "10000010005",
        "바디로션/크림": "10000010005010001",
        "핸드케어": "10000010005010003",
        "풋케어": "10000010005010004",
        # 향수/디퓨저
        "향수/디퓨저": "10000010006",
        "향수": "10000010006010001",
        # 네일
        "네일": "10000010008",
        # 건강식품
        "건강식품": "10000020001",
        # 푸드
        "푸드": "10000020002",
        # 구강용품
        "구강용품": "10000030003",
        # 위생용품
        "위생용품": "10000030004",
    }

    # 주요 카테고리 그룹
    CATEGORY_GROUPS = {
        "스킨케어 전체": ["스킨케어", "스킨/토너", "에센스/세럼/앰플", "크림", "로션", "미스트/오일"],
        "마스크팩 전체": ["마스크팩", "시트팩", "패드", "페이셜팩", "코팩", "패치"],
        "클렌징 전체": ["클렌징", "클렌징폼/젤", "오일/밤", "워터/밀크", "필링&스크럽"],
        "선케어 전체": ["선케어", "선크림", "선스틱", "선쿠션"],
        "메이크업 전체": ["메이크업", "립메이크업", "베이스메이크업", "아이메이크업", "메이크업툴"],
        "헤어케어 전체": ["헤어케어", "샴푸/린스", "트리트먼트/팩", "헤어에센스", "스타일링"],
        "바디케어 전체": ["바디케어", "바디로션/크림", "핸드케어", "풋케어"],
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.oliveyoung.co.kr/',
        })

    def get_best_products(self, category_name: str, limit: int = 100) -> List[Dict]:
        """
        카테고리별 베스트 상품 가져오기

        Args:
            category_name: 카테고리 이름 (예: "스킨케어")
            limit: 가져올 상품 수 (최대 100)

        Returns:
            상품 정보 리스트
        """
        if category_name not in self.CATEGORIES:
            raise ValueError(f"지원하지 않는 카테고리: {category_name}")

        category_code = self.CATEGORIES[category_name]
        products = []
        page = 1

        while len(products) < limit:
            try:
                page_products = self._fetch_page(category_code, page)
                if not page_products:
                    break

                products.extend(page_products)
                page += 1
                time.sleep(0.5)  # 서버 부하 방지

            except Exception as e:
                print(f"페이지 {page} 크롤링 실패: {e}")
                break

        return products[:limit]

    def _fetch_page(self, category_code: str, page: int = 1) -> List[Dict]:
        """페이지별 상품 가져오기"""
        params = {
            'dispCatNo': category_code,
            'fltDispCatNo': '',
            'pageIdx': page,
            'rowsPerPage': 24,
        }

        try:
            response = self.session.get(self.BEST_URL, params=params, timeout=10)
            response.raise_for_status()

            return self._parse_products(response.text)

        except requests.RequestException as e:
            print(f"요청 실패: {e}")
            return []

    def _parse_products(self, html: str) -> List[Dict]:
        """HTML에서 상품 정보 파싱"""
        soup = BeautifulSoup(html, 'lxml')
        products = []

        # 상품 리스트 찾기
        product_items = soup.select('li.flag_wrap, li.prd_info, div.prd_info')

        if not product_items:
            # 다른 셀렉터 시도
            product_items = soup.select('ul.cate_prd_list li, div.prd_list li')

        for item in product_items:
            try:
                product = self._parse_product_item(item)
                if product:
                    products.append(product)
            except Exception as e:
                continue

        return products

    def _parse_product_item(self, item) -> Optional[Dict]:
        """개별 상품 아이템 파싱"""
        # 브랜드명
        brand_elem = item.select_one('.tx_brand, .brand, a.tx_brand')
        brand = brand_elem.get_text(strip=True) if brand_elem else ""

        # 상품명
        name_elem = item.select_one('.tx_name, .prd_name, a.prd_name')
        name = name_elem.get_text(strip=True) if name_elem else ""

        if not name:
            return None

        # 가격
        price = 0
        price_elem = item.select_one('.tx_cur, .price, span.tx_num')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r'[\d,]+', price_text)
            if price_match:
                price = int(price_match.group().replace(',', ''))

        # 원가 (할인 전)
        original_price = price
        org_price_elem = item.select_one('.tx_org, .org_price')
        if org_price_elem:
            org_text = org_price_elem.get_text(strip=True)
            org_match = re.search(r'[\d,]+', org_text)
            if org_match:
                original_price = int(org_match.group().replace(',', ''))

        # 상품 URL
        link_elem = item.select_one('a[href*="goods"]')
        product_url = ""
        product_code = ""
        if link_elem:
            href = link_elem.get('href', '')
            if href:
                product_url = href if href.startswith('http') else self.BASE_URL + href
                # 상품 코드 추출
                code_match = re.search(r'goodsNo=(\w+)', href)
                if code_match:
                    product_code = code_match.group(1)

        # 이미지 URL
        img_elem = item.select_one('img')
        image_url = ""
        if img_elem:
            image_url = img_elem.get('src', '') or img_elem.get('data-src', '')

        # 순위
        rank = 0
        rank_elem = item.select_one('.num, .rank, .tx_num')
        if rank_elem:
            rank_text = rank_elem.get_text(strip=True)
            rank_match = re.search(r'\d+', rank_text)
            if rank_match:
                rank = int(rank_match.group())

        # 리뷰 수
        review_count = 0
        review_elem = item.select_one('.tx_review, .review_count')
        if review_elem:
            review_text = review_elem.get_text(strip=True)
            review_match = re.search(r'[\d,]+', review_text)
            if review_match:
                review_count = int(review_match.group().replace(',', ''))

        # 신제품 여부 (뱃지로 판단)
        is_new = False
        badges = item.select('.icon_flag, .badge, .tag')
        for badge in badges:
            badge_text = badge.get_text(strip=True).lower()
            if 'new' in badge_text or '신상' in badge_text:
                is_new = True
                break

        return {
            'brand': brand,
            'name': name,
            'price': price,
            'original_price': original_price,
            'product_url': product_url,
            'product_code': product_code,
            'image_url': image_url,
            'rank': rank,
            'review_count': review_count,
            'is_new': is_new,
            'crawled_at': datetime.now().isoformat(),
        }

    def get_all_categories_best(self, limit_per_category: int = 100,
                                 categories: List[str] = None) -> Dict[str, List[Dict]]:
        """
        모든 카테고리의 베스트 상품 가져오기

        Args:
            limit_per_category: 카테고리당 가져올 상품 수
            categories: 가져올 카테고리 리스트 (None이면 전체)

        Returns:
            {카테고리명: [상품리스트]} 형태의 딕셔너리
        """
        target_categories = categories or list(self.CATEGORIES.keys())
        results = {}

        for category in target_categories:
            print(f"크롤링 중: {category}...")
            try:
                products = self.get_best_products(category, limit_per_category)
                results[category] = products
                print(f"  - {len(products)}개 상품 수집 완료")
                time.sleep(1)  # 카테고리 간 딜레이
            except Exception as e:
                print(f"  - 실패: {e}")
                results[category] = []

        return results

    def find_new_products(self, products: List[Dict]) -> List[Dict]:
        """신제품만 필터링"""
        return [p for p in products if p.get('is_new', False)]

    @staticmethod
    def get_available_categories() -> List[str]:
        """사용 가능한 카테고리 목록 반환"""
        return list(OliveyoungCrawler.CATEGORIES.keys())

    @staticmethod
    def get_category_groups() -> dict:
        """카테고리 그룹 반환"""
        return OliveyoungCrawler.CATEGORY_GROUPS

    @staticmethod
    def get_main_categories() -> List[str]:
        """주요 대분류 카테고리만 반환"""
        return [
            "스킨케어", "마스크팩", "클렌징", "선케어",
            "메이크업", "더모코스메틱", "맨즈케어",
            "헤어케어", "바디케어", "향수/디퓨저", "네일"
        ]


# 테스트용
if __name__ == "__main__":
    crawler = OliveyoungCrawler()

    print("사용 가능한 카테고리:", crawler.get_available_categories())

    # 스킨케어 카테고리 테스트
    products = crawler.get_best_products("스킨케어", limit=10)
    print(f"\n스킨케어 베스트 {len(products)}개:")
    for p in products[:5]:
        print(f"  - {p['brand']} / {p['name']} / {p['price']:,}원")
