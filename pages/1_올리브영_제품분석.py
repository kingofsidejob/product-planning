"""
올리브영 베스트 상품 제품분석 페이지
- 브라우저 자동화 기반 수집
- goodsNo 기반 신규진입 상품 자동 감지
- 리뷰 기반 장단점 분석
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from config import DB_PATH
from database.db_manager import DatabaseManager

# Playwright 크롤러 import 시도
try:
    from modules.oliveyoung_browser_crawler import (
        run_crawler_sync,
        PLAYWRIGHT_AVAILABLE
    )
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# 리뷰 크롤러 import 시도
try:
    from modules.oliveyoung_review_crawler import (
        run_review_crawler_sync,
        PLAYWRIGHT_AVAILABLE as REVIEW_CRAWLER_AVAILABLE
    )
except ImportError:
    REVIEW_CRAWLER_AVAILABLE = False

# 리뷰 분석기 import
try:
    from modules.review_analyzer import quick_analyze, quick_marketing_analysis
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False

st.set_page_config(page_title="올리브영 제품분석", page_icon="🛒", layout="wide")


@st.cache_resource
def get_db():
    return DatabaseManager(DB_PATH)


db = get_db()


# 소분류 카테고리 목록 (대분류별 그룹핑)
CATEGORY_GROUPS = {
    "스킨케어": ["스킨/토너", "에센스/세럼/앰플", "크림", "아이크림", "로션", "올인원", "미스트/픽서", "페이스오일", "스킨케어세트"],
    "마스크팩": ["시트팩", "패드", "페이셜팩", "코팩", "패치"],
    "클렌징": ["클렌징폼/젤", "클렌징오일", "클렌징밤", "클렌징워터", "클렌징밀크", "필링&스크럽", "클렌징티슈/패드", "립&아이리무버"],
    "선케어": ["선크림", "선스틱", "선쿠션", "선스프레이/선패치", "태닝", "애프터선"],
    "메이크업-립": ["립틴트", "립스틱", "립라이너", "립밤", "립글로스"],
    "메이크업-베이스": ["쿠션", "파운데이션", "블러셔", "파우더/팩트", "컨실러", "프라이머/베이스", "쉐이딩", "하이라이터", "메이크업픽서", "BB/CC"],
    "메이크업-아이": ["아이섀도우", "아이라이너", "마스카라", "아이브로우"],
    "뷰티소품": ["브러시", "퍼프", "스펀지", "화장솜", "뷰러", "속눈썹/쌍꺼풀"],
    "더모 코스메틱": ["더모로션/크림", "더모에센스/세럼", "더모스킨/토너", "더모아이크림"],
    "맨즈케어": ["맨즈올인원", "맨즈토너/로션/크림", "면도기/면도날", "애프터쉐이브"],
    "헤어케어": ["샴푸", "린스/컨디셔너", "헤어팩/마스크", "헤어트리트먼트", "헤어오일/세럼", "염색/새치염색", "고데기", "드라이기"],
    "바디케어": ["바디로션", "바디크림", "바디오일", "바디워시", "바디스크럽", "입욕제", "립케어", "핸드크림", "핸드워시", "바디미스트", "제모크림", "데오드란트"],
    "향수/디퓨저": ["여성향수", "남성향수", "유니섹스향수", "미니/고체향수", "홈프래그런스"],
    "네일": ["일반네일", "젤네일", "네일팁/스티커", "네일케어"],
    "건강식품": ["비타민", "유산균", "영양제", "슬리밍/이너뷰티"],
    "푸드": ["식단관리", "과자/초콜릿", "생수/음료/커피"],
    "구강용품": ["칫솔", "치약", "애프터구강케어"],
    "여성/위생용품": ["생리/위생용품", "Y존케어"],
}

# 모든 소분류 카테고리 (크롤러에서 사용)
CATEGORIES = []
for cats in CATEGORY_GROUPS.values():
    CATEGORIES.extend(cats)


@st.dialog("📊 리뷰 분석 리포트", width="large")
def show_analysis_dialog(product_code: str, max_reviews: int = 5000):
    """분석 결과를 팝업 다이얼로그로 표시"""
    saved_analysis = db.get_review_analysis(product_code)

    if not saved_analysis:
        st.error("분석 데이터를 찾을 수 없습니다.")
        return

    # 제목
    st.markdown(f"### {saved_analysis.get('brand', '')} - {saved_analysis.get('name', '')}")

    # 재수집 버튼 (다이얼로그 내에서는 비활성화 - 상품 목록에서 사용)
    st.caption("💡 재수집은 상품 목록에서 '재수집' 버튼을 사용하세요")

    st.divider()

    # 요약 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 리뷰", f"{saved_analysis.get('total_reviews', 0)}개")
    with col2:
        st.metric("긍정 비율", f"{saved_analysis.get('positive_ratio', 0)}%")
    with col3:
        st.metric("긍정 리뷰", f"{saved_analysis.get('positive_count', 0)}개")
    with col4:
        st.metric("부정 리뷰", f"{saved_analysis.get('negative_count', 0)}개")

    st.info(f"📋 **요약**: {saved_analysis.get('summary', '')}")

    # 장단점
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ✅ 장점")
        for s in saved_analysis.get('strengths', []):
            st.markdown(f"- {s}")
        st.markdown("**빈출 긍정 키워드**")
        keywords = saved_analysis.get('top_positive_keywords', [])
        if keywords:
            st.markdown(", ".join([f"`{kw}` ({cnt})" for kw, cnt in keywords[:5]]))

    with col2:
        st.markdown("#### ⚠️ 단점")
        for w in saved_analysis.get('weaknesses', []):
            st.markdown(f"- {w}")
        st.markdown("**빈출 부정 키워드**")
        keywords = saved_analysis.get('top_negative_keywords', [])
        if keywords:
            st.markdown(", ".join([f"`{kw}` ({cnt})" for kw, cnt in keywords[:5]]))

    # 마케팅 분석
    st.divider()
    st.markdown("#### 🎯 마케팅 포인트")

    # 마케팅 포인트 요약 (장점 살리기 + 단점 보완)
    strengths_list = saved_analysis.get('strengths', [])
    weaknesses_list = saved_analysis.get('weaknesses', [])

    if strengths_list or weaknesses_list:
        st.markdown("##### 📋 마케팅 포인트 요약")

        summary_box = ""

        # 살려야 할 장점
        if strengths_list:
            top_strengths = strengths_list[:3]  # 상위 3개
            strength_keywords = [s.split(':')[0].strip() if ':' in s else s[:20] for s in top_strengths]
            summary_box += f"**✅ 강조할 포인트**: {', '.join(strength_keywords)}\n\n"
            summary_box += "→ 이 장점들은 소비자들이 가장 많이 언급한 긍정 요소입니다. 마케팅에서 적극 활용하세요.\n\n"

        # 보완해야 할 단점
        if weaknesses_list:
            top_weaknesses = weaknesses_list[:3]  # 상위 3개
            weakness_keywords = [w.split(':')[0].strip() if ':' in w else w[:20] for w in top_weaknesses]
            summary_box += f"**⚠️ 개선 필요**: {', '.join(weakness_keywords)}\n\n"
            summary_box += "→ 이 단점들은 소비자 불만이 집중된 부분입니다. 제품 개선 또는 마케팅 메시지로 보완을 고려하세요."

        st.info(summary_box)

        # USP 후보 표시 (DB에 저장된 데이터 사용, 없으면 샘플에서 추출)
        usp_candidates = saved_analysis.get('usp_candidates', [])
        viral_keyword_counts = saved_analysis.get('viral_keyword_counts', {})

        # 기존 데이터 호환: usp_candidates가 없으면 review_samples에서 추출
        if not usp_candidates:
            review_samples = saved_analysis.get('review_samples', [])
            if review_samples:
                try:
                    from modules.review_analyzer import extract_usp_from_reviews
                    usp_candidates = extract_usp_from_reviews(review_samples)
                except:
                    pass

        # 기존 데이터 호환: viral_keyword_counts가 없으면 review_samples에서 카운트
        if not viral_keyword_counts:
            review_samples = saved_analysis.get('review_samples', [])
            if review_samples:
                try:
                    from modules.usp_dictionary import get_usp_dictionary
                    usp_dict = get_usp_dictionary()
                    viral_keywords = usp_dict.get_keywords_by_category('viral')
                    all_text = ' '.join([r.get('content', '') for r in review_samples])
                    for vk in viral_keywords:
                        count = all_text.count(vk)
                        if count > 0:
                            viral_keyword_counts[vk] = count
                except:
                    pass

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

        if usp_candidates:
            st.markdown("**🎯 USP 후보** (제품의 특별한 점)")

            # 카테고리별로 문장과 키워드 수집 (중복 제거)
            by_category = {}
            seen_sentences = set()
            for usp in usp_candidates:
                cat = usp.get('category', 'other')
                sentence = usp.get('sentence', '')
                keywords = usp.get('trigger_words', [])

                # 문장 앞 20자 기준 중복 체크
                sent_key = sentence[:20]
                if sent_key in seen_sentences:
                    continue
                seen_sentences.add(sent_key)

                if cat not in by_category:
                    by_category[cat] = []

                # 전체 문장 표시 (잘리지 않게)
                if keywords and sentence:
                    keyword = keywords[0]
                    by_category[cat].append({
                        'keyword': keyword,
                        'context': sentence.strip()
                    })

            usp_items = []
            for cat, items in by_category.items():
                cat_name = category_names.get(cat, cat)
                for item in items[:2]:  # 카테고리당 최대 2개
                    usp_items.append({
                        'category': cat_name,
                        'keyword': item['keyword'],
                        'context': item['context']
                    })

            if usp_items:
                from modules.usp_dictionary import highlight_trigger_words
                for usp_item in usp_items:
                    highlighted_context = highlight_trigger_words(usp_item['context'])
                    st.markdown(
                        f'<div style="padding:10px;background-color:#d4edda;border-radius:5px;margin-bottom:5px">'
                        f'<b>[{usp_item["category"]}]</b> {usp_item["keyword"]}: "{highlighted_context}"</div>',
                        unsafe_allow_html=True
                    )
                st.caption("💡 리뷰에서 발견된 USP입니다. 신제품 기획 시 차별화 포인트로 참고하세요!")

        # 바이럴 키워드 언급 횟수 표시
        if viral_keyword_counts:
            counts_str = ', '.join([f"{kw} {cnt}회" for kw, cnt in sorted(viral_keyword_counts.items(), key=lambda x: -x[1])])
            st.info(f"📢 **바이럴 채널 언급**: {counts_str}")

        st.divider()

    # 유니크 포인트 (차별화 요소) - 전체 내용 표시
    unique_features = saved_analysis.get('unique_features', [])

    # unique_features가 없으면 marketing_suggestions에서 추출
    if not unique_features:
        suggestions = saved_analysis.get('marketing_suggestions', [])
        in_unique = False
        for s in suggestions:
            if "유니크 포인트" in s:
                in_unique = True
                continue
            if in_unique:
                if s.startswith("━━━"):
                    break
                if s.startswith("•"):
                    unique_features.append(s[1:].strip())

    if unique_features:
        st.markdown("**━━━ 🎯 유니크 포인트 (차별화 요소) ━━━**")
        # 트리거 키워드 하이라이트 함수 import
        from modules.usp_dictionary import highlight_trigger_words
        # 각 항목을 expander로 표시하여 전체 내용 확인 가능
        for i, feature in enumerate(unique_features, 1):
            # 미리보기 (앞 30자)
            preview = feature[:30] + "..." if len(feature) > 30 else feature
            with st.expander(f"📌 {i}. {preview}", expanded=True):
                # 트리거 키워드 하이라이트 (빨간 볼드)
                highlighted = highlight_trigger_words(feature)
                st.markdown(highlighted, unsafe_allow_html=True)
        st.divider()

    # 나머지 마케팅 제안 (유니크 포인트 섹션 제외)
    suggestions = saved_analysis.get('marketing_suggestions', [])
    if suggestions:
        in_unique_section = False
        for s in suggestions:
            if "유니크 포인트" in s:
                in_unique_section = True
                continue
            if in_unique_section:
                if s.startswith("━━━"):
                    in_unique_section = False
                    st.markdown(f"**{s}**")
                continue

            if s.startswith("━━━"):
                st.markdown(f"**{s}**")
            elif s.startswith("•"):
                st.markdown(f"- {s[1:].strip()}")
            else:
                st.markdown(s)

    # 추가 정보
    with st.expander("📊 상세 분석 데이터"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**빈출 키워드**")
            for kw, cnt in saved_analysis.get('repeated_keywords', [])[:5]:
                st.markdown(f"- `{kw}` ({cnt}회)")
        with col2:
            st.markdown("**경쟁제품 언급**")
            competitor_mentions = saved_analysis.get('competitor_mentions', {})
            if competitor_mentions:
                for brand, cnt in competitor_mentions.items():
                    st.markdown(f"- {brand}: {cnt}회")
            else:
                st.markdown("- 경쟁제품 언급 없음")

    # 리뷰 샘플
    samples = saved_analysis.get('review_samples', [])
    if samples:
        with st.expander(f"📖 리뷰 샘플 ({len(samples)}개)"):
            for i, r in enumerate(samples, 1):
                st.markdown(f"**{i}. {r.get('nickname', '익명')}** - {r.get('content', '')}")
                st.divider()

    st.caption(f"📅 분석일시: {saved_analysis.get('analyzed_at', '-')}")


def run_data_collection(category: str, limit: int):
    """데이터 수집 실행 및 DB 저장"""
    results = {
        'total': 0,
        'new': 0,
        'updated': 0,
        'products': []
    }

    # 기존 수집 이력 확인 (첫 수집인지 판단)
    crawl_history = db.get_crawl_history(limit=1)
    is_first_crawl = len(crawl_history) == 0

    # 기존 상품 코드 목록 (신규진입 판단용)
    existing_products = db.get_oliveyoung_products(category=category if category != "전체" else None)
    existing_codes = {p['product_code'] for p in existing_products if p.get('product_code')}

    # 수집 전 모든 상품의 is_new 플래그 초기화 (첫 수집이 아닐 때만)
    if not is_first_crawl:
        db.reset_new_flags()

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current, total):
        progress_bar.progress(min(current / total, 1.0))
        status_text.text(f"수집 중: {current}/{total}개")

    try:
        status_text.text(f"'{category}' 카테고리 수집 시작...")

        products = run_crawler_sync(
            category=category,
            limit=limit,
            headless=True,
            progress_callback=update_progress
        )

        for product in products:
            product_code = product.get('product_code')

            if product_code:
                # 첫 수집이 아니고, 기존에 없던 상품이면 is_new=True로 설정
                is_new_entry = (not is_first_crawl) and (product_code not in existing_codes)
                product['is_new'] = is_new_entry

                _, is_new = db.upsert_oliveyoung_product(product)

                if is_new:
                    results['new'] += 1
                else:
                    results['updated'] += 1

                results['products'].append({
                    **product,
                    'is_new_entry': is_new_entry
                })

        results['total'] = len(products)
        results['is_first_crawl'] = is_first_crawl
        db.add_crawl_history(category, results['total'], results['new'])

    except Exception as e:
        st.error(f"수집 실패: {e}")
        import traceback
        st.code(traceback.format_exc())

    progress_bar.progress(1.0)
    status_text.text("수집 완료!")

    return results


def run_review_analysis(product_code: str, max_reviews: int = 100, save_to_db: bool = True):
    """리뷰 수집 및 분석 (결과를 DB에 자동 저장)"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    st.caption("💡 수집을 중단하려면 브라우저를 새로고침하세요 (수집된 데이터는 저장되지 않습니다)")

    def update_progress(current, total, message):
        progress_bar.progress(current / total)
        status_text.text(message)

    try:
        # 리뷰 수집
        result = run_review_crawler_sync(
            product_id=product_code,
            max_reviews=max_reviews,
            headless=True,
            progress_callback=update_progress
        )

        reviews = result.get('reviews', [])
        product_info = result.get('product_info', {})

        if reviews:
            # 리뷰 분석
            analysis = quick_analyze(reviews)

            # 마케팅 포인트 분석
            marketing = quick_marketing_analysis(
                reviews,
                product_name=product_info.get('name', ''),
                brand=product_info.get('brand', '')
            )

            progress_bar.progress(1.0)
            status_text.text(f"분석 완료: {len(reviews)}개 리뷰")

            # 전체 리뷰에서 USP 후보 추출
            usp_candidates_to_save = []
            viral_counts_to_save = {}
            try:
                from modules.review_analyzer import extract_usp_from_reviews
                from modules.usp_dictionary import get_usp_dictionary

                # 전체 리뷰에서 USP 추출
                all_usp = extract_usp_from_reviews(reviews)

                # 중복 제거 후 저장 (카테고리당 최대 5개)
                seen = set()
                by_cat = {}
                for usp in all_usp:
                    cat = usp.get('category', 'other')
                    sent = usp.get('sentence', '')
                    key = sent[:30]
                    if key not in seen:
                        seen.add(key)
                        if cat not in by_cat:
                            by_cat[cat] = []
                        if len(by_cat[cat]) < 5:
                            by_cat[cat].append(usp)

                for cat, items in by_cat.items():
                    usp_candidates_to_save.extend(items)

                # 전체 리뷰에서 바이럴 키워드 카운트
                usp_dict = get_usp_dictionary()
                viral_keywords = usp_dict.get_keywords_by_category('viral')
                all_text = ' '.join([r.get('content', '') for r in reviews])
                for vk in viral_keywords:
                    count = all_text.count(vk)
                    if count > 0:
                        viral_counts_to_save[vk] = count
            except Exception as e:
                pass  # USP 추출 실패 시 무시

            # DB에 저장
            if save_to_db:
                analysis_data = {
                    'brand': product_info.get('brand', ''),
                    'name': product_info.get('name', ''),
                    'total_reviews': analysis['total'],
                    'positive_count': analysis['positive_count'],
                    'negative_count': analysis['negative_count'],
                    'positive_ratio': analysis['positive_ratio'],
                    'strengths': analysis['strengths'],
                    'weaknesses': analysis['weaknesses'],
                    'top_positive_keywords': analysis['top_positive'],
                    'top_negative_keywords': analysis['top_negative'],
                    'category_scores': analysis['category_scores'],
                    'summary': analysis['summary'],
                    'repeated_keywords': marketing.get('repeated_keywords', []),
                    'unique_features': marketing.get('unique_features', []),
                    'competitor_mentions': marketing.get('competitor_mentions', {}),
                    'comparison_insights': marketing.get('comparison_insights', []),
                    'marketing_suggestions': marketing.get('marketing_suggestions', []),
                    'review_samples': reviews[:10],  # 상위 10개 리뷰만 저장
                    'usp_candidates': usp_candidates_to_save,  # 전체 리뷰에서 추출한 USP
                    'viral_keyword_counts': viral_counts_to_save  # 전체 리뷰에서 카운트한 바이럴 키워드
                }
                db.save_review_analysis(product_code, analysis_data)

            return {
                'success': True,
                'product_info': product_info,
                'reviews': reviews,
                'analysis': analysis,
                'marketing': marketing
            }
        else:
            progress_bar.progress(1.0)
            status_text.text("리뷰를 찾을 수 없습니다.")
            return {'success': False, 'message': '리뷰를 찾을 수 없습니다.'}

    except Exception as e:
        progress_bar.progress(1.0)
        status_text.text(f"분석 실패: {e}")
        return {'success': False, 'message': str(e)}


