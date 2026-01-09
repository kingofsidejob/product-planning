"""
과거 특이 제품 분석 페이지
"""
import streamlit as st

from config import (
    DB_PATH, PRODUCT_CATEGORIES, REVIVAL_POTENTIAL_LABELS,
    NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
)
from database.db_manager import DatabaseManager
from modules.legacy_discoverer import LegacyDiscoverer

st.set_page_config(page_title="과거 특이 제품", page_icon="📜", layout="wide")

@st.cache_resource
def get_db():
    return DatabaseManager(DB_PATH)

db = get_db()


def render_discovery_tab():
    """자동 발굴 탭 렌더링"""
    st.subheader("과거 히트상품 자동 발굴")
    st.caption("네이버 검색 API를 활용하여 단종된 화장품을 자동으로 찾습니다.")

    # API 키 확인
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        st.error("네이버 API 키가 설정되지 않았습니다.")
        st.info("""
        **설정 방법:**
        1. [네이버 개발자 센터](https://developers.naver.com/)에서 애플리케이션 등록
        2. 검색 API 사용 신청
        3. 프로젝트 루트에 `.env` 파일 생성:
        ```
        NAVER_CLIENT_ID=your_client_id
        NAVER_CLIENT_SECRET=your_client_secret
        ```
        """)
        return

    # 검색 설정
    st.markdown("**검색 설정**")
    col1, col2, col3 = st.columns(3)

    with col1:
        sources = st.multiselect(
            "검색 소스",
            options=["blog", "cafe", "kin"],
            default=["blog", "cafe", "kin"],
            format_func=lambda x: {"blog": "블로그", "cafe": "카페", "kin": "지식인"}[x]
        )

    with col2:
        max_products = st.number_input(
            "최대 발굴 개수",
            min_value=1,
            max_value=10,
            value=5
        )

    with col3:
        min_mentions = st.number_input(
            "최소 언급 횟수",
            min_value=1,
            max_value=20,
            value=5,
            help="이 횟수 이상 반복 언급된 제품만 수집"
        )

    # 발굴 시작 버튼
    if st.button("발굴 시작", width='stretch', type="primary"):
        if not sources:
            st.warning("검색 소스를 하나 이상 선택해주세요.")
            return

        discoverer = LegacyDiscoverer(db)

        # 진행 상황 표시
        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_callback(message, current, total):
            progress = current / total if total > 0 else 0
            progress = min(progress, 1.0)  # 1.0 초과 방지
            progress_bar.progress(progress)
            status_text.text(message)

        # 발굴 실행
        with st.spinner("검색 중..."):
            results = discoverer.discover(
                sources=sources,
                max_products=max_products,
                min_mentions=min_mentions,
                callback=progress_callback
            )

        progress_bar.empty()
        status_text.empty()

        if not results:
            st.warning("발굴된 제품이 없습니다. 다른 검색 조건을 시도해보세요.")
        else:
            st.success(f"{len(results)}개 제품 발굴 완료!")
            st.session_state['discovered_products'] = results

    # 발굴 결과 표시
    if 'discovered_products' in st.session_state and st.session_state['discovered_products']:
        st.divider()
        st.markdown("**발굴 결과**")

        results = st.session_state['discovered_products']

        # 저장할 제품 선택
        selected_products = []

        for i, product in enumerate(results):
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])

                with col1:
                    mention_count = product.get('mention_count', 1)
                    st.markdown(f"**{i+1}. {product['brand']}** - {product['name']} ({mention_count}회 언급)")

                    # 원문 한 줄 미리보기 + 링크
                    context_preview = product.get('context', '')[:80] + '...' if product.get('context') else ''
                    source_url = product.get('source_url', '')

                    if source_url:
                        st.caption(f"{context_preview} [원문보기]({source_url})")
                    else:
                        st.caption(context_preview)

                with col2:
                    if st.checkbox("저장", key=f"save_discovered_{i}", value=True):
                        selected_products.append(product)

        # 선택한 제품 저장
        if st.button(f"선택한 제품 저장 ({len(selected_products)}개)", width='stretch'):
            saved_count = 0
            for product in selected_products:
                try:
                    db.add_discovered_product({
                        'brand': product['brand'],
                        'name': product['name'],
                        'category': '미분류',
                        'discovery_source': product.get('discovery_source'),
                        'discovery_keyword': product.get('discovery_keyword'),
                        'source_url': product.get('source_url'),
                        'notes': product.get('context', '')[:500]
                    })
                    saved_count += 1
                except Exception as e:
                    # 중복 등 오류 무시
                    pass

            if saved_count > 0:
                st.success(f"{saved_count}개 제품이 저장되었습니다!")
                # 발굴 히스토리 기록
                source_str = ",".join(sources)
                db.add_discovery_history(source_str, saved_count)

            # 세션에서 결과 제거
            del st.session_state['discovered_products']
            st.rerun()

    # 발굴된 제품 목록
    st.divider()
    st.markdown("**저장된 발굴 제품**")

    discovered = db.get_discovered_products()

    if not discovered:
        st.info("아직 발굴된 제품이 없습니다. 위에서 '발굴 시작'을 눌러주세요.")
    else:
        st.markdown(f"총 {len(discovered)}개 제품")

        for product in discovered:
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])

                with col1:
                    st.markdown(f"**{product['brand']}** - {product['name']}")
                    source_label = {"blog": "블로그", "cafe": "카페", "kin": "지식인"}.get(
                        product.get('discovery_source', ''), product.get('discovery_source', '')
                    )

                    # 메모 한 줄 + 원문 링크
                    note_preview = product.get('notes', '')[:60] + '...' if product.get('notes') else ''
                    source_url = product.get('source_url', '')

                    if source_url:
                        st.caption(f"{note_preview} [원문보기]({source_url})")
                    else:
                        st.caption(note_preview)

                with col2:
                    if st.button("삭제", key=f"del_discovered_{product['id']}"):
                        db.delete_discovered_product(product['id'])
                        st.rerun()


