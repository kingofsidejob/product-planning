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

-- 신제품 아이디어 테이블
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

-- 경쟁사 베스트 상품 테이블 (크롤링 데이터)
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

-- 발굴된 과거 히트상품 테이블
CREATE TABLE IF NOT EXISTS discovered_hit_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 기본 정보
    brand TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT,

    -- 발굴 정보
    discovery_source TEXT,
    discovery_keyword TEXT,
    original_year INTEGER,
    source_url TEXT,

    -- 단종 판별
    discontinuation_status TEXT DEFAULT 'pending',
    oliveyoung_checked_at TIMESTAMP,
    brand_mall_checked_at TIMESTAMP,

    -- 리뷰 분석
    review_count INTEGER DEFAULT 0,
    review_samples TEXT,
    positive_ratio REAL,
    strengths TEXT,
    weaknesses TEXT,

    -- 단종 이유 및 마케팅
    inferred_discontinuation_reasons TEXT,
    marketing_points TEXT,
    revival_potential INTEGER DEFAULT 3,

    -- 메타
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(brand, name)
);

-- 발굴 히스토리 테이블
CREATE TABLE IF NOT EXISTS discovery_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discovery_source TEXT NOT NULL,
    products_found INTEGER DEFAULT 0,
    discontinued_count INTEGER DEFAULT 0,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def create_tables(connection):
    """테이블 생성"""
    connection.executescript(SCHEMA_SQL)
    connection.commit()

def run_migrations(connection):
    """
    데이터베이스 마이그레이션 실행
    migrations 폴더의 모든 SQL 파일을 순서대로 실행
    """
    import os
    
    # migrations 디렉토리 경로
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    
    # migrations 폴더가 없으면 생성
    if not os.path.exists(migrations_dir):
        os.makedirs(migrations_dir)
        return
    
    # 모든 .sql 파일 가져오기 (알파벳 순서로 정렬)
    migration_files = sorted([
        f for f in os.listdir(migrations_dir)
        if f.endswith('.sql')
    ])
    
    if not migration_files:
        return
    
    # 각 마이그레이션 파일 실행
    for migration_file in migration_files:
        migration_path = os.path.join(migrations_dir, migration_file)
        with open(migration_path, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
            connection.executescript(migration_sql)
    
    connection.commit()
