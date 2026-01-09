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

# 통합 카테고리 데이터 import (Single Source of Truth)
from config import get_category_codes


class OliveyoungBrowserCrawler:
    """Playwright 기반 올리브영 크롤러"""

    BASE_URL = "https://www.oliveyoung.co.kr"
    CATEGORY_URL = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"


    # 소분류 카테고리 코드 매핑
    CATEGORIES = get_category_codes()

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

        # 페이지 접속 (타임아웃 60초, domcontentloaded로 변경)
        await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(3000)  # 동적 로딩 대기

        # 봇 감지 페이지 대기
        try:
            await self.page.wait_for_selector(".prd_info", timeout=20000)
        except:
            # 봇 감지 페이지일 수 있음, 추가 대기
            await self.page.wait_for_timeout(5000)
            await self.page.wait_for_selector(".prd_info", timeout=20000)

        # 페이지당 48개 상품 표시 설정
        await self.set_items_per_page(48)

        all_products = []
        seen_codes = set()  # 중복 체크용
        page_num = 1

        while len(all_products) < limit:
            # 현재 페이지 상품 추출
            products = await self._extract_products_from_page()

            if not products:
                break

            # 중복 제거 및 순위 설정
            for product in products:
                product_code = product.get('product_code')
                if product_code and product_code not in seen_codes:
                    seen_codes.add(product_code)
                    product['rank'] = len(all_products) + 1
                    product['category'] = category
                    all_products.append(product)

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
        """다음 페이지로 이동 (URL 파라미터 방식)"""
        try:
            current_url = self.page.url

            # URL에 pageIdx 파라미터 추가/수정
            if 'pageIdx=' in current_url:
                import re
                new_url = re.sub(r'pageIdx=\d+', f'pageIdx={page_num}', current_url)
            else:
                separator = '&' if '?' in current_url else '?'
                new_url = f"{current_url}{separator}pageIdx={page_num}"

            await self.page.goto(new_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(3000)

            # 상품이 로드되었는지 확인
            try:
                await self.page.wait_for_selector(".prd_info", timeout=20000)
                return True
            except:
                return False

        except Exception as e:
            print(f"페이지 이동 실패: {e}")
            return False

    async def set_items_per_page(self, count: int = 48):
        """페이지당 상품 수 설정 (24, 36, 48)"""
        try:
            # VIEW 옵션 클릭 (다양한 셀렉터 시도)
            selectors = [
                f'.view_num a:has-text("{count}")',
                f'a:has-text("VIEW"):has-text("{count}")',
                f'[class*="view"] a:has-text("{count}")',
                f'a[href*="pageSize={count}"]',
            ]

            for selector in selectors:
                view_btn = await self.page.query_selector(selector)
                if view_btn:
                    await view_btn.click()
                    await self.page.wait_for_load_state("networkidle")
                    await self.page.wait_for_timeout(1500)
                    return True

            # JavaScript로 직접 클릭 시도
            js_code = f"""
            () => {{
                const links = document.querySelectorAll('a');
                for (const link of links) {{
                    if (link.textContent.trim() === '{count}') {{
                        link.click();
                        return true;
                    }}
                }}
                return false;
            }}
            """
            result = await self.page.evaluate(js_code)
            if result:
                await self.page.wait_for_load_state("networkidle")
                await self.page.wait_for_timeout(1500)
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
