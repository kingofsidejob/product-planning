"""
올리브영 리뷰 크롤러 (Python/Playwright 기반)
- 상품 ID(goodsNo)로 리뷰 전체 수집
- 무한스크롤 + 더보기 버튼 자동 처리
- 기존 Node.js 크롤러 로직 참조
"""
import asyncio
import sys
import csv
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path

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
    from playwright.async_api import async_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# 설정값
CONFIG = {
    'MAX_SCROLL_ITERATIONS': 9999,    # 최대 스크롤 횟수
    'SCROLL_DELAY': 100,              # 스크롤 후 대기 (ms)
    'SCROLL_STEP': 1200,              # 한 번에 스크롤할 픽셀
    'NO_SCROLL_LIMIT': 30,            # 스크롤 위치 변화 없으면 종료
    'MAX_NO_NEW_REVIEWS': 50,         # 연속 새 리뷰 없으면 종료
    'PAGE_TIMEOUT': 60000,            # 페이지 로딩 타임아웃 (ms)
    'HEADLESS': True,                 # 헤드리스 모드
}


class OliveyoungReviewCrawler:
    """올리브영 리뷰 크롤러"""

    def __init__(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright가 설치되지 않았습니다.")
        self.browser = None
        self.page = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self, headless: bool = True):
        """브라우저 시작"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=['--lang=ko-KR']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='ko-KR'
        )
        self.page = await self.context.new_page()

    async def close(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def crawl_reviews(
        self,
        product_id: str,
        max_reviews: int = 0,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        상품 리뷰 크롤링

        Args:
            product_id: 상품 ID (goodsNo, A로 시작)
            max_reviews: 최대 수집 개수 (0이면 전체)
            progress_callback: 진행 콜백 (current, total, message)

        Returns:
            {'product_info': {...}, 'reviews': [...], 'count': int}
        """
        if not self.page:
            raise RuntimeError("브라우저가 시작되지 않았습니다.")

        url = f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={product_id}"

        # 페이지 접속
        if progress_callback:
            progress_callback(0, 100, f"페이지 접속 중: {product_id}")

        await self.page.goto(url, wait_until='domcontentloaded', timeout=CONFIG['PAGE_TIMEOUT'])
        await self.page.wait_for_timeout(3000)

        # 봇 감지 대기
        try:
            await self.page.wait_for_selector('.GoodsDetailInfo_title__Vl_IP', timeout=15000)
        except:
            await self.page.wait_for_timeout(5000)

        # 상품 정보 추출
        product_info = await self._extract_product_info(product_id)
        if progress_callback:
            progress_callback(5, 100, f"상품: {product_info['brand']} - {product_info['name'][:30]}...")

        total_reviews = product_info.get('total_reviews', 0)
        target_count = max_reviews if max_reviews > 0 else total_reviews

        # 리뷰 섹션으로 이동
        await self._navigate_to_review_section()
        if progress_callback:
            progress_callback(10, 100, "리뷰 섹션 진입 완료")

        # 리뷰 수집
        reviews = await self._scroll_and_collect_reviews(
            target_count,
            progress_callback
        )

        return {
            'product_info': product_info,
            'reviews': reviews,
            'count': len(reviews)
        }

    async def _extract_product_info(self, product_id: str) -> Dict:
        """상품 정보 추출"""
        info = {
            'product_id': product_id,
            'brand': '',
            'name': '',
            'total_reviews': 0
        }

        try:
            # 브랜드
            brand_el = self.page.locator('.TopUtils_btn-brand__tvEdp').first
            if await brand_el.count() > 0:
                info['brand'] = (await brand_el.text_content()).strip()

            # 상품명
            name_el = self.page.locator('.GoodsDetailInfo_title__Vl_IP').first
            if await name_el.count() > 0:
                info['name'] = (await name_el.text_content()).strip()

            # 총 리뷰 수
            review_count_el = self.page.locator('.GoodsDetailTabs_review-count__Vi4U_').first
            if await review_count_el.count() > 0:
                text = await review_count_el.text_content()
                match = re.search(r'\d+', text.replace(',', ''))
                if match:
                    info['total_reviews'] = int(match.group())

        except Exception as e:
            print(f"상품 정보 추출 오류: {e}")

        return info

    async def _navigate_to_review_section(self):
        """리뷰 섹션으로 이동"""
        try:
            # 리뷰 탭 클릭
            review_tab = self.page.locator('.GoodsDetailTabs_tab-item-label__tyN8W').filter(has_text='리뷰')
            if await review_tab.count() > 0:
                await review_tab.first.click()
                await self.page.wait_for_timeout(2000)

            # 리뷰 섹션으로 스크롤
            await self.page.evaluate("""
                () => {
                    const reviewSection = document.querySelector('[class*="review"]');
                    if (reviewSection) {
                        reviewSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            """)
            await self.page.wait_for_timeout(3000)

        except Exception as e:
            print(f"리뷰 섹션 이동 오류: {e}")

    async def _scroll_and_collect_reviews(
        self,
        target_count: int,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """무한스크롤로 리뷰 수집"""
        collected_reviews = []
        previous_keys = set()
        no_new_count = 0
        no_scroll_count = 0

        for i in range(CONFIG['MAX_SCROLL_ITERATIONS']):
            # 현재 DOM의 리뷰 추출
            current_reviews = await self._extract_reviews_from_page()

            # 새 리뷰 필터링 (중복 제거)
            new_count = 0
            current_keys = set()

            for review in current_reviews:
                key = f"{review['nickname']}_{review['content'][:50]}"
                current_keys.add(key)

                if key not in previous_keys:
                    collected_reviews.append(review)
                    new_count += 1

            previous_keys = current_keys

            # 진행 상황
            if progress_callback and i % 10 == 0:
                progress = min(10 + int(80 * len(collected_reviews) / max(target_count, 1)), 90)
                progress_callback(progress, 100, f"리뷰 수집 중: {len(collected_reviews)}/{target_count}개")

            # 종료 조건 체크
            if new_count == 0:
                no_new_count += 1
                if no_new_count >= CONFIG['MAX_NO_NEW_REVIEWS']:
                    break
            else:
                no_new_count = 0

            if target_count > 0 and len(collected_reviews) >= target_count:
                break

            # 스크롤
            current_scroll = await self.page.evaluate('window.scrollY')
            await self.page.evaluate(f'window.scrollBy(0, {CONFIG["SCROLL_STEP"]})')
            await self.page.wait_for_timeout(CONFIG['SCROLL_DELAY'])
            new_scroll = await self.page.evaluate('window.scrollY')

            # 스크롤 위치 변화 없으면 종료
            if abs(new_scroll - current_scroll) < 10:
                no_scroll_count += 1
                if no_scroll_count >= CONFIG['NO_SCROLL_LIMIT']:
                    break
            else:
                no_scroll_count = 0

        # 최종 중복 제거 (내용 기준)
        unique_reviews = []
        seen_contents = set()
        for review in collected_reviews:
            content_key = review['content']
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                unique_reviews.append(review)

        if progress_callback:
            progress_callback(95, 100, f"수집 완료: {len(unique_reviews)}개 리뷰")

        return unique_reviews

    async def _extract_reviews_from_page(self) -> List[Dict]:
        """현재 페이지에서 리뷰 추출 (Shadow DOM 지원)"""
        reviews = []

        try:
            # Shadow DOM 내부까지 탐색하는 JavaScript로 리뷰 추출
            js_code = """
            () => {
                // Shadow DOM 내부에서 텍스트 추출하는 헬퍼 함수
                function getTextFromShadow(el, maxDepth = 3, depth = 0) {
                    if (!el || depth > maxDepth) return '';

                    // Shadow Root가 있으면 그 안에서 텍스트 추출
                    if (el.shadowRoot) {
                        return getTextFromShadow(el.shadowRoot, maxDepth, depth + 1);
                    }

                    // 일반 텍스트 노드
                    let text = '';
                    if (el.nodeType === Node.TEXT_NODE) {
                        text = el.textContent || '';
                    } else if (el.childNodes) {
                        for (const child of el.childNodes) {
                            text += getTextFromShadow(child, maxDepth, depth + 1);
                        }
                    }

                    // 엘리먼트의 직접 텍스트도 포함
                    if (!text && el.textContent) {
                        text = el.textContent;
                    }

                    return text.trim();
                }

                function findReviewsInShadow(root, depth = 0) {
                    if (depth > 8) return [];

                    const reviews = [];
                    const elements = root.querySelectorAll('*');

                    for (const el of elements) {
                        // Shadow DOM이 있으면 재귀 탐색
                        if (el.shadowRoot) {
                            const nested = findReviewsInShadow(el.shadowRoot, depth + 1);
                            reviews.push(...nested);
                        }

                        // oy-review-review-item 찾기
                        if (el.tagName === 'OY-REVIEW-REVIEW-ITEM' && el.shadowRoot) {
                            const itemShadow = el.shadowRoot;

                            // 리뷰 내용 추출 (여러 방법 시도)
                            let content = '';

                            // 방법 1: oy-review-review-content 커스텀 엘리먼트에서 추출
                            const contentEl = itemShadow.querySelector('oy-review-review-content');
                            if (contentEl) {
                                content = getTextFromShadow(contentEl);
                            }

                            // 방법 2: .review-content 클래스에서 추출
                            if (!content) {
                                const reviewContentEl = itemShadow.querySelector('.review-content, .content, [class*="content"]');
                                if (reviewContentEl) {
                                    content = getTextFromShadow(reviewContentEl);
                                }
                            }

                            // 방법 3: P 태그에서 긴 텍스트 추출
                            if (!content) {
                                const paragraphs = itemShadow.querySelectorAll('p');
                                for (const p of paragraphs) {
                                    const pText = p.textContent || '';
                                    if (pText.length > 30) {
                                        content = pText.trim();
                                        break;
                                    }
                                }
                            }

                            // 방법 4: div나 span에서 긴 텍스트 추출
                            if (!content) {
                                const allText = itemShadow.querySelectorAll('div, span');
                                for (const txt of allText) {
                                    const t = txt.textContent || '';
                                    if (t.length > 50 && !t.includes('옵션') && !t.includes('구매')) {
                                        content = t.trim();
                                        break;
                                    }
                                }
                            }

                            if (!content || content.length < 10) continue;

                            // 닉네임
                            let nickname = '';
                            const nameEl = itemShadow.querySelector('.name, [class*="name"], [class*="user"]');
                            if (nameEl) nickname = nameEl.textContent.trim();

                            // 날짜
                            let date = '';
                            const dateEl = itemShadow.querySelector('.date, [class*="date"]');
                            if (dateEl) date = dateEl.textContent.trim();

                            // 옵션
                            let option = '';
                            const optionEl = itemShadow.querySelector('.goods-option, [class*="option"]');
                            if (optionEl) {
                                option = optionEl.textContent.replace(/^\\[옵션\\]\\s*/, '').trim();
                            }

                            reviews.push({
                                nickname: nickname || '익명',
                                date: date || '',
                                option: option || '옵션없음',
                                rating: 0,
                                content: content
                            });
                        }
                    }

                    return reviews;
                }

                // oy-review-review-in-product에서 시작
                const oyReview = document.querySelector('oy-review-review-in-product');
                if (oyReview && oyReview.shadowRoot) {
                    return findReviewsInShadow(oyReview.shadowRoot);
                }

                // 대체 방법: 일반 DOM에서 리뷰 찾기
                const fallbackReviews = [];
                const reviewItems = document.querySelectorAll('[class*="review-item"], [class*="ReviewItem"]');
                for (const item of reviewItems) {
                    const content = item.textContent || '';
                    if (content.length > 50) {
                        fallbackReviews.push({
                            nickname: '익명',
                            date: '',
                            option: '옵션없음',
                            rating: 0,
                            content: content.substring(0, 1000).trim()
                        });
                    }
                }

                return fallbackReviews;
            }
            """

            reviews = await self.page.evaluate(js_code)

            # 줄바꿈 및 lit 템플릿 마커 정리
            for review in reviews:
                content = review['content']
                # lit-html 템플릿 마커 제거 (예: ?lit$337127225$)
                content = re.sub(r'\?lit\$\d+\$', '', content)
                # 연속 공백 정리
                content = re.sub(r'\s+', ' ', content)
                # 줄바꿈 정리
                content = re.sub(r'\n+', '\n', content.strip())
                review['content'] = content

        except Exception as e:
            print(f"리뷰 추출 오류: {e}")

        return reviews


def run_review_crawler_sync(
    product_id: str,
    max_reviews: int = 0,
    headless: bool = True,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    동기식 리뷰 크롤러 실행

    Args:
        product_id: 상품 ID (goodsNo)
        max_reviews: 최대 수집 개수 (0=전체)
        headless: 헤드리스 모드
        progress_callback: 진행 콜백

    Returns:
        {'product_info': {...}, 'reviews': [...], 'count': int}
    """
    async def _run():
        crawler = OliveyoungReviewCrawler()
        await crawler.start(headless=headless)
        try:
            return await crawler.crawl_reviews(
                product_id=product_id,
                max_reviews=max_reviews,
                progress_callback=progress_callback
            )
        finally:
            await crawler.close()

    return asyncio.run(_run())


def save_reviews_to_csv(reviews: List[Dict], filepath: str):
    """리뷰를 CSV로 저장"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['nickname', 'date', 'option', 'rating', 'content'])
        writer.writeheader()
        writer.writerows(reviews)

    return filepath


# 테스트
if __name__ == "__main__":
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright를 설치해주세요")
    else:
        def progress(current, total, message):
            print(f"[{current}/{total}] {message}")

        result = run_review_crawler_sync(
            product_id="A000000243499",  # 온그리디언츠 로션
            max_reviews=50,
            headless=False,
            progress_callback=progress
        )

        print(f"\n수집 완료: {result['count']}개 리뷰")
        for r in result['reviews'][:5]:
            print(f"  - {r['nickname']}: {r['content'][:50]}...")
