"""
데이터베이스 매니저 - SQLite CRUD 작업
"""
import sqlite3
import json
import os
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

from .models import create_tables, run_migrations


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()

    def _ensure_db_directory(self):
        """데이터베이스 디렉토리 확인 및 생성"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def _init_database(self):
        """데이터베이스 초기화"""
        with self.get_connection() as conn:
            create_tables(conn)
            run_migrations(conn)

    def _parse_json_fields(
        self,
        row: Dict[str, Any],
        list_fields: List[str] = None,
        dict_fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        공통 JSON 파싱 헬퍼 함수
        
        Args:
            row: 파싱할 row 딕셔너리
            list_fields: 리스트로 파싱할 필드 목록
            dict_fields: 딕셔너리로 파싱할 필드 목록
            
        Returns:
            파싱된 row 딕셔너리
        """
        if list_fields:
            for field in list_fields:
                if row.get(field):
                    try:
                        row[field] = json.loads(row[field])
                    except json.JSONDecodeError:
                        row[field] = []
        
        if dict_fields:
            for field in dict_fields:
                if row.get(field):
                    try:
                        row[field] = json.loads(row[field])
                    except json.JSONDecodeError:
                        row[field] = {}
        
        return row

    @contextmanager
    def get_connection(self):
        """컨텍스트 매니저로 데이터베이스 연결 관리"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # ==================== 경쟁사 제품 CRUD ====================

    def add_competitor_product(self, data: Dict[str, Any]) -> int:
        """경쟁사 제품 추가"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO competitor_products (
                    brand, name, category,
                    design_packaging, user_experience, formulation,
                    color, scent, ingredients, technology,
                    usage_environment, marketing, sustainability,
                    price, launch_date, image_url,
                    product_page_url, strengths, weaknesses, review_summary,
                    notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('brand'),
                data.get('name'),
                data.get('category'),
                json.dumps(data.get('design_packaging', {}), ensure_ascii=False),
                json.dumps(data.get('user_experience', {}), ensure_ascii=False),
                json.dumps(data.get('formulation', {}), ensure_ascii=False),
                json.dumps(data.get('color', {}), ensure_ascii=False),
                json.dumps(data.get('scent', {}), ensure_ascii=False),
                json.dumps(data.get('ingredients', {}), ensure_ascii=False),
                json.dumps(data.get('technology', {}), ensure_ascii=False),
                json.dumps(data.get('usage_environment', {}), ensure_ascii=False),
                json.dumps(data.get('marketing', {}), ensure_ascii=False),
                json.dumps(data.get('sustainability', {}), ensure_ascii=False),
                data.get('price'),
                data.get('launch_date'),
                data.get('image_url'),
                data.get('product_page_url'),
                data.get('strengths'),
                data.get('weaknesses'),
                data.get('review_summary'),
                data.get('notes')
            ))
            return cursor.lastrowid

    def get_competitor_products(self) -> List[Dict[str, Any]]:
        """모든 경쟁사 제품 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM competitor_products ORDER BY created_at DESC"
            )
            return [self._parse_competitor_row(dict(row)) for row in cursor.fetchall()]

    def get_competitor_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """특정 경쟁사 제품 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM competitor_products WHERE id = ?", (product_id,)
            )
            row = cursor.fetchone()
            return self._parse_competitor_row(dict(row)) if row else None

    def update_competitor_product(self, product_id: int, data: Dict[str, Any]) -> bool:
        """경쟁사 제품 수정"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE competitor_products SET
                    brand = ?, name = ?, category = ?,
                    design_packaging = ?, user_experience = ?, formulation = ?,
                    color = ?, scent = ?, ingredients = ?, technology = ?,
                    usage_environment = ?, marketing = ?, sustainability = ?,
                    price = ?, launch_date = ?, image_url = ?,
                    product_page_url = ?, strengths = ?, weaknesses = ?, review_summary = ?,
                    notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                data.get('brand'),
                data.get('name'),
                data.get('category'),
                json.dumps(data.get('design_packaging', {}), ensure_ascii=False),
                json.dumps(data.get('user_experience', {}), ensure_ascii=False),
                json.dumps(data.get('formulation', {}), ensure_ascii=False),
                json.dumps(data.get('color', {}), ensure_ascii=False),
                json.dumps(data.get('scent', {}), ensure_ascii=False),
                json.dumps(data.get('ingredients', {}), ensure_ascii=False),
                json.dumps(data.get('technology', {}), ensure_ascii=False),
                json.dumps(data.get('usage_environment', {}), ensure_ascii=False),
                json.dumps(data.get('marketing', {}), ensure_ascii=False),
                json.dumps(data.get('sustainability', {}), ensure_ascii=False),
                data.get('price'),
                data.get('launch_date'),
                data.get('image_url'),
                data.get('product_page_url'),
                data.get('strengths'),
                data.get('weaknesses'),
                data.get('review_summary'),
                data.get('notes'),
                product_id
            ))
            return True

    def delete_competitor_product(self, product_id: int) -> bool:
        """경쟁사 제품 삭제"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM competitor_products WHERE id = ?", (product_id,))
            return True

    def _parse_competitor_row(self, row: Dict) -> Dict[str, Any]:
        """경쟁사 제품 JSON 필드 파싱"""
        dict_fields = [
            'design_packaging', 'user_experience', 'formulation',
            'color', 'scent', 'ingredients', 'technology',
            'usage_environment', 'marketing', 'sustainability'
        ]
        return self._parse_json_fields(row, dict_fields=dict_fields)

    # ==================== 과거 특이 제품 CRUD ====================

    def add_legacy_product(self, data: Dict[str, Any]) -> int:
        """과거 특이 제품 추가"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO legacy_products (
                    brand, name, category,
                    launch_year, discontinue_year,
                    unique_features, failure_reason, market_condition,
                    revival_potential, current_trend_fit, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('brand'),
                data.get('name'),
                data.get('category'),
                data.get('launch_year'),
                data.get('discontinue_year'),
                data.get('unique_features'),
                data.get('failure_reason'),
                data.get('market_condition'),
                data.get('revival_potential', 3),
                data.get('current_trend_fit'),
                data.get('notes')
            ))
            return cursor.lastrowid

    def get_legacy_products(self) -> List[Dict[str, Any]]:
        """모든 과거 특이 제품 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM legacy_products ORDER BY revival_potential DESC, created_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_legacy_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """특정 과거 특이 제품 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM legacy_products WHERE id = ?", (product_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_legacy_product(self, product_id: int, data: Dict[str, Any]) -> bool:
        """과거 특이 제품 수정"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE legacy_products SET
                    brand = ?, name = ?, category = ?,
                    launch_year = ?, discontinue_year = ?,
                    unique_features = ?, failure_reason = ?, market_condition = ?,
                    revival_potential = ?, current_trend_fit = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                data.get('brand'),
                data.get('name'),
                data.get('category'),
                data.get('launch_year'),
                data.get('discontinue_year'),
                data.get('unique_features'),
                data.get('failure_reason'),
                data.get('market_condition'),
                data.get('revival_potential', 3),
                data.get('current_trend_fit'),
                data.get('notes'),
                product_id
            ))
            return True

    def delete_legacy_product(self, product_id: int) -> bool:
        """과거 특이 제품 삭제"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM legacy_products WHERE id = ?", (product_id,))
            return True

    def get_high_potential_legacy_products(self, min_score: int = 4) -> List[Dict[str, Any]]:
        """부활 가능성 높은 과거 제품 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM legacy_products WHERE revival_potential >= ? ORDER BY revival_potential DESC",
                (min_score,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ==================== 신제품 제안 CRUD ====================

    def add_proposal(self, data: Dict[str, Any]) -> int:
        """신제품 제안 추가"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO product_proposals (
                    title, category, concept_description, key_features,
                    reference_competitor_ids, reference_legacy_ids, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('title'),
                data.get('category'),
                data.get('concept_description'),
                json.dumps(data.get('key_features', []), ensure_ascii=False),
                json.dumps(data.get('reference_competitor_ids', []), ensure_ascii=False),
                json.dumps(data.get('reference_legacy_ids', []), ensure_ascii=False),
                data.get('notes')
            ))
            return cursor.lastrowid

    def get_proposals(self) -> List[Dict[str, Any]]:
        """모든 신제품 제안 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM product_proposals ORDER BY created_at DESC"
            )
            return [self._parse_proposal_row(dict(row)) for row in cursor.fetchall()]

    def get_proposal(self, proposal_id: int) -> Optional[Dict[str, Any]]:
        """특정 신제품 제안 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM product_proposals WHERE id = ?", (proposal_id,)
            )
            row = cursor.fetchone()
            return self._parse_proposal_row(dict(row)) if row else None

    def delete_proposal(self, proposal_id: int) -> bool:
        """신제품 제안 삭제"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM product_proposals WHERE id = ?", (proposal_id,))
            return True

    def _parse_proposal_row(self, row: Dict) -> Dict[str, Any]:
        """신제품 제안 JSON 필드 파싱"""
        list_fields = ['key_features', 'reference_competitor_ids', 'reference_legacy_ids']
        return self._parse_json_fields(row, list_fields=list_fields)

    # ==================== 올리브영 제품 CRUD ====================

    def upsert_oliveyoung_product(self, data: Dict[str, Any]) -> tuple:
        """
        올리브영 제품 추가 또는 업데이트
        Returns: (product_id, is_new) - is_new가 True면 신규 진입 제품
        """
        with self.get_connection() as conn:
            # 기존 제품 확인
            existing = conn.execute(
                "SELECT id, best_rank FROM oliveyoung_products WHERE product_code = ?",
                (data.get('product_code'),)
            ).fetchone()

            if existing:
                # 기존 제품 업데이트
                old_rank = existing['best_rank']
                new_rank = data.get('rank', 0)
                rank_change = old_rank - new_rank if old_rank and new_rank else 0

                conn.execute("""
                    UPDATE oliveyoung_products SET
                        brand = ?, name = ?, category = ?, price = ?, original_price = ?,
                        product_url = ?, image_url = ?, best_rank = ?,
                        review_count = ?, is_new = ?,
                        last_seen_at = CURRENT_TIMESTAMP,
                        last_rank = ?, rank_change = ?
                    WHERE product_code = ?
                """, (
                    data.get('brand'),
                    data.get('name'),
                    data.get('category'),
                    data.get('price'),
                    data.get('original_price'),
                    data.get('product_url'),
                    data.get('image_url'),
                    new_rank,
                    data.get('review_count'),
                    data.get('is_new', False),
                    old_rank,
                    rank_change,
                    data.get('product_code')
                ))
                return (existing['id'], False)
            else:
                # 신규 제품 추가
                cursor = conn.execute("""
                    INSERT INTO oliveyoung_products (
                        product_code, brand, name, category,
                        price, original_price, product_url, image_url,
                        best_rank, review_count, is_new
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('product_code'),
                    data.get('brand'),
                    data.get('name'),
                    data.get('category'),
                    data.get('price'),
                    data.get('original_price'),
                    data.get('product_url'),
                    data.get('image_url'),
                    data.get('rank'),
                    data.get('review_count'),
                    data.get('is_new', False)
                ))
                return (cursor.lastrowid, True)

    def get_oliveyoung_products(self, category: str = None, only_new: bool = False) -> List[Dict]:
        """올리브영 제품 조회"""
        with self.get_connection() as conn:
            query = "SELECT * FROM oliveyoung_products WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category)

            if only_new:
                query += " AND added_to_competitor = 0"

            query += " ORDER BY best_rank ASC"

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def delete_oliveyoung_product(self, product_code: str) -> bool:
        """올리브영 제품 삭제 (관련 리뷰 분석도 함께 삭제)"""
        with self.get_connection() as conn:
            # 리뷰 분석 삭제
            conn.execute("DELETE FROM review_analysis WHERE product_code = ?", (product_code,))
            # 상품 삭제
            conn.execute("DELETE FROM oliveyoung_products WHERE product_code = ?", (product_code,))
            return True

    def get_new_oliveyoung_entries(self, category: str = None) -> List[Dict]:
        """
        새로 100위 안에 진입한 제품 조회
        - 첫 수집 시에는 신규진입 없음
        - 이전 수집에 없었던 제품만 신규진입으로 표시
        """
        with self.get_connection() as conn:
            # 크롤링 히스토리가 2개 이상이어야 신규진입 판단 가능
            history_count = conn.execute(
                "SELECT COUNT(*) FROM crawl_history"
            ).fetchone()[0]

            if history_count < 2:
                # 첫 수집이므로 신규진입 없음
                return []

            # is_new = 1인 제품 중 경쟁사 분석에 추가 안 된 것
            query = """
                SELECT * FROM oliveyoung_products
                WHERE added_to_competitor = 0
                AND is_new = 1
            """
            params = []

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " ORDER BY best_rank ASC"

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def reset_new_flags(self):
        """모든 상품의 is_new 플래그를 초기화 (수집 전에 호출)"""
        with self.get_connection() as conn:
            conn.execute("UPDATE oliveyoung_products SET is_new = 0")

    def mark_oliveyoung_as_added(self, product_id: int):
        """올리브영 제품을 경쟁사 분석에 추가됨으로 표시"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE oliveyoung_products SET added_to_competitor = 1 WHERE id = ?",
                (product_id,)
            )

    def add_crawl_history(self, category: str, products_count: int, new_count: int):
        """크롤링 히스토리 추가"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO crawl_history (category, products_count, new_products_count)
                VALUES (?, ?, ?)
            """, (category, products_count, new_count))

    def get_crawl_history(self, limit: int = 10) -> List[Dict]:
        """크롤링 히스토리 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM crawl_history ORDER BY crawled_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ==================== 리뷰 분석 CRUD ====================

    def save_review_analysis(self, product_code: str, analysis_data: Dict[str, Any]) -> int:
        """리뷰 분석 결과 저장 (upsert)"""
        with self.get_connection() as conn:
            # 기존 분석 확인
            existing = conn.execute(
                "SELECT id FROM review_analysis WHERE product_code = ?",
                (product_code,)
            ).fetchone()

            if existing:
                # 업데이트
                conn.execute("""
                    UPDATE review_analysis SET
                        brand = ?, name = ?,
                        total_reviews = ?, positive_count = ?, negative_count = ?,
                        positive_ratio = ?, strengths = ?, weaknesses = ?,
                        top_positive_keywords = ?, top_negative_keywords = ?,
                        category_scores = ?, summary = ?,
                        repeated_keywords = ?, unique_features = ?,
                        competitor_mentions = ?, comparison_insights = ?,
                        marketing_suggestions = ?, review_samples = ?,
                        usp_candidates = ?, viral_keyword_counts = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE product_code = ?
                """, (
                    analysis_data.get('brand'),
                    analysis_data.get('name'),
                    analysis_data.get('total_reviews', 0),
                    analysis_data.get('positive_count', 0),
                    analysis_data.get('negative_count', 0),
                    analysis_data.get('positive_ratio', 0),
                    json.dumps(analysis_data.get('strengths', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('weaknesses', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('top_positive_keywords', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('top_negative_keywords', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('category_scores', {}), ensure_ascii=False),
                    analysis_data.get('summary', ''),
                    json.dumps(analysis_data.get('repeated_keywords', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('unique_features', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('competitor_mentions', {}), ensure_ascii=False),
                    json.dumps(analysis_data.get('comparison_insights', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('marketing_suggestions', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('review_samples', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('usp_candidates', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('viral_keyword_counts', {}), ensure_ascii=False),
                    product_code
                ))
                return existing['id']
            else:
                # 새로 추가
                cursor = conn.execute("""
                    INSERT INTO review_analysis (
                        product_code, brand, name,
                        total_reviews, positive_count, negative_count,
                        positive_ratio, strengths, weaknesses,
                        top_positive_keywords, top_negative_keywords,
                        category_scores, summary,
                        repeated_keywords, unique_features,
                        competitor_mentions, comparison_insights,
                        marketing_suggestions, review_samples,
                        usp_candidates, viral_keyword_counts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product_code,
                    analysis_data.get('brand'),
                    analysis_data.get('name'),
                    analysis_data.get('total_reviews', 0),
                    analysis_data.get('positive_count', 0),
                    analysis_data.get('negative_count', 0),
                    analysis_data.get('positive_ratio', 0),
                    json.dumps(analysis_data.get('strengths', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('weaknesses', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('top_positive_keywords', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('top_negative_keywords', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('category_scores', {}), ensure_ascii=False),
                    analysis_data.get('summary', ''),
                    json.dumps(analysis_data.get('repeated_keywords', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('unique_features', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('competitor_mentions', {}), ensure_ascii=False),
                    json.dumps(analysis_data.get('comparison_insights', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('marketing_suggestions', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('review_samples', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('usp_candidates', []), ensure_ascii=False),
                    json.dumps(analysis_data.get('viral_keyword_counts', {}), ensure_ascii=False)
                ))
                return cursor.lastrowid

    def get_review_analysis(self, product_code: str) -> Optional[Dict[str, Any]]:
        """특정 상품의 리뷰 분석 결과 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM review_analysis WHERE product_code = ?",
                (product_code,)
            )
            row = cursor.fetchone()
            if row:
                return self._parse_review_analysis_row(dict(row))
            return None

    def get_review_analyses_by_codes(self, product_codes: List[str]) -> List[Dict[str, Any]]:
        """여러 상품코드의 리뷰 분석 결과 조회"""
        if not product_codes:
            return []
        with self.get_connection() as conn:
            placeholders = ','.join(['?' for _ in product_codes])
            cursor = conn.execute(
                f"SELECT * FROM review_analysis WHERE product_code IN ({placeholders})",
                product_codes
            )
            return [self._parse_review_analysis_row(dict(row)) for row in cursor.fetchall()]

    def get_analyzed_product_codes(self) -> set:
        """분석 완료된 상품 코드 목록"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT product_code FROM review_analysis")
            return {row['product_code'] for row in cursor.fetchall()}

    def get_analyzed_product_dates(self) -> Dict[str, str]:
        """분석 완료된 상품 코드와 분석 날짜 딕셔너리"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT product_code, analyzed_at FROM review_analysis")
            return {row['product_code']: row['analyzed_at'] for row in cursor.fetchall()}

    def get_analyzed_product_review_counts(self) -> Dict[str, int]:
        """분석 완료된 상품 코드와 리뷰 수집 개수 딕셔너리"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT product_code, total_reviews FROM review_analysis")
            return {row['product_code']: row['total_reviews'] for row in cursor.fetchall()}

    def _parse_review_analysis_row(self, row: Dict) -> Dict[str, Any]:
        """리뷰 분석 JSON 필드 파싱"""
        list_fields = [
            'strengths', 'weaknesses', 'top_positive_keywords',
            'top_negative_keywords', 'repeated_keywords',
            'unique_features', 'comparison_insights',
            'marketing_suggestions', 'review_samples',
            'usp_candidates'
        ]
        dict_fields = ['category_scores', 'competitor_mentions', 'viral_keyword_counts']
        return self._parse_json_fields(row, list_fields=list_fields, dict_fields=dict_fields)

    # ==================== 발굴된 과거 제품 CRUD ====================

    def add_discovered_product(self, data: Dict[str, Any]) -> int:
        """발굴된 과거 제품 추가"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO discovered_hit_products (
                    brand, name, category,
                    discovery_source, discovery_keyword, source_url,
                    discontinuation_status, revival_potential, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('brand'),
                data.get('name'),
                data.get('category', '미분류'),
                data.get('discovery_source'),
                data.get('discovery_keyword'),
                data.get('source_url'),
                data.get('discontinuation_status', 'pending'),
                data.get('revival_potential', 3),
                data.get('notes')
            ))
            return cursor.lastrowid

    def get_discovered_products(self, status: str = None) -> List[Dict[str, Any]]:
        """발굴된 과거 제품 조회"""
        with self.get_connection() as conn:
            if status:
                cursor = conn.execute(
                    """SELECT * FROM discovered_hit_products
                    WHERE discontinuation_status = ?
                    ORDER BY created_at DESC""",
                    (status,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM discovered_hit_products ORDER BY created_at DESC"
                )
            return [self._parse_discovered_product_row(dict(row)) for row in cursor.fetchall()]

    def get_discovered_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """특정 발굴된 제품 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM discovered_hit_products WHERE id = ?", (product_id,)
            )
            row = cursor.fetchone()
            return self._parse_discovered_product_row(dict(row)) if row else None

    def get_discovered_product_by_name(self, brand: str, name: str) -> Optional[Dict[str, Any]]:
        """브랜드+제품명으로 발굴된 제품 조회 (중복 체크용)"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM discovered_hit_products WHERE brand = ? AND name = ?",
                (brand, name)
            )
            row = cursor.fetchone()
            return self._parse_discovered_product_row(dict(row)) if row else None

    def update_discovered_product(self, product_id: int, data: Dict[str, Any]) -> bool:
        """발굴된 제품 정보 업데이트"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE discovered_hit_products SET
                    brand = ?, name = ?, category = ?,
                    discontinuation_status = ?,
                    revival_potential = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                data.get('brand'),
                data.get('name'),
                data.get('category'),
                data.get('discontinuation_status'),
                data.get('revival_potential', 3),
                data.get('notes'),
                product_id
            ))
            return True

    def delete_discovered_product(self, product_id: int) -> bool:
        """발굴된 제품 삭제"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM discovered_hit_products WHERE id = ?", (product_id,))
            return True

    def add_discovery_history(self, source: str, found: int, discontinued: int = 0) -> int:
        """발굴 히스토리 추가"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO discovery_history (discovery_source, products_found, discontinued_count)
                VALUES (?, ?, ?)
            """, (source, found, discontinued))
            return cursor.lastrowid

    def get_discovery_history(self, limit: int = 10) -> List[Dict]:
        """발굴 히스토리 조회"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM discovery_history ORDER BY discovered_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def _parse_discovered_product_row(self, row: Dict) -> Dict[str, Any]:
        """발굴된 제품 JSON 필드 파싱"""
        list_fields = ['review_samples', 'strengths', 'weaknesses',
                       'inferred_discontinuation_reasons', 'marketing_points']
        return self._parse_json_fields(row, list_fields=list_fields)

    # ==================== 통계 ====================

    def get_statistics(self) -> Dict[str, int]:
        """전체 통계 조회"""
        with self.get_connection() as conn:
            stats = {}
            stats['competitor_count'] = conn.execute(
                "SELECT COUNT(*) FROM competitor_products"
            ).fetchone()[0]
            stats['legacy_count'] = conn.execute(
                "SELECT COUNT(*) FROM legacy_products"
            ).fetchone()[0]
            stats['proposal_count'] = conn.execute(
                "SELECT COUNT(*) FROM product_proposals"
            ).fetchone()[0]
            stats['high_potential_count'] = conn.execute(
                "SELECT COUNT(*) FROM legacy_products WHERE revival_potential >= 4"
            ).fetchone()[0]

            # 올리브영 테이블 존재 여부 확인 후 통계 추가
            try:
                stats['oliveyoung_count'] = conn.execute(
                    "SELECT COUNT(*) FROM oliveyoung_products"
                ).fetchone()[0]
                stats['oliveyoung_new_count'] = conn.execute(
                    "SELECT COUNT(*) FROM oliveyoung_products WHERE added_to_competitor = 0"
                ).fetchone()[0]
            except:
                stats['oliveyoung_count'] = 0
                stats['oliveyoung_new_count'] = 0

            return stats
