"""
경쟁사 제품 분석 페이지
"""
import streamlit as st
import pandas as pd
import json

from config import DB_PATH, PRODUCT_CATEGORIES, CLASSIFICATION_SCHEMA
from database.db_manager import DatabaseManager

st.set_page_config(page_title="경쟁사 제품 분석", page_icon="🔍", layout="wide")

@st.cache_resource
def get_db():
    return DatabaseManager(DB_PATH)

db = get_db()


def render_classification_inputs(category_key: str, schema: dict, prefix: str = "") -> dict:
    """분류 스키마 기반 입력 위젯 생성"""
    result = {}

    for key, value in schema.items():
        full_key = f"{prefix}_{key}" if prefix else key

        if isinstance(value, dict):
            st.markdown(f"**{key}**")
            result[key] = render_classification_inputs(key, value, full_key)
        elif isinstance(value, list):
            selected = st.multiselect(
                key,
                options=value,
                key=f"ms_{category_key}_{full_key}"
            )
            if selected:
                result[key] = selected
        else:
            result[key] = value

    return result


def product_form(product_data: dict = None, form_key: str = "new"):
    """제품 등록/수정 폼"""
    is_edit = product_data is not None
    data = product_data or {}

    with st.form(key=f"product_form_{form_key}"):
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

        col1, col2, col3 = st.columns(3)
        with col1:
            price = st.number_input("가격 (원)", value=data.get('price', 0), min_value=0, step=1000)
        with col2:
            launch_date = st.text_input("출시일 (YYYY-MM)", value=data.get('launch_date', ''))
        with col3:
            product_page_url = st.text_input("상세페이지 URL", value=data.get('product_page_url', ''))

        image_url = st.text_input("이미지 URL", value=data.get('image_url', ''))

        st.divider()

        # 10가지 대분류 탭
        st.subheader("📊 제품 분석 (10가지 관점)")

        tabs = st.tabs([
            "디자인/패키징", "사용자경험", "제형", "컬러", "향",
            "성분", "기술", "사용환경", "마케팅", "지속가능성"
        ])

        classification_data = {}

        with tabs[0]:  # 디자인/패키징
            st.markdown("**디자인/패키징 특징**")
            classification_data['design_packaging'] = st.text_area(
                "디자인/패키징 분석",
                value=json.dumps(data.get('design_packaging', {}), ensure_ascii=False, indent=2) if isinstance(data.get('design_packaging'), dict) else data.get('design_packaging', ''),
                height=150,
                help="단상자, 용기, 소재, 패션결합, 휴대성 등"
            )

        with tabs[1]:  # 사용자경험
            st.markdown("**사용자 경험 (UX)**")
            classification_data['user_experience'] = st.text_area(
                "사용자 경험 분석",
                value=json.dumps(data.get('user_experience', {}), ensure_ascii=False, indent=2) if isinstance(data.get('user_experience'), dict) else data.get('user_experience', ''),
                height=150,
                help="촉감, 개폐감, 사용방식, ASMR 요소 등"
            )

        with tabs[2]:  # 제형
            st.markdown("**제형**")
            classification_data['formulation'] = st.text_area(
                "제형 분석",
                value=json.dumps(data.get('formulation', {}), ensure_ascii=False, indent=2) if isinstance(data.get('formulation'), dict) else data.get('formulation', ''),
                height=150,
                help="기본제형, 변형, 시각제형, 연출 등"
            )

        with tabs[3]:  # 컬러
            st.markdown("**컬러**")
            classification_data['color'] = st.text_area(
                "컬러 분석",
                value=json.dumps(data.get('color', {}), ensure_ascii=False, indent=2) if isinstance(data.get('color'), dict) else data.get('color', ''),
                height=150,
                help="단일, 다중, 기능, 반응, 시즌 컬러 등"
            )

        with tabs[4]:  # 향
            st.markdown("**향**")
            classification_data['scent'] = st.text_area(
                "향 분석",
                value=json.dumps(data.get('scent', {}), ensure_ascii=False, indent=2) if isinstance(data.get('scent'), dict) else data.get('scent', ''),
                height=150,
                help="무향, 시그니처, 라인구분, 잔향설계 등"
            )

        with tabs[5]:  # 성분
            st.markdown("**성분**")
            classification_data['ingredients'] = st.text_area(
                "성분 분석",
                value=json.dumps(data.get('ingredients', {}), ensure_ascii=False, indent=2) if isinstance(data.get('ingredients'), dict) else data.get('ingredients', ''),
                height=150,
                help="즉각체감, 컨셉, 트렌드, 안전성 성분 등"
            )

        with tabs[6]:  # 기술
            st.markdown("**기술**")
            classification_data['technology'] = st.text_area(
                "기술 분석",
                value=json.dumps(data.get('technology', {}), ensure_ascii=False, indent=2) if isinstance(data.get('technology'), dict) else data.get('technology', ''),
                height=150,
                help="전달기술, 지속기술, 밀착, 안정화 등"
            )

        with tabs[7]:  # 사용환경
            st.markdown("**사용 환경/씬**")
            classification_data['usage_environment'] = st.text_area(
                "사용환경 분석",
                value=json.dumps(data.get('usage_environment', {}), ensure_ascii=False, indent=2) if isinstance(data.get('usage_environment'), dict) else data.get('usage_environment', ''),
                height=150,
                help="시간, 장소, 계절, 부위, 상황 등"
            )

        with tabs[8]:  # 마케팅
            st.markdown("**마케팅/구매 트리거**")
            classification_data['marketing'] = st.text_area(
                "마케팅 분석",
                value=json.dumps(data.get('marketing', {}), ensure_ascii=False, indent=2) if isinstance(data.get('marketing'), dict) else data.get('marketing', ''),
                height=150,
                help="바이럴, 증거, 한정, 메시지, 가격구조 등"
            )

        with tabs[9]:  # 지속가능성
            st.markdown("**지속가능성**")
            classification_data['sustainability'] = st.text_area(
                "지속가능성 분석",
                value=json.dumps(data.get('sustainability', {}), ensure_ascii=False, indent=2) if isinstance(data.get('sustainability'), dict) else data.get('sustainability', ''),
                height=150,
                help="리필, 분리배출, 재사용 등"
            )

        st.divider()

        # 장단점 분석 (리뷰 기반)
        st.subheader("💪 장점 / 약점 분석")
        st.caption("💡 장점은 상세페이지/블로그에서, 단점은 리뷰에서 찾으면 효과적입니다!")

        col1, col2 = st.columns(2)
        with col1:
            strengths = st.text_area(
                "장점 (상세페이지/블로그 기반)",
                value=data.get('strengths', ''),
                height=120
            )
        with col2:
            weaknesses = st.text_area(
                "단점 (리뷰 기반) ⭐중요",
                value=data.get('weaknesses', ''),
                height=120
            )

        review_summary = st.text_area(
            "리뷰 요약",
            value=data.get('review_summary', ''),
            height=100
        )

        notes = st.text_area("기타 메모", value=data.get('notes', ''), height=80)

        submitted = st.form_submit_button("💾 저장" if not is_edit else "✏️ 수정", use_container_width=True)

        if submitted:
            if not brand or not name:
                st.error("브랜드명과 제품명은 필수입니다.")
                return None

            # JSON 필드 파싱
            parsed_data = {
                'brand': brand,
                'name': name,
                'category': category,
                'price': price if price > 0 else None,
                'launch_date': launch_date,
                'image_url': image_url,
                'product_page_url': product_page_url,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'review_summary': review_summary,
                'notes': notes
            }

            # 분류 데이터 파싱
            for key, value in classification_data.items():
                try:
                    parsed_data[key] = json.loads(value) if value.strip().startswith('{') else {'notes': value}
                except json.JSONDecodeError:
                    parsed_data[key] = {'notes': value}

            return parsed_data

    return None


