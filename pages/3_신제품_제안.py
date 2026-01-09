"""
신제품 제안 페이지
"""
import streamlit as st
import pandas as pd
import re
from datetime import datetime
from collections import Counter

from config import DB_PATH, PRODUCT_CATEGORIES, REVIVAL_POTENTIAL_LABELS
from database.db_manager import DatabaseManager

st.set_page_config(page_title="신제품 제안", page_icon="💡", layout="wide")

@st.cache_resource
def get_db():
    return DatabaseManager(DB_PATH)

db = get_db()


def parse_goodsno_input(text: str) -> list:
    """GOODSNO 입력 파싱 (줄바꿈, 콤마, 공백 구분)"""
    # 줄바꿈, 콤마, 공백을 구분자로 분리
    codes = re.split(r'[\n,\s]+', text.strip())
    # 빈 문자열 제거 및 중복 제거
    return list(dict.fromkeys([c.strip() for c in codes if c.strip()]))


def generate_oliveyoung_prompt(analyses: list) -> str:
    """올리브영 분석 데이터 기반 Claude/Gemini/GPT 프롬프트 생성 (개선된 버전)"""
    if not analyses:
        return ""

    # 제품 정보 수집
    products_info = []
    all_strengths = []  # (키워드, 원문) 튜플
    all_weaknesses = []  # (키워드, 원문) 튜플
    all_usp = []
    all_review_samples = []
    categories = set()
    prices = []

    for a in analyses:
        product_code = a.get('product_code', '')

        products_info.append({
            'code': product_code,
            'brand': a.get('brand', ''),
            'name': a.get('name', ''),
            'total_reviews': a.get('total_reviews', 0),
            'positive_ratio': a.get('positive_ratio', 0)
        })

        # 장점 수집 (키워드와 원문 함께)
        for s in a.get('strengths', []):
            if ':' in s:
                kw = s.split(':')[0].strip()
                detail = s.split(':', 1)[1].strip() if ':' in s else s
            else:
                kw = s[:15].strip()
                detail = s
            all_strengths.append((kw, detail))

        # 단점 수집 (키워드와 원문 함께)
        for w in a.get('weaknesses', []):
            if ':' in w:
                kw = w.split(':')[0].strip()
                detail = w.split(':', 1)[1].strip() if ':' in w else w
            else:
                kw = w[:15].strip()
                detail = w
            all_weaknesses.append((kw, detail))

        # USP 수집
        for usp in a.get('usp_candidates', []):
            cat = usp.get('category', 'other')
            sentence = usp.get('sentence', '')
            keywords = usp.get('trigger_words', [])
            if sentence and keywords:
                all_usp.append({
                    'category': cat,
                    'keyword': keywords[0] if keywords else '',
                    'sentence': sentence
                })

        # 리뷰 샘플 수집
        for r in a.get('review_samples', [])[:3]:
            all_review_samples.append(r.get('content', '')[:100])

        # 올리브영 제품 정보에서 카테고리, 가격 가져오기
        if product_code:
            oliveyoung_products = db.get_oliveyoung_products()
            for p in oliveyoung_products:
                if p.get('product_code') == product_code:
                    if p.get('category'):
                        categories.add(p['category'])
                    if p.get('price'):
                        prices.append(p['price'])
                    break

    # 장점/단점 빈도 분석
    def get_freq_with_samples(items):
        """빈도 분석 + 대표 리뷰 추출"""
        keyword_counts = Counter([item[0] for item in items])
        keyword_samples = {}
        for kw, detail in items:
            if kw not in keyword_samples:
                keyword_samples[kw] = detail
        result = []
        for kw, cnt in keyword_counts.most_common(8):
            result.append({
                'keyword': kw,
                'count': cnt,
                'sample': keyword_samples.get(kw, '')[:80]
            })
        return result

    strength_data = get_freq_with_samples(all_strengths)
    weakness_data = get_freq_with_samples(all_weaknesses)

    # USP 카테고리별 정리
    usp_by_cat = {}
    for usp in all_usp:
        cat = usp['category']
        if cat not in usp_by_cat:
            usp_by_cat[cat] = []
        existing_keywords = [u['keyword'] for u in usp_by_cat[cat]]
        if usp['keyword'] not in existing_keywords and len(usp_by_cat[cat]) < 2:
            usp_by_cat[cat].append(usp)

    # 카테고리 한글명 매핑
    category_names = {
        'visual': '시각적 특징',
        'tactile': '촉감/제형',
        'action': '사용 시 변화',
        'olfactory': '향 특징',
        'design': '디자인/휴대성',
        'reaction': '소비자 반응',
        'viral': '바이럴/SNS'
    }

    # 가격 정보
    price_info = ""
    if prices:
        avg_price = int(sum(prices) / len(prices))
        min_price = min(prices)
        max_price = max(prices)
        price_info = f"- 경쟁 제품 가격대: {min_price:,}원 ~ {max_price:,}원\n- 평균가: {avg_price:,}원"
    else:
        price_info = "- 가격 정보 없음"

    # 카테고리 문자열
    category_str = ', '.join(categories) if categories else '미분류'

    # === 프롬프트 생성 ===
    md = f"""# 역할
당신은 올리브영 베스트셀러를 기획하는 **화장품 신제품 기획자**입니다.
아래 리뷰 분석 데이터를 바탕으로 실제 출시 가능한 신제품 아이디어를 제안해주세요.

---

# 분석 데이터

## 카테고리
**{category_str}**

## 분석 제품 ({len(analyses)}개)
"""

    for i, p in enumerate(products_info, 1):
        md += f"{i}. [{p['brand']}] {p['name']} - 리뷰 {p['total_reviews']:,}개, 긍정률 {p['positive_ratio']}%\n"

    md += f"""
## 소비자가 좋아하는 점 (장점)
"""
    if strength_data:
        for i, s in enumerate(strength_data[:6], 1):
            md += f"{i}. **{s['keyword']}** ({s['count']}회 언급)\n"
            if s['sample']:
                md += f"   - 대표 리뷰: \"{s['sample']}\"\n"
    else:
        md += "- 분석된 장점이 없습니다.\n"

    md += f"""
## 소비자 불만 (단점 = 개선 기회)
"""
    if weakness_data:
        for i, w in enumerate(weakness_data[:6], 1):
            md += f"{i}. **{w['keyword']}** ({w['count']}회 언급)\n"
            if w['sample']:
                md += f"   - 대표 리뷰: \"{w['sample']}\"\n"
    else:
        md += "- 분석된 단점이 없습니다.\n"

    md += f"""
## 차별화 포인트 (USP 후보)
"""
    if usp_by_cat:
        for cat, items in usp_by_cat.items():
            cat_name = category_names.get(cat, cat)
            for item in items:
                md += f"- [{cat_name}] **{item['keyword']}**: \"{item['sentence'][:60]}...\"\n"
    else:
        md += "- USP 후보가 없습니다.\n"

    md += f"""
## 가격 정보
{price_info}

---

# 신제품 아이디어 요청

위 분석을 바탕으로 다음을 제안해주세요:

1. **신제품 컨셉**: 공통 장점을 살리고 단점을 보완한 제품 아이디어
2. **컨셉명**: 제품의 핵심 가치를 담은 브랜드명/제품명 (예: 아쿠아락 제로, 글로우드롭 등)
3. **핵심 USP**: 경쟁 제품과 차별화할 수 있는 포인트
4. **타겟 고객층**: 이 제품이 가장 어필할 고객층
5. **마케팅 포인트**: 소비자에게 강조할 메시지
6. **아이디어 3개**: 위 내용을 바탕으로 신제품 아이디어 3개를 제안해주세요

## 컨셉명 작성 가이드
- 영문+한글 조합 또는 순한글 모두 가능
- 제품의 핵심 효능이나 특징을 직관적으로 표현
- 올리브영 감성에 맞는 트렌디한 네이밍
- 예시: "아쿠아락 제로", "시카밤 리페어", "글로우 부스터" 등
- **영문 스타일**: Aqualock Zero, Glow Drop, Cica Calm 등
- **한글 스타일**: 물광젤리, 촉촉담, 진정수 등
- **혼합 스타일**: 수분락 제로, 글로우 물광팩 등

각 아이디어는 구체적으로 작성해주세요.
"""

    return md


