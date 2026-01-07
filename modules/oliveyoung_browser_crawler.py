"""
올리브영 베스트 상품 브라우저 크롤러 (Playwright 기반)
- 동적 로딩 페이지 지원
- goodsNo 기반 신규 상품 감지
"""
import asyncio
import sys
import re
from typing import List, Dict, Optional, Callable
from datetime import datetime

# Windows asyncio 이벤트 루프 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# nest_asyncio로 중첩 이벤트 루프 허용 (Streamlit 호환)
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class OliveyoungBrowserCrawler:
    """Playwright 기반 올리브영 크롤러"""

    BASE_URL = "https://www.oliveyoung.co.kr"
    CATEGORY_URL = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"

    # 소분류 카테고리 코드 매핑
    # URL 예시: https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo={카테고리코드}
    CATEGORIES = {
        # 스킨케어
        "스킨/토너": "100000100010013",
        "에센스/세럼/앰플": "100000100010014",
        "크림": "1000001000100150001",
        "아이크림": "1000001000100150002",
        "로션": "1000001000100160001",
        "올인원": "1000001000100160002",
        "미스트/픽서": "1000001000100100001",
        "페이스오일": "1000001000100100002",
        "스킨케어세트": "100000100010017",
        # 마스크팩
        "시트팩": "1000001000900010001",
        "패드": "1000001000900040001",
        "페이셜팩": "100000100090002",
        "코팩": "100000100090005",
        "패치": "100000100090006",
        # 클렌징
        "클렌징폼/젤": "100000100100001",
        "클렌징오일": "1000001001000040001",
        "클렌징밤": "1000001001000040002",
        "클렌징워터": "1000001001000050003",
        "클렌징밀크": "1000001001000050001",
        "필링&스크럽": "100000100100007",
        "클렌징티슈/패드": "100000100100008",
        "립&아이리무버": "100000100100006",
        # 선케어
        "선크림": "1000001001100060001",
        "선스틱": "1000001001100030001",
        "선쿠션": "100000100110004",
        "선스프레이/선패치": "100000100110005",
        "태닝": "1000001001100020001",
        "애프터선": "1000001001100020002",
        # 메이크업 - 립
        "립틴트": "1000001000200060003",
        "립스틱": "1000001000200060004",
        "립라이너": "1000001000200060006",
        "립밤": "1000001000200060001",
        "립글로스": "1000001000200060002",
        # 메이크업 - 베이스
        "쿠션": "1000001000200010009",
        "파운데이션": "1000001000200010002",
        "블러셔": "1000001000200010006",
        "파우더/팩트": "1000001000200010004",
        "컨실러": "1000001000200010005",
        "프라이머/베이스": "1000001000200010003",
        "쉐이딩": "1000001000200010007",
        "하이라이터": "1000001000200010008",
        "메이크업픽서": "1000001000200010010",
        "BB/CC": "1000001000200010001",
        # 메이크업 - 아이
        "아이섀도우": "1000001000200070003",
        "아이라이너": "1000001000200070002",
        "마스카라": "1000001000200070001",
        "아이브로우": "1000001000200070004",
        # 뷰티소품
        "브러시": "1000001000600010007",
        "퍼프": "1000001000600010005",
        "스펀지": "1000001000600010006",
        "화장솜": "1000001000600060001",
        "뷰러": "1000001000600070001",
        "속눈썹/쌍꺼풀": "1000001000600070002",
        # 더모 코스메틱
        "더모로션/크림": "1000001000800130001",
        "더모에센스/세럼": "1000001000800130005",
        "더모스킨/토너": "1000001000800130002",
        "더모아이크림": "1000001000800130004",
        # 맨즈케어
        "맨즈올인원": "1000001000700070006",
        "맨즈토너/로션/크림": "1000001000700070013",
        "면도기/면도날": "1000001000700100001",
        "애프터쉐이브": "1000001000700100005",
        # 헤어케어
        "샴푸": "1000001000400080001",
        "린스/컨디셔너": "1000001000400080002",
        "헤어팩/마스크": "1000001000400070004",
        "헤어트리트먼트": "1000001000400070005",
        "헤어오일/세럼": "1000001000400130002",
        "염색/새치염색": "1000001000400100007",
        "고데기": "1000001000400040008",
        "드라이기": "1000001000400040009",
        # 바디케어
        "바디로션": "1000001000300140001",
        "바디크림": "1000001000300140002",
        "바디오일": "1000001000300140003",
        "바디워시": "1000001000300050001",
        "바디스크럽": "1000001000300050002",
        "입욕제": "1000001000300050003",
        "립케어": "100000100030008",
        "핸드크림": "1000001000300160002",
        "핸드워시": "1000001000300160001",
        "바디미스트": "100000100030015",
        "제모크림": "1000001000300190001",
        "데오드란트": "100000100030012",
        # 향수/디퓨저
        "여성향수": "1000001000500030001",
        "남성향수": "1000001000500040001",
        "유니섹스향수": "1000001000500110001",
        "미니/고체향수": "100000100050010",
        "홈프래그런스": "100000100050012",
        # 네일
        "일반네일": "100000100120007",
        "젤네일": "100000100120010",
        "네일팁/스티커": "100000100120008",
        "네일케어": "100000100120004",
        # 건강식품
        "비타민": "100000200010015",
        "유산균": "100000200010024",
        "영양제": "100000200010025",
        "슬리밍/이너뷰티": "100000200010023",
        # 푸드
        "식단관리": "100000200020020",
        "과자/초콜릿": "100000200020023",
        "생수/음료/커피": "100000200020022",
        # 구강용품
        "칫솔": "100000200030015",
        "치약": "100000200030016",
        "애프터구강케어": "100000200030017",
        # 여성/위생용품
        "생리/위생용품": "100000200040001",
        "Y존케어": "100000200040006",
    }

    def __init__(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright가 설치되지 않았습니다. "
                "pip install playwright && playwright install chromium"
            )
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self, headless: bool = True):
        """브라우저 시작"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.page = await self.context.new_page()

    async def close(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def get_best_products(
        self,
        category: str = "전체",
        limit: int = 100,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Dict]:
        """
        카테고리별 베스트 상품 수집

        Args:
            category: 카테고리명
            limit: 수집할 상품 수 (최대)
            progress_callback: 진행률 콜백 함수 (current, total)

        Returns:
            상품 정보 리스트
        """
        if not self.page:
            raise RuntimeError("브라우저가 시작되지 않았습니다. start()를 먼저 호출하세요.")

        # 카테고리 URL 구성
        category_code = self.CATEGORIES.get(category, "")
        if not category_code:
            raise ValueError(f"알 수 없는 카테고리: {category}. 사용 가능한 카테고리: {list(self.CATEGORIES.keys())}")
        url = f"{self.CATEGORY_URL}?dispCatNo={category_code}"

        # 페이지 접속
        await self.page.goto(url, wait_until="networkidle", timeout=30000)
        await self.page.wait_for_timeout(2000)  # 동적 로딩 대기

        # 봇 감지 페이지 대기
        try:
            await self.page.wait_for_selector(".prd_info", timeout=15000)
        except:
            # 봇 감지 페이지일 수 있음, 추가 대기
            await self.page.wait_for_timeout(5000)
            await self.page.wait_for_selector(".prd_info", timeout=15000)

        all_products = []
        page_num = 1

        while len(all_products) < limit:
            # 현재 페이지 상품 추출
            products = await self._extract_products_from_page()

            if not products:
                break

            # 순위 설정 (이전 페이지 상품 수 + 현재 인덱스)
            for i, product in enumerate(products):
                product['rank'] = len(all_products) + i + 1
                product['category'] = category

            all_products.extend(products)

            if progress_callback:
                progress_callback(len(all_products), limit)

            # 목표 수량 도달 시 종료
            if len(all_products) >= limit:
                break

            # 다음 페이지 이동
            page_num += 1
            has_next = await self._go_to_next_page(page_num)
            if not has_next:
                break

            await self.page.wait_for_timeout(1500)  # 페이지 로딩 대기

        return all_products[:limit]

    async def _extract_products_from_page(self) -> List[Dict]:
        """현재 페이지에서 상품 정보 추출"""

        js_code = """
        () => {
            const products = [];
            const items = document.querySelectorAll('.prd_info');

            items.forEach((item) => {
                const link = item.querySelector('a[href*="goodsNo"]');
                const brandEl = item.querySelector('.tx_brand');
                const nameEl = item.querySelector('.tx_name');
                const priceEl = item.querySelector('.tx_cur .tx_num');
                const orgPriceEl = item.querySelector('.tx_org .tx_num');
                const reviewEl = item.querySelector('.tx_review');
                const imgEl = item.closest('.prd_info')?.previousElementSibling?.querySelector('img');

                if (link) {
                    const href = link.getAttribute('href');
                    const goodsNoMatch = href.match(/goodsNo=([A-Z0-9]+)/);
                    const goodsNo = goodsNoMatch ? goodsNoMatch[1] : null;

                    // 리뷰 수 추출
                    let reviewCount = 0;
                    if (reviewEl) {
                        const reviewMatch = reviewEl.textContent.match(/[\\d,]+/);
                        if (reviewMatch) {
                            reviewCount = parseInt(reviewMatch[0].replace(/,/g, ''));
                        }
                    }

                    products.push({
                        product_code: goodsNo,
                        brand: brandEl ? brandEl.textContent.trim() : '',
                        name: nameEl ? nameEl.textContent.trim() : '',
                        price: priceEl ? parseInt(priceEl.textContent.replace(/[^0-9]/g, '')) || 0 : 0,
                        original_price: orgPriceEl ? parseInt(orgPriceEl.textContent.replace(/[^0-9]/g, '')) || 0 : 0,
                        review_count: reviewCount,
                        image_url: imgEl ? imgEl.src : '',
                        product_url: href.startsWith('http') ? href : 'https://www.oliveyoung.co.kr' + href
                    });
                }
            });

            return products;
        }
        """

        products = await self.page.evaluate(js_code)
        return products

    async def _go_to_next_page(self, page_num: int) -> bool:
        """다음 페이지로 이동"""
        try:
            # 페이지 버튼 클릭
            page_btn = await self.page.query_selector(f'.pageing a:has-text("{page_num}")')
            if page_btn:
                await page_btn.click()
                await self.page.wait_for_load_state("networkidle")
                return True

            # 다음 페이지 버튼 (>>) 시도
            next_btn = await self.page.query_selector('.pageing .next')
            if next_btn:
                await next_btn.click()
                await self.page.wait_for_load_state("networkidle")
                return True

            return False
        except Exception as e:
            print(f"페이지 이동 실패: {e}")
            return False

    async def set_items_per_page(self, count: int = 48):
        """페이지당 상품 수 설정 (24, 36, 48)"""
        try:
            # VIEW 옵션 클릭
            view_btn = await self.page.query_selector(f'.view_num a:has-text("{count}")')
            if view_btn:
                await view_btn.click()
                await self.page.wait_for_load_state("networkidle")
                await self.page.wait_for_timeout(1000)
                return True
        except Exception as e:
            print(f"보기 설정 실패: {e}")
        return False

    @staticmethod
    def get_available_categories() -> List[str]:
        """사용 가능한 카테고리 목록"""
        return list(OliveyoungBrowserCrawler.CATEGORIES.keys())


def run_crawler_sync(
    category: str = "전체",
    limit: int = 100,
    headless: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[Dict]:
    """
    동기식 크롤러 실행 (Streamlit 등에서 사용)

    Args:
        category: 카테고리명
        limit: 수집할 상품 수
        headless: 헤드리스 모드 여부
        progress_callback: 진행률 콜백

    Returns:
        수집된 상품 리스트
    """
    async def _run():
        async with OliveyoungBrowserCrawler() as crawler:
            await crawler.start(headless=headless)
            return await crawler.get_best_products(
                category=category,
                limit=limit,
                progress_callback=progress_callback
            )

    return asyncio.run(_run())


# 테스트
if __name__ == "__main__":
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright를 설치해주세요: pip install playwright && playwright install chromium")
    else:
        def progress(current, total):
            print(f"진행률: {current}/{total}")

        products = run_crawler_sync(
            category="스킨케어",
            limit=10,
            headless=False,
            progress_callback=progress
        )

        print(f"\n수집된 상품 {len(products)}개:")
        for p in products:
            print(f"  {p['rank']}. {p['brand']} - {p['name']} ({p['product_code']})")
