-- 성능 개선을 위한 인덱스 추가
-- 실행 일자: 2026-01-09
-- Phase 1: 긴급 성능 개선

-- 1. oliveyoung_products 테이블 인덱스
-- 카테고리별 베스트 순위 조회 최적화 (가장 자주 사용되는 쿼리)
CREATE INDEX IF NOT EXISTS idx_oliveyoung_category_rank
ON oliveyoung_products(category, best_rank);

-- 신규 진입 상품 조회 최적화
CREATE INDEX IF NOT EXISTS idx_oliveyoung_is_new
ON oliveyoung_products(is_new)
WHERE is_new = 1;

-- product_code는 이미 UNIQUE 제약으로 인덱스가 있음

-- 2. review_analysis 테이블 인덱스
-- 분석 날짜별 정렬 최적화
CREATE INDEX IF NOT EXISTS idx_review_analysis_analyzed_at
ON review_analysis(analyzed_at DESC);

-- product_code는 이미 UNIQUE 제약으로 인덱스가 있음

-- 3. discovered_hit_products 테이블 인덱스
-- 단종 상태별 조회 최적화
CREATE INDEX IF NOT EXISTS idx_discovered_status
ON discovered_hit_products(discontinuation_status);

-- 부활 가능성별 정렬 최적화
CREATE INDEX IF NOT EXISTS idx_discovered_revival
ON discovered_hit_products(revival_potential DESC);

-- 4. legacy_products 테이블 인덱스
-- 부활 가능성별 조회 최적화 (get_high_potential_legacy_products에서 사용)
CREATE INDEX IF NOT EXISTS idx_legacy_revival
ON legacy_products(revival_potential DESC);

-- 5. crawl_history 테이블 인덱스
-- 카테고리별 히스토리 조회 최적화
CREATE INDEX IF NOT EXISTS idx_crawl_history_category
ON crawl_history(category, crawled_at DESC);

-- 인덱스 효과 확인 쿼리 예시:
-- EXPLAIN QUERY PLAN SELECT * FROM oliveyoung_products WHERE category = '스킨/토너' ORDER BY best_rank;
-- EXPLAIN QUERY PLAN SELECT * FROM oliveyoung_products WHERE is_new = 1;
-- EXPLAIN QUERY PLAN SELECT * FROM review_analysis ORDER BY analyzed_at DESC LIMIT 100;
