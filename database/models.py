"""
데이터베이스 테이블 스키마 정의
"""

SCHEMA_SQL = """
-- 경쟁사 제품 테이블
CREATE TABLE IF NOT EXISTS competitor_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,

    -- 10가지 대분류 (JSON 형식으로 저장)
    design_packaging TEXT,
    user_experience TEXT,
    formulation TEXT,
    color TEXT,
    scent TEXT,
    ingredients TEXT,
    technology TEXT,
    usage_environment TEXT,
    marketing TEXT,
    sustainability TEXT,

    -- 기본 정보
    price INTEGER,
    launch_date TEXT,
    image_url TEXT,

    -- 데이터 소스 및 분석
    product_page_url TEXT,
    strengths TEXT,
    weaknesses TEXT,
    review_summary TEXT,

    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 과거 특이 제품 테이블
CREATE TABLE IF NOT EXISTS legacy_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,

    launch_year INTEGER,
    discontinue_year INTEGER,

    unique_features TEXT,
    failure_reason TEXT,
    market_condition TEXT,
    revival_potential INTEGER DEFAULT 3,
    current_trend_fit TEXT,

    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 신제품 제안 테이블
CREATE TABLE IF NOT EXISTS product_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,

    concept_description TEXT,
    key_features TEXT,

    reference_competitor_ids TEXT,
    reference_legacy_ids TEXT,

    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 올리브영 베스트 상품 테이블 (크롤링 데이터)
CREATE TABLE IF NOT EXISTS oliveyoung_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT UNIQUE,
    brand TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,

    price INTEGER,
    original_price INTEGER,
    product_url TEXT,
    image_url TEXT,

    best_rank INTEGER,
    review_count INTEGER,
    is_new BOOLEAN DEFAULT 0,

    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_rank INTEGER,
    rank_change INTEGER DEFAULT 0,

    added_to_competitor BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 크롤링 히스토리 테이블
CREATE TABLE IF NOT EXISTS crawl_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    products_count INTEGER,
    new_products_count INTEGER,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 리뷰 분석 결과 테이블
CREATE TABLE IF NOT EXISTS review_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT UNIQUE NOT NULL,
    brand TEXT,
    name TEXT,

    -- 분석 통계
    total_reviews INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    positive_ratio REAL DEFAULT 0,

    -- 분석 결과 (JSON)
    strengths TEXT,
    weaknesses TEXT,
    top_positive_keywords TEXT,
    top_negative_keywords TEXT,
    category_scores TEXT,
    summary TEXT,

    -- 마케팅 분석 (JSON)
    repeated_keywords TEXT,
    unique_features TEXT,
    competitor_mentions TEXT,
    comparison_insights TEXT,
    marketing_suggestions TEXT,

    -- 리뷰 샘플 (JSON)
    review_samples TEXT,

    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def create_tables(connection):
    """테이블 생성"""
    connection.executescript(SCHEMA_SQL)
    connection.commit()