def render_oliveyoung_tab():
    """올리브영 기반 제안 탭 렌더링"""
    st.subheader("올리브영 제품 분석 기반 신제품 아이디어")
    st.caption("분석 완료된 GOODSNO를 입력하면 장단점, USP, 마케팅포인트를 분석하여 신제품 아이디어를 자동 생성합니다.")

    # 분석 완료된 제품 수 표시
    analyzed_codes = db.get_analyzed_product_codes()
    st.info(f"현재 분석 완료된 제품: **{len(analyzed_codes)}개**")

    # GOODSNO 입력
    st.markdown("**GOODSNO 입력** (줄바꿈, 콤마, 공백으로 구분)")

    goodsno_input = st.text_area(
        "GOODSNO 입력",
        placeholder="A000000243499\nA000000123456\nA000000789012",
        height=150,
        help="올리브영 상품코드(GOODSNO)를 입력하세요. 여러 개를 입력할 수 있습니다.",
        label_visibility="collapsed"
    )

    st.divider()

    # 프롬프트 생성 버튼 (항상 표시)
    if st.button("📋 Claude/Gemini/GPT 프롬프트 생성", type="primary", use_container_width=True,
                help="Claude 또는 GPT에 붙여넣을 프롬프트 생성"):
        # 버튼 클릭 시 입력값 파싱
        input_codes = parse_goodsno_input(goodsno_input) if goodsno_input else []

        if not input_codes:
            st.error("GOODSNO를 입력해주세요.")
        else:
            # 분석 완료/미완료 분류
            valid_codes = [c for c in input_codes if c in analyzed_codes]
            invalid_codes = [c for c in input_codes if c not in analyzed_codes]

            if invalid_codes:
                st.warning(f"미분석 GOODSNO {len(invalid_codes)}개는 제외됩니다: {', '.join(invalid_codes[:3])}{'...' if len(invalid_codes) > 3 else ''}")

            if not valid_codes:
                st.error("분석 완료된 GOODSNO가 없습니다. 올리브영 제품분석에서 먼저 리뷰를 분석해주세요.")
            else:
                with st.spinner(f"{len(valid_codes)}개 제품 프롬프트 생성 중..."):
                    analyses = db.get_review_analyses_by_codes(valid_codes)

                if analyses:
                    prompt = generate_oliveyoung_prompt(analyses)
                    st.session_state['oliveyoung_prompt'] = prompt
                    st.success(f"✅ {len(analyses)}개 제품 기반 프롬프트 생성 완료!")
                else:
                    st.error("분석 데이터를 가져오지 못했습니다.")

    # === 생성된 프롬프트 표시 ===
    if 'oliveyoung_prompt' in st.session_state and st.session_state['oliveyoung_prompt']:
        prompt = st.session_state['oliveyoung_prompt']

        st.divider()
        st.markdown("## 📋 Claude/Gemini/GPT 프롬프트")
        st.caption("오른쪽 상단 📋 버튼을 클릭하면 복사됩니다. → Claude/GPT에 붙여넣기 (Ctrl+V)")

        # 프롬프트 표시 (st.code는 복사 버튼 내장)
        st.code(prompt, language="markdown")

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

    col1, col2, col3 = st.columns(3)
    with col1:
        # 분석 완료된 올리브영 제품 수
        analyzed_count = len(db.get_analyzed_product_codes())
        st.metric("분석 완료 제품", f"{analyzed_count}개")
    with col2:
        st.metric("과거 특이 제품", f"{stats['legacy_count']}개")
    with col3:
        st.metric("부활 가능성 높음", f"{stats['high_potential_count']}개")

    st.divider()

    # 탭 구성 (올리브영 기반 제안을 첫 번째로)
    tab_oliveyoung, tab_opportunity, tab_export, tab_saved = st.tabs([
        "🛒 올리브영 기반 제안", "🎯 기회 발굴", "📤 데이터 내보내기", "💾 저장된 제안"
    ])

    with tab_oliveyoung:
        render_oliveyoung_tab()

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