def main():
    st.title("🔍 경쟁사 제품 분석")

    # 탭 구성
    tab_list, tab_add, tab_compare = st.tabs(["📋 제품 목록", "➕ 제품 추가", "⚖️ 제품 비교"])

    with tab_list:
        products = db.get_competitor_products()

        if not products:
            st.info("등록된 경쟁사 제품이 없습니다. '제품 추가' 탭에서 추가해주세요.")
        else:
            # 필터
            col1, col2 = st.columns([1, 3])
            with col1:
                filter_category = st.selectbox(
                    "카테고리 필터",
                    options=["전체"] + PRODUCT_CATEGORIES
                )

            if filter_category != "전체":
                products = [p for p in products if p.get('category') == filter_category]

            st.markdown(f"**총 {len(products)}개 제품**")

            for product in products:
                with st.expander(f"**{product['brand']}** - {product['name']} ({product['category']})"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        if product.get('price'):
                            st.markdown(f"💰 가격: {product['price']:,}원")
                        if product.get('launch_date'):
                            st.markdown(f"📅 출시: {product['launch_date']}")
                        if product.get('product_page_url'):
                            st.markdown(f"🔗 [상세페이지]({product['product_page_url']})")

                        st.divider()

                        if product.get('strengths'):
                            st.markdown(f"**✅ 장점:** {product['strengths']}")
                        if product.get('weaknesses'):
                            st.markdown(f"**❌ 단점:** {product['weaknesses']}")
                        if product.get('review_summary'):
                            st.markdown(f"**📝 리뷰 요약:** {product['review_summary']}")

                    with col2:
                        if product.get('image_url'):
                            st.image(product['image_url'], width=150)

                        if st.button("🗑️ 삭제", key=f"del_{product['id']}"):
                            db.delete_competitor_product(product['id'])
                            st.rerun()

    with tab_add:
        result = product_form()
        if result:
            db.add_competitor_product(result)
            st.success("✅ 제품이 추가되었습니다!")
            st.rerun()

    with tab_compare:
        products = db.get_competitor_products()

        if len(products) < 2:
            st.info("비교하려면 최소 2개 이상의 제품이 필요합니다.")
        else:
            product_options = {f"{p['brand']} - {p['name']}": p['id'] for p in products}
            selected = st.multiselect(
                "비교할 제품 선택 (2~4개)",
                options=list(product_options.keys()),
                max_selections=4
            )

            if len(selected) >= 2:
                compare_data = []
                for name in selected:
                    product = db.get_competitor_product(product_options[name])
                    if product:
                        compare_data.append({
                            '제품': f"{product['brand']} - {product['name']}",
                            '카테고리': product.get('category', '-'),
                            '가격': f"{product['price']:,}원" if product.get('price') else '-',
                            '장점': product.get('strengths', '-')[:50] + '...' if product.get('strengths') else '-',
                            '단점': product.get('weaknesses', '-')[:50] + '...' if product.get('weaknesses') else '-'
                        })

                df = pd.DataFrame(compare_data)
                st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
