"""
신제품 제안 페이지
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from config import DB_PATH, PRODUCT_CATEGORIES, REVIVAL_POTENTIAL_LABELS
from database.db_manager import DatabaseManager

st.set_page_config(page_title="신제품 제안", page_icon="💡", layout="wide")

@st.cache_resource
def get_db():
    return DatabaseManager(DB_PATH)

db = get_db()


def generate_export_markdown():
    """Claude용 마크다운 내보내기 생성"""
    legacy_products = db.get_legacy_products()
    high_potential = db.get_high_potential_legacy_products(min_score=4)

    md = f"""# 화장품 시장 조사 데이터 요약
생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 1. 부활 가능성 높은 과거 제품 ({len(high_potential)}개)

"""

    if high_potential:
        for p in high_potential:
            md += f"""### {p['brand']} - {p['name']} (⭐{p['revival_potential']})
- **카테고리**: {p.get('category', '-')}
- **출시/단종**: {p.get('launch_year', '-')} → {p.get('discontinue_year', '-')}
- **특이점**: {p.get('unique_features', '-')}
- **실패 이유**: {p.get('failure_reason', '-')}
- **현재 트렌드 적합성**: {p.get('current_trend_fit', '-')}

"""
    else:
        md += "부활 가능성 4점 이상의 과거 제품이 없습니다.\n\n"

    md += """---

## 2. 신제품 아이디어 요청

위 데이터를 바탕으로 다음을 고려한 신제품 아이디어를 제안해주세요:

1. 부활 가능성 높은 과거 제품의 컨셉을 현대적으로 재해석
2. 독특한 특징을 가진 제품

각 아이디어에 대해 다음을 포함해주세요:
- 제품 컨셉
- 핵심 차별화 포인트
- 타겟 고객
- 예상 가격대
"""

    return md


def find_opportunities():
    """규칙 기반 기회 발굴"""
    high_potential = db.get_high_potential_legacy_products(min_score=4)

    opportunities = []

    # 부활 가능성 높은 과거 제품
    for l in high_potential:
        opportunities.append({
            'type': '부활 기회',
            'source': f"{l['brand']} - {l['name']}",
            'insight': l.get('unique_features', '-'),
            'category': l.get('category', '-')
        })

    return opportunities


def main():
    st.title("💡 신제품 제안")

    # 통계 요약
    stats = db.get_statistics()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("과거 특이 제품", f"{stats['legacy_count']}개")
    with col2:
        st.metric("부활 가능성 높음", f"{stats['high_potential_count']}개")

    st.divider()

    # 탭 구성
    tab_opportunity, tab_export, tab_saved = st.tabs([
        "🎯 기회 발굴", "📤 데이터 내보내기", "💾 저장된 제안"
    ])

    with tab_opportunity:
        st.subheader("규칙 기반 기회 발굴")
        st.caption("부활 가능성 높은 과거 제품에서 기회를 찾습니다.")

        opportunities = find_opportunities()

        if not opportunities:
            st.info("기회를 찾으려면 먼저 과거 특이 제품 데이터를 등록해주세요.")
        else:
            st.markdown(f"**{len(opportunities)}개 기회 발견**")

            for i, opp in enumerate(opportunities):
                with st.expander(f"🔄 [{opp['type']}] {opp['source']}"):
                    st.markdown(f"**카테고리:** {opp['category']}")
                    st.markdown(f"**인사이트:**")
                    st.write(opp['insight'])

    with tab_export:
        st.subheader("Claude용 데이터 내보내기")
        st.caption("수집된 데이터를 마크다운 형식으로 내보내 Claude에게 신제품 아이디어를 요청하세요.")

        if stats['legacy_count'] == 0:
            st.warning("내보낼 데이터가 없습니다. 먼저 과거 특이 제품을 등록해주세요.")
        else:
            if st.button("📋 마크다운 생성", width='stretch'):
                markdown_content = generate_export_markdown()
                st.session_state['export_markdown'] = markdown_content

            if 'export_markdown' in st.session_state:
                st.text_area(
                    "생성된 마크다운 (복사해서 Claude에게 붙여넣기)",
                    value=st.session_state['export_markdown'],
                    height=400
                )

                st.download_button(
                    "📥 마크다운 파일 다운로드",
                    data=st.session_state['export_markdown'],
                    file_name=f"cosmetics_research_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown"
                )

    with tab_saved:
        st.subheader("저장된 신제품 제안")

        # 새 제안 추가 폼
        with st.expander("➕ 새 제안 추가"):
            with st.form("new_proposal"):
                title = st.text_input("제안 제목 *")
                category = st.selectbox("카테고리", options=PRODUCT_CATEGORIES)
                concept = st.text_area("컨셉 설명", height=100)
                features = st.text_area("핵심 특징 (줄바꿈으로 구분)", height=100)
                notes = st.text_area("메모", height=80)

                if st.form_submit_button("💾 저장", width='stretch'):
                    if not title:
                        st.error("제목은 필수입니다.")
                    else:
                        db.add_proposal({
                            'title': title,
                            'category': category,
                            'concept_description': concept,
                            'key_features': [f.strip() for f in features.split('\n') if f.strip()],
                            'notes': notes
                        })
                        st.success("✅ 제안이 저장되었습니다!")
                        st.rerun()

        # 저장된 제안 목록
        proposals = db.get_proposals()

        if not proposals:
            st.info("저장된 제안이 없습니다.")
        else:
            for proposal in proposals:
                with st.expander(f"💡 {proposal['title']} ({proposal['category']})"):
                    if proposal.get('concept_description'):
                        st.markdown("**컨셉:**")
                        st.write(proposal['concept_description'])

                    if proposal.get('key_features'):
                        st.markdown("**핵심 특징:**")
                        for feature in proposal['key_features']:
                            st.markdown(f"- {feature}")

                    if proposal.get('notes'):
                        st.markdown("**메모:**")
                        st.write(proposal['notes'])

                    st.caption(f"생성일: {proposal.get('created_at', '-')}")

                    if st.button("🗑️ 삭제", key=f"del_prop_{proposal['id']}"):
                        db.delete_proposal(proposal['id'])
                        st.rerun()


if __name__ == "__main__":
    main()
