"""
과거 특이 제품 분석 페이지
"""
import streamlit as st

from config import DB_PATH, PRODUCT_CATEGORIES, REVIVAL_POTENTIAL_LABELS
from database.db_manager import DatabaseManager

st.set_page_config(page_title="과거 특이 제품", page_icon="📜", layout="wide")

@st.cache_resource
def get_db():
    return DatabaseManager(DB_PATH)

db = get_db()


def legacy_product_form(product_data: dict = None, form_key: str = "new"):
    """과거 특이 제품 등록/수정 폼"""
    is_edit = product_data is not None
    data = product_data or {}

    with st.form(key=f"legacy_form_{form_key}"):
        st.subheader("📝 기본 정보")

        col1, col2, col3 = st.columns(3)
        with col1:
            brand = st.text_input("브랜드명 *", value=data.get('brand', ''))
        with col2:
            name = st.text_input("제품명 *", value=data.get('name', ''))
        with col3:
            category = st.selectbox(
                "카테고리 *",
                options=PRODUCT_CATEGORIES,
                index=PRODUCT_CATEGORIES.index(data.get('category', '스킨케어')) if data.get('category') in PRODUCT_CATEGORIES else 0
            )

        col1, col2 = st.columns(2)
        with col1:
            launch_year = st.number_input(
                "출시 연도",
                value=data.get('launch_year', 2020),
                min_value=1990,
                max_value=2026,
                step=1
            )
        with col2:
            discontinue_year = st.number_input(
                "단종 연도",
                value=data.get('discontinue_year', 2022),
                min_value=1990,
                max_value=2026,
                step=1
            )

        st.divider()

        st.subheader("🔍 제품 분석")

        unique_features = st.text_area(
            "어떤 점이 특이했는지 *",
            value=data.get('unique_features', ''),
            height=100,
            help="당시에 독특했던 제형, 디자인, 컨셉 등"
        )

        failure_reason = st.text_area(
            "실패 이유",
            value=data.get('failure_reason', ''),
            height=100,
            help="시기상조, 가격, 마케팅 부족, 소비자 인식 등"
        )

        market_condition = st.text_area(
            "당시 시장 상황",
            value=data.get('market_condition', ''),
            height=100,
            help="경쟁 상황, 소비자 트렌드, 경제 상황 등"
        )

        st.divider()

        st.subheader("⭐ 부활 가능성 평가")

        revival_potential = st.slider(
            "부활 가능성 점수",
            min_value=1,
            max_value=5,
            value=data.get('revival_potential', 3),
            help="1: 매우 낮음 ~ 5: 매우 높음"
        )

        # 점수 설명 표시
        st.caption(f"현재 점수: **{revival_potential}점** - {REVIVAL_POTENTIAL_LABELS[revival_potential]}")

        current_trend_fit = st.text_area(
            "현재 트렌드 적합성",
            value=data.get('current_trend_fit', ''),
            height=100,
            help="현재 트렌드와 어떻게 맞는지, 왜 부활 가능성이 있는지"
        )

        notes = st.text_area("기타 메모", value=data.get('notes', ''), height=80)

        submitted = st.form_submit_button(
            "💾 저장" if not is_edit else "✏️ 수정",
            width='stretch'
        )

        if submitted:
            if not brand or not name or not unique_features:
                st.error("브랜드명, 제품명, 특이점은 필수입니다.")
                return None

            return {
                'brand': brand,
                'name': name,
                'category': category,
                'launch_year': launch_year,
                'discontinue_year': discontinue_year,
                'unique_features': unique_features,
                'failure_reason': failure_reason,
                'market_condition': market_condition,
                'revival_potential': revival_potential,
                'current_trend_fit': current_trend_fit,
                'notes': notes
            }

    return None


def main():
    st.title("📜 과거 특이 제품 분석")
    st.caption("과거에 실패했지만 현재 트렌드에 부활 가능성이 있는 제품들을 조사합니다.")

    # 탭 구성
    tab_list, tab_add = st.tabs(["📋 제품 목록", "➕ 제품 추가"])

    with tab_list:
        products = db.get_legacy_products()

        if not products:
            st.info("등록된 과거 특이 제품이 없습니다. '제품 추가' 탭에서 추가해주세요.")
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
                st.success(f"🌟 부활 가능성 높은 제품 {len(high_potential)}개!")

            for product in filtered:
                potential = product.get('revival_potential', 3)
                stars = "⭐" * potential

                with st.expander(f"{stars} **{product['brand']}** - {product['name']} ({product['category']})"):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(f"📅 출시: {product.get('launch_year', '-')} → 단종: {product.get('discontinue_year', '-')}")

                        st.divider()

                        st.markdown("**🔍 특이점:**")
                        st.write(product.get('unique_features', '-'))

                        if product.get('failure_reason'):
                            st.markdown("**❌ 실패 이유:**")
                            st.write(product['failure_reason'])

                        if product.get('market_condition'):
                            st.markdown("**📊 당시 시장 상황:**")
                            st.write(product['market_condition'])

                        if product.get('current_trend_fit'):
                            st.markdown("**✨ 현재 트렌드 적합성:**")
                            st.write(product['current_trend_fit'])

                    with col2:
                        st.metric(
                            "부활 가능성",
                            f"{potential}점",
                            help=REVIVAL_POTENTIAL_LABELS[potential]
                        )

                        if st.button("🗑️ 삭제", key=f"del_legacy_{product['id']}"):
                            db.delete_legacy_product(product['id'])
                            st.rerun()

    with tab_add:
        result = legacy_product_form()
        if result:
            db.add_legacy_product(result)
            st.success("✅ 과거 특이 제품이 추가되었습니다!")
            st.rerun()


if __name__ == "__main__":
    main()