def main():
    st.title("🛒 올리브영 제품분석")
    st.caption("올리브영 베스트 상품 수집, 신규 진입 감지, 리뷰 장단점 분석")

    # Playwright 설치 확인
    if not PLAYWRIGHT_AVAILABLE:
        st.error("""
        ⚠️ Playwright가 설치되지 않았습니다.
        ```
        pip install playwright
        playwright install chromium
        ```
        """)
        st.stop()

    # 탭 구성 (자주 사용하는 순서로 정렬)
    tab_crawl, tab_review, tab_viral, tab_new, tab_products, tab_history = st.tabs([
        "🔄 데이터 수집", "📝 리뷰 분석", "🔥 바이럴 아이템", "🆕 신규 진입", "📋 수집된 제품", "📊 수집 기록"
    ])

    # ===== 크롤링 실행 탭 =====
    with tab_crawl:
        st.subheader("데이터 수집 설정")

        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            selected_group = st.selectbox(
                "대분류",
                options=list(CATEGORY_GROUPS.keys()),
                index=0,
                help="대분류 카테고리 선택"
            )

        with col2:
            selected_category = st.selectbox(
                "소분류",
                options=CATEGORY_GROUPS[selected_group],
                index=0,
                help="수집할 소분류 카테고리"
            )

        with col3:
            limit = st.number_input(
                "수집 개수",
                min_value=10,
                max_value=500,
                value=100,
                step=10,
                help="1위부터 지정 개수까지 수집"
            )

        st.divider()

        col_btn1, col_btn2 = st.columns([1, 3])

        with col_btn1:
            start_crawl = st.button("🚀 수집 시작", type="primary", width='stretch')

        with col_btn2:
            st.caption("💡 수집 시 기존 상품코드(goodsNo)와 비교하여 신규 진입 상품을 자동 감지합니다.")

        if start_crawl:
            with st.spinner("브라우저 크롤러 실행 중..."):
                results = run_data_collection(selected_category, limit)

            if results['total'] > 0:
                is_first = results.get('is_first_crawl', False)

                # 요청 수보다 적게 수집된 경우 (카테고리 총 상품수가 적은 경우)
                category_limit_msg = ""
                if results['total'] < limit:
                    category_limit_msg = f"\n\n📌 **{selected_category}** 카테고리의 총 상품 수는 **{results['total']}개**입니다."

                if is_first:
                    st.success(f"""
                    ✅ **첫 수집 완료!**
                    - 총 수집: **{results['total']}개**
                    - 📝 DB 등록: **{results['new']}개**
                    - 🔄 기존 업데이트: **{results['updated']}개**

                    💡 다음 수집부터 신규 진입 상품이 감지됩니다.{category_limit_msg}
                    """)
                else:
                    new_entries = [p for p in results['products'] if p.get('is_new_entry')]
                    st.success(f"""
                    ✅ **수집 완료!**
                    - 총 수집: **{results['total']}개**
                    - 🆕 신규 진입: **{len(new_entries)}개**
                    - 🔄 기존 업데이트: **{results['updated']}개**{category_limit_msg}
                    """)

                new_entries = [p for p in results['products'] if p.get('is_new_entry')]
                if new_entries:
                    st.subheader("🆕 이번에 새로 진입한 상품")
                    new_df = pd.DataFrame([
                        {
                            '순위': p['rank'],
                            '브랜드': p['brand'],
                            '상품명': p['name'][:40] + '...' if len(p['name']) > 40 else p['name'],
                            '가격': f"{p['price']:,}원" if p.get('price') else '-',
                            '상품코드': p['product_code']
                        }
                        for p in new_entries[:10]
                    ])
                    st.dataframe(new_df, width='stretch', hide_index=True)

                    if len(new_entries) > 10:
                        st.caption(f"... 외 {len(new_entries) - 10}개 더")
            else:
                st.warning("수집된 상품이 없습니다.")

    # ===== 수집된 제품 탭 =====
    with tab_products:
        st.subheader("수집된 올리브영 제품")

        col1, col2 = st.columns([1, 1])
        with col1:
            products_filter_group = st.selectbox(
                "대분류",
                options=["전체"] + list(CATEGORY_GROUPS.keys()),
                key="products_filter_group"
            )

        with col2:
            # 대분류 선택에 따라 소분류 옵션 변경
            if products_filter_group == "전체":
                products_category_options = ["전체"] + CATEGORIES
            else:
                products_category_options = ["전체"] + CATEGORY_GROUPS[products_filter_group]

            products_filter_category = st.selectbox(
                "소분류",
                options=products_category_options,
                key="products_filter_category"
            )

        # 대분류/소분류 필터 적용
        if products_filter_category != "전체":
            # 소분류가 선택된 경우
            products = db.get_oliveyoung_products(category=products_filter_category)
        elif products_filter_group != "전체":
            # 대분류만 선택된 경우 - 해당 대분류의 모든 소분류 상품 조회
            group_categories = CATEGORY_GROUPS[products_filter_group]
            all_products = db.get_oliveyoung_products(category=None)
            products = [p for p in all_products if p.get('category') in group_categories]
        else:
            # 전체 선택
            products = db.get_oliveyoung_products(category=None)

        if products:
            st.markdown(f"**총 {len(products)}개 제품**")

            df = pd.DataFrame([
                {
                    '순위': p.get('best_rank', '-'),
                    '브랜드': p['brand'],
                    '제품명': p['name'][:35] + '...' if len(p['name']) > 35 else p['name'],
                    '카테고리': p.get('category', '-'),
                    '가격': f"{p['price']:,}원" if p.get('price') else '-',
                    '상품코드': p.get('product_code', '-')
                }
                for p in products[:100]
            ])
            st.dataframe(df, width='stretch', hide_index=True)

            if len(products) > 100:
                st.caption(f"상위 100개만 표시 (전체 {len(products)}개)")
        else:
            st.info("수집된 제품이 없습니다. '데이터 수집' 탭에서 수집을 시작하세요.")

    # ===== 신규 진입 탭 =====
    with tab_new:
        st.subheader("🆕 신규 진입 제품")
        st.caption("최근 7일 내 베스트 100에 새로 진입한 제품입니다.")

        # 대분류/소분류 필터
        col1, col2 = st.columns([1, 1])
        with col1:
            new_filter_group = st.selectbox(
                "대분류",
                options=["전체"] + list(CATEGORY_GROUPS.keys()),
                key="new_filter_group"
            )

        with col2:
            if new_filter_group == "전체":
                new_category_options = ["전체"] + CATEGORIES
            else:
                new_category_options = ["전체"] + CATEGORY_GROUPS[new_filter_group]

            new_filter_category = st.selectbox(
                "소분류",
                options=new_category_options,
                key="new_filter_category"
            )

        # 신규 진입 상품 조회 및 필터 적용
        all_new_products = db.get_new_oliveyoung_entries()

        if new_filter_category != "전체":
            new_products = [p for p in all_new_products if p.get('category') == new_filter_category]
        elif new_filter_group != "전체":
            group_categories = CATEGORY_GROUPS[new_filter_group]
            new_products = [p for p in all_new_products if p.get('category') in group_categories]
        else:
            new_products = all_new_products

        if new_products:
            st.success(f"🎉 {len(new_products)}개의 신규 진입 제품 발견!")

            for product in new_products:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(f"**{product['brand']}** - {product['name'][:50]}...")
                        st.caption(f"{product.get('category', '-')} · 베스트 {product.get('best_rank', '-')}위 · 코드: `{product.get('product_code', '-')}`")
                        if product.get('price'):
                            st.markdown(f"💰 {product['price']:,}원")

                    with col2:
                        if product.get('image_url'):
                            st.image(product['image_url'], width=80)
        else:
            st.info("신규 진입 제품이 없습니다.")

    # ===== 리뷰 분석 탭 =====
    with tab_review:
        st.subheader("📝 리뷰 장단점 분석")
        st.caption("수집된 상품의 리뷰를 수집하고 장단점을 자동으로 분석합니다. 분석 결과는 DB에 저장됩니다.")

        if not REVIEW_CRAWLER_AVAILABLE or not ANALYZER_AVAILABLE:
            st.warning("리뷰 분석 모듈이 로드되지 않았습니다.")
        else:
            # 세션 상태 초기화
            if 'selected_products' not in st.session_state:
                st.session_state.selected_products = set()
            if 'batch_crawling' not in st.session_state:
                st.session_state.batch_crawling = False

            # 설정
            col_group, col_category, col_setting = st.columns([1, 1, 1])

            with col_group:
                review_filter_group = st.selectbox(
                    "대분류",
                    options=["전체"] + list(CATEGORY_GROUPS.keys()),
                    key="review_filter_group"
                )

            with col_category:
                # 대분류 선택에 따라 소분류 옵션 변경
                if review_filter_group == "전체":
                    category_options = ["전체"] + CATEGORIES
                else:
                    category_options = ["전체"] + CATEGORY_GROUPS[review_filter_group]

                review_filter_category = st.selectbox(
                    "소분류",
                    options=category_options,
                    key="review_filter_category"
                )

            with col_setting:
                max_reviews = st.number_input(
                    "리뷰 수집 개수",
                    min_value=10,
                    max_value=50000,
                    value=500,
                    step=100,
                    help="상품당 수집할 최대 리뷰 개수 (기본 500개)"
                )

            # 수동 상품코드 입력
            with st.expander("📝 상품코드 직접 입력하여 분석"):
                col_input, col_btn = st.columns([3, 1])
                with col_input:
                    manual_code = st.text_input(
                        "올리브영 상품코드",
                        placeholder="A000000243499",
                        help="올리브영 상품 URL의 goodsNo 값 (A로 시작)",
                        label_visibility="collapsed"
                    )
                with col_btn:
                    if st.button("🔍 분석", width='stretch', disabled=not manual_code):
                        if manual_code:
                            with st.spinner(f"'{manual_code}' 분석 중..."):
                                result = run_review_analysis(manual_code, max_reviews)
                            if result.get('success'):
                                st.success(f"✅ 분석 완료! 아래 상품 목록에서 '보기'를 클릭하세요.")
                                st.rerun()
                            else:
                                st.error(f"분석 실패: {result.get('message', '알 수 없는 오류')}")

            st.divider()

            # 수집된 상품 목록 - 대분류/소분류 필터 적용
            if review_filter_category != "전체":
                # 소분류가 선택된 경우
                review_products = db.get_oliveyoung_products(category=review_filter_category)
            elif review_filter_group != "전체":
                # 대분류만 선택된 경우 - 해당 대분류의 모든 소분류 상품 조회
                group_categories = CATEGORY_GROUPS[review_filter_group]
                all_products = db.get_oliveyoung_products(category=None)
                review_products = [p for p in all_products if p.get('category') in group_categories]
            else:
                # 전체 선택
                review_products = db.get_oliveyoung_products(category=None)

            # 분석 완료된 상품 코드, 날짜, 리뷰 개수 목록
            analyzed_codes = db.get_analyzed_product_codes()
            analyzed_dates = db.get_analyzed_product_dates()
            analyzed_review_counts = db.get_analyzed_product_review_counts()

            if review_products:
                analyzed_count = sum(1 for p in review_products if p.get('product_code') in analyzed_codes)
                st.markdown(f"**총 {len(review_products)}개 상품** (분석완료: {analyzed_count}개)")

                st.divider()

                # 일괄 수집/삭제 버튼
                col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 1])

                with col_btn1:
                    if st.button("✅ 전체 선택", width='stretch'):
                        # 미분석 상품들의 코드 목록
                        unanalyzed_codes = {
                            p['product_code'] for p in review_products[:500]
                            if p.get('product_code') and p['product_code'] not in analyzed_codes
                        }
                        st.session_state.selected_products = unanalyzed_codes
                        # 체크박스 상태도 동기화
                        for code in unanalyzed_codes:
                            st.session_state[f"check_{code}"] = True
                        st.rerun()

                with col_btn2:
                    if st.button("❌ 선택 해제", width='stretch'):
                        # 체크박스 상태 초기화
                        for code in st.session_state.selected_products:
                            if f"check_{code}" in st.session_state:
                                st.session_state[f"check_{code}"] = False
                        st.session_state.selected_products = set()
                        st.rerun()

                with col_btn3:
                    selected_count = len(st.session_state.selected_products)
                    if st.button(
                        f"🚀 선택한 {selected_count}개 수집",
                        type="primary",
                        disabled=selected_count == 0,
                        width='stretch'
                    ):
                        st.session_state.batch_crawling = True
                        st.rerun()

                with col_btn4:
                    if st.button(
                        f"🗑️ 선택한 {selected_count}개 삭제",
                        disabled=selected_count == 0,
                        width='stretch'
                    ):
                        for product_code in st.session_state.selected_products:
                            db.delete_oliveyoung_product(product_code)
                        st.session_state.selected_products = set()
                        st.success(f"✅ {selected_count}개 상품이 삭제되었습니다.")
                        st.rerun()

                # 일괄 수집 실행
                if st.session_state.batch_crawling and st.session_state.selected_products:
                    st.divider()
                    st.markdown("### 🔄 일괄 수집 진행 중...")

                    products_to_crawl = list(st.session_state.selected_products)
                    total = len(products_to_crawl)
                    progress_bar = st.progress(0)
                    status_container = st.empty()

                    success_count = 0
                    fail_count = 0

                    for i, product_code in enumerate(products_to_crawl):
                        status_container.markdown(f"**[{i+1}/{total}]** `{product_code}` 분석 중...")

                        try:
                            result = run_review_analysis(product_code, max_reviews)
                            if result.get('success'):
                                success_count += 1
                            else:
                                fail_count += 1
                        except Exception as e:
                            fail_count += 1
                            st.warning(f"`{product_code}` 실패: {e}")

                        progress_bar.progress((i + 1) / total)

                    st.session_state.batch_crawling = False
                    st.session_state.selected_products = set()
                    status_container.empty()
                    st.success(f"✅ 일괄 수집 완료! 성공: {success_count}개, 실패: {fail_count}개")
                    st.rerun()

                st.divider()

                # 상품 목록 (체크박스 포함)
                col_title, col_search = st.columns([2, 1])
                with col_title:
                    st.markdown("### 📋 상품 목록")
                with col_search:
                    search_query = st.text_input(
                        "🔍 상품 검색",
                        placeholder="브랜드명 또는 상품명 검색...",
                        label_visibility="collapsed",
                        key="product_search"
                    )

                # 검색어로 필터링
                filtered_products = review_products
                if search_query:
                    search_terms = search_query.strip().lower().split()
                    filtered_products = [
                        p for p in review_products
                        if all(
                            term in p.get('name', '').lower() or term in p.get('brand', '').lower()
                            for term in search_terms
                        )
                    ]
                    st.caption(f"🔎 '{search_query}' 검색 결과: {len(filtered_products)}개")

                for product in filtered_products[:500]:
                    product_code = product.get('product_code', '')
                    is_analyzed = product_code in analyzed_codes
                    is_selected = product_code in st.session_state.selected_products

                    with st.container(border=True):
                        col_check, col_info, col_img, col_action = st.columns([0.5, 4, 1, 1.5])

                        with col_check:
                            if not is_analyzed:
                                # 체크박스 키가 없으면 초기화
                                checkbox_key = f"check_{product_code}"
                                if checkbox_key not in st.session_state:
                                    st.session_state[checkbox_key] = is_selected

                                # 체크박스 표시 및 상태 동기화
                                checked = st.checkbox("선택", key=checkbox_key, label_visibility="collapsed")

                                # 체크박스 상태에 따라 selected_products 업데이트
                                if checked and product_code not in st.session_state.selected_products:
                                    st.session_state.selected_products.add(product_code)
                                elif not checked and product_code in st.session_state.selected_products:
                                    st.session_state.selected_products.discard(product_code)
                            else:
                                st.markdown("✅")

                        with col_info:
                            st.markdown(f"**{product['brand']}** - {product['name']}")
                            if is_analyzed:
                                # 분석 날짜 및 리뷰 개수 표시
                                analyzed_at = analyzed_dates.get(product_code, '')
                                review_count = analyzed_review_counts.get(product_code, 0)
                                if analyzed_at:
                                    # 날짜 포맷: 2026-01-07 12:34:56 -> 2026.01.07
                                    date_str = analyzed_at[:10].replace('-', '.')
                                    st.caption(f"✅ 분석완료 · 베스트 {product.get('best_rank', '-')}위 · `{product_code}` · 📅 {date_str} ({review_count}개 리뷰)")
                                else:
                                    st.caption(f"✅ 분석완료 · 베스트 {product.get('best_rank', '-')}위 · `{product_code}` ({review_count}개 리뷰)")
                            else:
                                st.caption(f"⏳ 미분석 · 베스트 {product.get('best_rank', '-')}위 · `{product_code}`")

                        with col_img:
                            if product.get('image_url'):
                                st.image(product['image_url'], width=50)

                        with col_action:
                            if is_analyzed:
                                if st.button("📊 보기", key=f"view_{product_code}", width='stretch'):
                                    show_analysis_dialog(product_code, max_reviews)
                                if st.button("🔄 재수집", key=f"recrawl_{product_code}", width='stretch'):
                                    with st.spinner(f"'{product['name'][:20]}...' 재수집 중..."):
                                        run_review_analysis(product_code, max_reviews)
                                    st.rerun()
                            else:
                                if st.button("🔍 수집", key=f"crawl_{product_code}", width='stretch'):
                                    with st.spinner(f"'{product['name'][:20]}...' 분석 중..."):
                                        run_review_analysis(product_code, max_reviews)
                                    st.rerun()

                if len(review_products) > 100:
                    st.caption(f"상위 100개만 표시 (전체 {len(review_products)}개)")
            else:
                st.info("수집된 제품이 없습니다. '데이터 수집' 탭에서 먼저 상품을 수집하세요.")

    # ===== 바이럴 아이템 탭 =====
    with tab_viral:
        st.subheader("🔥 바이럴 아이템 랭킹")
        st.caption("SNS/바이럴 채널에서 언급된 제품을 바이럴 비율(%) 순으로 정렬합니다.")

        # DB에서 바이럴 키워드 카운트가 있는 제품 조회
        viral_products = []
        try:
            import json as json_lib
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT product_code, brand, name, total_reviews, viral_keyword_counts, analyzed_at
                    FROM review_analysis
                    WHERE viral_keyword_counts IS NOT NULL AND viral_keyword_counts != '{}' AND viral_keyword_counts != 'null'
                """)
                for row in cursor.fetchall():
                    try:
                        counts = json_lib.loads(row['viral_keyword_counts']) if row['viral_keyword_counts'] else {}
                        if counts:
                            total_viral = sum(counts.values())
                            total_reviews = row['total_reviews'] or 1  # 0 나누기 방지
                            viral_ratio = (total_viral / total_reviews) * 100
                            viral_products.append({
                                'product_code': row['product_code'],
                                'brand': row['brand'],
                                'name': row['name'],
                                'total_reviews': total_reviews,
                                'viral_counts': counts,
                                'total_viral': total_viral,
                                'viral_ratio': viral_ratio,
                                'analyzed_at': row['analyzed_at']
                            })
                    except:
                        pass
        except Exception as e:
            st.error(f"데이터 조회 오류: {e}")

        # 바이럴 비율(%)로 정렬 (높은 순)
        viral_products.sort(key=lambda x: x['viral_ratio'], reverse=True)

        if viral_products:
            st.success(f"🎯 바이럴 언급이 있는 제품: **{len(viral_products)}개**")

            # 상위 100개만 표시
            for rank, product in enumerate(viral_products[:100], 1):
                with st.container(border=True):
                    col_rank, col_info, col_viral = st.columns([0.5, 3, 2])

                    with col_rank:
                        st.markdown(f"### {rank}")

                    with col_info:
                        st.markdown(f"**{product['brand']}** - {product['name'][:50]}{'...' if len(product['name']) > 50 else ''}")
                        analyzed_date = product['analyzed_at'][:10].replace('-', '.') if product['analyzed_at'] else '-'
                        st.caption(f"📊 리뷰 {product['total_reviews']}개 · 📅 {analyzed_date} · `{product['product_code']}`")
                        if st.button("📊 보기", key=f"viral_view_{product['product_code']}"):
                            show_analysis_dialog(product['product_code'])

                    with col_viral:
                        # 바이럴 비율 및 상세 정보
                        counts_str = ', '.join([f"**{kw}** {cnt}회" for kw, cnt in sorted(product['viral_counts'].items(), key=lambda x: -x[1])])
                        st.info(f"📢 총 **{product['total_viral']}회** 언급 (**{product['viral_ratio']:.1f}%**)\n\n리뷰 {product['total_reviews']:,}개 중 {product['total_viral']}개\n\n{counts_str}")

            if len(viral_products) > 100:
                st.caption(f"상위 100개만 표시 (전체 {len(viral_products)}개)")
        else:
            st.info("바이럴 언급이 있는 제품이 없습니다. 리뷰 분석 탭에서 제품을 수집/재수집하세요.")

        st.divider()
        st.caption("💡 바이럴 키워드: 인스타, 유튜브, 틱톡, 숏츠, 릴스, 와디즈, 공구, 공동구매 등")

    # ===== 히스토리 탭 =====
    with tab_history:
        st.subheader("수집 기록")

        history = db.get_crawl_history(limit=20)

        if history:
            df = pd.DataFrame([
                {
                    '수집일시': h['crawled_at'],
                    '카테고리': h['category'],
                    '수집 수': h['products_count'],
                    '신규 수': h['new_products_count']
                }
                for h in history
            ])
            st.dataframe(df, width='stretch', hide_index=True)

            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 수집 횟수", f"{len(history)}회")
            with col2:
                st.metric("총 수집 상품", f"{sum(h['products_count'] for h in history):,}개")
            with col3:
                st.metric("총 신규 발견", f"{sum(h['new_products_count'] for h in history):,}개")
        else:
            st.info("수집 기록이 없습니다.")


if __name__ == "__main__":
    main()
