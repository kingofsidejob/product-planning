"""
배치 데이터 수집 스크립트
4개 대분류(스킨케어, 마스크팩, 클렌징, 선케어)의 소분류 카테고리를 500개씩 수집
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def log(msg):
    """출력 함수 (flush 포함)"""
    print(msg, flush=True)

from modules.oliveyoung_browser_crawler import run_crawler_sync
from database.db_manager import DatabaseManager
from config import DB_PATH

# 수집할 카테고리 목록
CATEGORIES_TO_COLLECT = {
    "스킨케어": [
        "스킨/토너", "에센스/세럼/앰플", "크림", "아이크림",
        "로션", "올인원", "미스트/픽서", "페이스오일", "스킨케어세트"
    ],
    "마스크팩": [
        "시트팩", "패드", "페이셜팩", "코팩", "패치"
    ],
    "클렌징": [
        "클렌징폼/젤", "클렌징오일", "클렌징밤", "클렌징워터",
        "클렌징밀크", "필링&스크럽", "클렌징티슈/패드", "립&아이리무버"
    ],
    "선케어": [
        "선크림", "선스틱", "선쿠션", "선스프레이/선패치", "태닝", "애프터선"
    ]
}

LIMIT = 500  # 각 카테고리당 수집 개수

def main():
    db = DatabaseManager(DB_PATH)

    total_categories = sum(len(cats) for cats in CATEGORIES_TO_COLLECT.values())
    current = 0

    results_summary = []

    for main_cat, sub_cats in CATEGORIES_TO_COLLECT.items():
        log(f"\n{'='*60}")
        log(f"[Category] {main_cat} ({len(sub_cats)} subcategories)")
        log('='*60)

        for sub_cat in sub_cats:
            current += 1
            log(f"\n[{current}/{total_categories}] Collecting: {main_cat} > {sub_cat}...")

            try:
                # 크롤러 실행
                products = run_crawler_sync(
                    category=sub_cat,
                    limit=LIMIT,
                    headless=True,
                    progress_callback=lambda c, t: print(f"  Progress: {c}/{t}", end='\r', flush=True)
                )

                # DB 저장
                new_count = 0
                update_count = 0

                for product in products:
                    result = db.upsert_oliveyoung_product(product)
                    if result == 'new':
                        new_count += 1
                    elif result == 'updated':
                        update_count += 1

                # 수집 기록 저장
                db.save_crawl_history(sub_cat, len(products), new_count)

                result_msg = f"OK {sub_cat}: {len(products)} collected (new: {new_count}, updated: {update_count})"
                log(f"\n  {result_msg}")
                results_summary.append(result_msg)

            except Exception as e:
                error_msg = f"FAIL {sub_cat}: {str(e)[:50]}"
                log(f"\n  {error_msg}")
                results_summary.append(error_msg)

    # 최종 요약
    log(f"\n\n{'='*60}")
    log("SUMMARY")
    log('='*60)
    for msg in results_summary:
        log(msg)

    # DB 통계
    stats = db.get_oliveyoung_stats()
    log(f"\nTotal products in DB: {stats.get('total', 0):,}")

if __name__ == "__main__":
    main()