def main():
    st.title("과거 특이 제품 분석")
    st.caption("과거에 실패했지만 현재 트렌드에 부활 가능성이 있는 제품들을 조사합니다.")

    # 탭 구성
    tab_list, tab_discover = st.tabs([
        "제품 목록", "자동 발굴"
    ])

    with tab_list:
        products = db.get_legacy_products()

        if not products:
            st.info("등록된 과거 특이 제품이 없습니다. '자동 발굴' 탭을 이용해주세요.")
        else:
            # 필터
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                filter_category = st.selectbox(
                    "카테고리 필터",
                    options=["전체"] + PRODUCT_CATEGORIES,
                    key="legacy_cat_filter"
                )
            with col2:
                min_potential = st.slider(
                    "최소 부활 가능성",
                    min_value=1,
                    max_value=5,
                    value=1,
                    key="legacy_potential_filter"
                )

            # 필터 적용
            filtered = products
            if filter_category != "전체":
                filtered = [p for p in filtered if p.get('category') == filter_category]
            filtered = [p for p in filtered if p.get('revival_potential', 0) >= min_potential]

            st.markdown(f"**총 {len(filtered)}개 제품** (부활 가능성 높은 순)")

            # 부활 가능성 높은 제품 하이라이트
            high_potential = [p for p in filtered if p.get('revival_potential', 0) >= 4]
            if high_potential:
                st.success(f"부활 가능성 높은 제품 {len(high_potential)}개!")

            for product in filtered:
                potential = product.get('revival_potential', 3)
                stars = "★" * potential + "☆" * (5 - potential)

                with st.expander(f"{stars} **{product['brand']}** - {product['name']} ({product['category']})"):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(f"출시: {product.get('launch_year', '-')} → 단종: {product.get('discontinue_year', '-')}")

                        st.divider()

                        st.markdown("**특이점:**")
                        st.write(product.get('unique_features', '-'))

                        if product.get('failure_reason'):
                            st.markdown("**실패 이유:**")
                            st.write(product['failure_reason'])

                        if product.get('market_condition'):
                            st.markdown("**당시 시장 상황:**")
                            st.write(product['market_condition'])

                        if product.get('current_trend_fit'):
                            st.markdown("**현재 트렌드 적합성:**")
                            st.write(product['current_trend_fit'])

                    with col2:
                        st.metric(
                            "부활 가능성",
                            f"{potential}점",
                            help=REVIVAL_POTENTIAL_LABELS[potential]
                        )

                        if st.button("삭제", key=f"del_legacy_{product['id']}"):
                            db.delete_legacy_product(product['id'])
                            st.rerun()

    with tab_discover:
        render_discovery_tab()


if __name__ == "__main__":
    main()
