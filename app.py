"""
화장품 신제품 개발 시장 조사 분석 도구 - 메인 대시보드
"""
import streamlit as st

from config import DB_PATH
from database.db_manager import DatabaseManager

# 페이지 설정
st.set_page_config(
    page_title="화장품 시장 조사 분석",
    page_icon="💄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 데이터베이스 연결 (세션에 캐시)
@st.cache_resource
def get_db():
    return DatabaseManager(DB_PATH)

db = get_db()


def main():
    st.title("💄 화장품 신제품 개발 시장 조사")

    # 통계 가져오기
    stats = db.get_statistics()

    # 상단 메트릭 카드 (간소화)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("경쟁사 제품", f"{stats['competitor_count']}개")
    with m2:
        st.metric("과거 특이 제품", f"{stats['legacy_count']}개")
    with m3:
        st.metric("부활 가능성 높음", f"{stats['high_potential_count']}개")

    st.divider()

    # 3개 섹션 가로 배치
    col1, col2, col3 = st.columns(3)

    # ===== 1. 경쟁사 제품 분석 =====
    with col1:
        st.subheader("🔍 경쟁사 제품 분석")
        competitor_products = db.get_competitor_products()

        if competitor_products:
            for p in competitor_products:
                with st.container(border=True):
                    st.markdown(f"**{p['brand']}** - {p['name']}")
                    st.caption(f"{p.get('category', '-')} · {p['price']:,}원" if p.get('price') else p.get('category', '-'))
                    if p.get('weaknesses'):
                        st.markdown(f"❌ {p['weaknesses'][:80]}{'...' if len(p.get('weaknesses', '')) > 80 else ''}")
        else:
            st.info("등록된 경쟁사 제품이 없습니다.")

        st.page_link("pages/1_경쟁사_제품_분석.py", label="➕ 제품 추가하기", icon="🔗")

    # ===== 2. 과거 특이 제품 조사 =====
    with col2:
        st.subheader("📜 과거 특이 제품 조사")
        legacy_products = db.get_legacy_products()

        if legacy_products:
            for p in legacy_products:
                with st.container(border=True):
                    stars = "⭐" * p.get('revival_potential', 0)
                    st.markdown(f"**{p['brand']}** - {p['name']} {stars}")
                    st.caption(f"{p.get('launch_year', '-')} → {p.get('discontinue_year', '-')} 단종")
                    if p.get('unique_features'):
                        st.markdown(f"✨ {p['unique_features'][:60]}{'...' if len(p.get('unique_features', '')) > 60 else ''}")
        else:
            st.info("등록된 과거 제품이 없습니다.")

        st.page_link("pages/2_과거_특이_제품.py", label="➕ 제품 추가하기", icon="🔗")

    # ===== 3. 신제품 아이디어 제안 =====
    with col3:
        st.subheader("💡 신제품 아이디어 제안")

        # 기회 발굴 요약
        high_potential = db.get_high_potential_legacy_products(min_score=4)
        weaknesses_count = len([p for p in competitor_products if p.get('weaknesses')]) if competitor_products else 0

        st.markdown(f"**발견된 기회: {weaknesses_count + len(high_potential)}개**")

        if weaknesses_count > 0:
            with st.container(border=True):
                st.markdown("🎯 **경쟁사 약점 기반**")
                for p in competitor_products[:3]:
                    if p.get('weaknesses'):
                        st.caption(f"• {p['brand']}: {p['weaknesses'][:40]}...")

        if high_potential:
            with st.container(border=True):
                st.markdown("🔄 **부활 가능 제품**")
                for p in high_potential[:3]:
                    st.caption(f"• {p['brand']} {p['name']} ({'⭐' * p['revival_potential']})")

        if not high_potential and weaknesses_count == 0:
            st.info("데이터를 추가하면 기회를 발굴합니다.")

        st.page_link("pages/3_신제품_제안.py", label="📤 상세 보기 / 내보내기", icon="🔗")

    # 사이드바 안내
    with st.sidebar:
        st.header("📌 사용 방법")
        st.markdown("""
        1. **경쟁사 제품 분석**: 현재 시장의 경쟁 제품 분석
        2. **과거 특이 제품**: 과거 실패했지만 부활 가능한 제품
        3. **신제품 제안**: 데이터 기반 아이디어 도출

        ---

        💡 **팁**: 리뷰에서 단점을 찾아 기록하면 경쟁사의 약점을 파악할 수 있습니다.
        """)


if __name__ == "__main__":
    main()
