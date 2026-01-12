"""
신제품 아이디어 생성 페이지
"""
import streamlit as st
import pandas as pd
import re
from datetime import datetime
from collections import Counter
from pathlib import Path

from config import DB_PATH, PRODUCT_CATEGORIES, REVIVAL_POTENTIAL_LABELS
from database.db_manager import DatabaseManager

# 리포트 디렉토리 경로 (2_리서치.py와 동일)
REPORTS_DIR = Path(__file__).parent.parent / "reports"

# AI 모델 설정
# Note: Sonnet 4.5, Haiku 4.5는 아직 API 미지원 (웹에서만 사용 가능)
AI_MODELS = {
    "Claude Opus 4.5 (최고 품질)": {
        "provider": "anthropic",
        "id": "claude-opus-4-5-20251101",
        "cost": "~₩300원",
        "thinking_budget": 10000
    },
    "Claude Sonnet 4 (균형)": {
        "provider": "anthropic",
        "id": "claude-sonnet-4-20250514",
        "cost": "~₩40원",
        "thinking_budget": 5000
    },
    "Claude Haiku 3.5 (빠름)": {
        "provider": "anthropic",
        "id": "claude-3-5-haiku-20241022",
        "cost": "~₩3원",
        "thinking_budget": 0
    },
    "GPT-5.2 (OpenAI 최신)": {
        "provider": "openai",
        "id": "gpt-5.2",
        "cost": "~₩50원"
    },
    "GPT-4o (균형)": {
        "provider": "openai",
        "id": "gpt-4o",
        "cost": "~₩30원"
    }
}

# 시스템 프롬프트 (출력 품질 향상)
SYSTEM_PROMPT = """당신은 올리브영 베스트셀러를 기획하는 **시니어 화장품 신제품 기획자**입니다.

## 역할
- 10년 이상의 화장품 기획 경력
- 올리브영 트렌드와 MZ세대 소비 패턴에 정통
- 실제 출시 가능한 구체적인 제품 아이디어 제안
- **최신 시장 리서치 데이터를 반영한 트렌드 분석**

## 출력 스타일
- 각 아이디어는 **구체적이고 실행 가능**하게 작성
- 컨셉명은 **트렌디하고 기억에 남는** 네이밍
- USP는 **경쟁사와 명확히 차별화**되는 포인트
- 마케팅 포인트는 **실제 광고 카피로 사용 가능**한 수준
- 데이터에 기반한 **논리적 근거** 제시
- **리서치 데이터의 최신 트렌드를 반영**

## 출력 형식 (반드시 준수)
각 신제품 아이디어는 다음 형식을 엄격히 따르세요:

💡 신제품 아이디어 #N

컨셉명: [제품명] ([영문명])

🎯 신제품 컨셉
"[핵심 메시지를 인용부호로 강조]"
[상세 설명 2-3문장]

📦 제품 상세
- 형태: [내용]
- 제형: [내용]
- 용량/가격: [내용]
- 핵심 성분: [내용]
- 특허 기술: [내용] (선택)

🧪 성분 및 제형 상세
- 주성분: [성분명 (농도%), 효능]
- 부성분: [성분명 (농도%), 역할]
- 제형 기술: [유화 방식, 안정화 기술, 침투 기술 등]
- pH: [적정 pH 범위]
- 텍스처: [상세한 제형감 설명]

🌟 핵심 USP 💧
"[인용부호로 시작하는 메인 USP]"
- [부연 설명 1]
- [부연 설명 2]
- [부연 설명 3]

📖 제품 스토리
[창의적이고 감성적인 스토리텔링]
- 영감의 원천 (예: 치앙마이 고산지대 아침이슬, 신라 화랑의 미학 등)
- 브랜드 철학과 연결
- 소비자 공감 포인트
- 2-4문장으로 간결하게

👥 타겟 고객층
1차 타겟 | [20대 설명]
2차 타겟 | [30대 설명] (선택)

📢 마케팅 포인트
메인 카피: "[광고 카피]"
서브 메시지:
- "[서브 카피 1]"
- "[서브 카피 2]"
바이럴 전략: [SNS 바이럴 포인트]

**중요: 복잡한 표(table) 형식, 체크박스(✅), 다단 표 구조는 절대 사용하지 마세요. 위 형식만 사용하세요.**

## 주의사항
- 분석 데이터의 장점/단점을 반드시 반영
- **시장 리서치 데이터의 최신 트렌드를 반영** (제공된 경우)
- 추상적인 제안 대신 구체적인 제형, 성분, 용량 제안
- **성분명과 농도를 구체적으로 제시** (예: Niacinamide 5%, Hyaluronic Acid 2%)
- 올리브영 가격대와 타겟층에 맞는 현실적인 제안
- 핵심 메시지는 반드시 인용부호("")로 강조
- **제품 스토리는 감성적이면서도 브랜드 정체성과 연결**"""


def call_ai_api(prompt: str, model_info: dict) -> str:
    """AI API 호출 (Claude/OpenAI 지원)"""
    provider = model_info.get("provider", "anthropic")
    model_id = model_info.get("id", "")

    if provider == "anthropic":
        return _call_claude_api(prompt, model_id, model_info.get("thinking_budget", 0))
    elif provider == "openai":
        return _call_openai_api(prompt, model_id)
    else:
        return f"❌ 지원하지 않는 provider: {provider}"


def _call_claude_api(prompt: str, model_id: str, thinking_budget: int = 0) -> str:
    """Claude API 호출 (Extended Thinking 지원)"""
    try:
        import anthropic

        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "❌ ANTHROPIC_API_KEY가 설정되지 않았습니다. .streamlit/secrets.toml 파일을 확인해주세요."

        client = anthropic.Anthropic(api_key=api_key)

        if thinking_budget > 0:
            message = client.messages.create(
                model=model_id,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                thinking={
                    "type": "enabled",
                    "budget_tokens": thinking_budget
                },
                messages=[{"role": "user", "content": prompt}]
            )
            result_text = ""
            for block in message.content:
                if block.type == "text":
                    result_text += block.text
            return result_text
        else:
            message = client.messages.create(
                model=model_id,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                temperature=1.0,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text

    except ImportError:
        return "❌ anthropic 패키지가 설치되지 않았습니다. pip install anthropic"
    except Exception as e:
        return f"❌ Claude API 오류: {str(e)}"


def _call_openai_api(prompt: str, model_id: str) -> str:
    """OpenAI API 호출"""
    try:
        from openai import OpenAI

        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            return "❌ OPENAI_API_KEY가 설정되지 않았습니다. .streamlit/secrets.toml 파일을 확인해주세요."

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model_id,
            max_completion_tokens=4096,
            temperature=1.0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    except ImportError:
        return "❌ openai 패키지가 설치되지 않았습니다. pip install openai"
    except Exception as e:
        return f"❌ OpenAI API 오류: {str(e)}"


def load_all_research_files() -> dict:
    """
    리서치 탭의 모든 md 파일 로드

    Returns:
        dict: {
            'trendier': [(filename, content), ...],
            'hwahae': [(filename, content), ...],
            'deepresearch': [(filename, content), ...]
        }
    """
    research_data = {
        'trendier': [],
        'hwahae': [],
        'deepresearch': []
    }

    for category in research_data.keys():
        category_dir = REPORTS_DIR / category
        if category_dir.exists():
            for md_file in sorted(category_dir.glob("*.md")):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    research_data[category].append((md_file.name, content))
                except UnicodeDecodeError:
                    # cp949 fallback
                    try:
                        content = md_file.read_text(encoding="cp949")
                        research_data[category].append((md_file.name, content))
                    except Exception:
                        pass
                except Exception as e:
                    print(f"Error loading {md_file}: {e}")

    return research_data


def format_research_section(research_data: dict) -> str:
    """
    리서치 데이터를 프롬프트 섹션으로 포맷팅

    Returns:
        str: 마크다운 형식의 리서치 섹션
    """
    if not any(research_data.values()):
        return ""

    md = "\n\n---\n\n# 시장 리서치 데이터\n\n"

    # 카테고리별 리서치 추가
    category_names = {
        'trendier': '🔍 Trendier 리포트',
        'hwahae': '💧 화해 리포트',
        'deepresearch': '🤖 딥리서치 (Claude Code)'
    }

    for category, files in research_data.items():
        if files:
            md += f"## {category_names[category]}\n\n"
            for filename, content in files:
                md += f"### 📄 {filename}\n\n"
                md += content + "\n\n"

    return md


st.set_page_config(page_title="신제품 아이디어 생성", page_icon="💡", layout="wide")

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


def generate_oliveyoung_prompt(analyses: list, selected_research_categories: list = None) -> str:
    """
    올리브영 분석 데이터 기반 프롬프트 생성 (리서치 데이터 포함)

    Args:
        analyses: 경쟁사 분석 데이터
        selected_research_categories: 선택된 리서치 카테고리 리스트
            ["Trendier 리포트", "화해 리포트", "딥리서치"]
    """
    if not analyses:
        return ""

    # 올리브영 제품 정보를 한 번만 조회하여 딕셔너리로 변환 (성능 최적화)
    oliveyoung_products_dict = {
        p['product_code']: p
        for p in db.get_oliveyoung_products()
    }

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
        for s in a.get('strengths', []) or []:
            if ':' in s:
                kw = s.split(':')[0].strip()
                detail = s.split(':', 1)[1].strip() if ':' in s else s
            else:
                kw = s[:15].strip()
                detail = s
            all_strengths.append((kw, detail))

        # 단점 수집 (키워드와 원문 함께)
        for w in a.get('weaknesses', []) or []:
            if ':' in w:
                kw = w.split(':')[0].strip()
                detail = w.split(':', 1)[1].strip() if ':' in w else w
            else:
                kw = w[:15].strip()
                detail = w
            all_weaknesses.append((kw, detail))

        # USP 수집
        for usp in a.get('usp_candidates', []) or []:
            cat = usp.get('category', 'other')
            sentence = usp.get('sentence', '')
            keywords = usp.get('trigger_words', []) or []
            if sentence and keywords:
                all_usp.append({
                    'category': cat,
                    'keyword': keywords[0] if keywords else '',
                    'sentence': sentence
                })

        # 리뷰 샘플 수집
        for r in (a.get('review_samples', []) or [])[:3]:
            all_review_samples.append(r.get('content', '')[:100])

        # 올리브영 제품 정보에서 카테고리, 가격 가져오기 (딕셔너리 조회로 최적화)
        if product_code and product_code in oliveyoung_products_dict:
            p = oliveyoung_products_dict[product_code]
            if p.get('category'):
                categories.add(p['category'])
            if p.get('price'):
                prices.append(p['price'])

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
4. **성분 및 제형**: 구체적인 성분명, 농도, 제형 기술 제안
5. **제품 스토리**: 감성적이고 창의적인 스토리텔링
6. **타겟 고객층**: 이 제품이 가장 어필할 고객층
7. **마케팅 포인트**: 소비자에게 강조할 메시지
8. **아이디어 3개**: 위 내용을 바탕으로 신제품 아이디어 3개를 제안해주세요

## 시장 리서치 리포트 활용
**리포트가 별도로 첨부된 경우**, 아래 사항을 참고하여 아이디어를 보완하세요:
- 최신 화장품 트렌드 (성분, 제형, 디자인)
- 소비자 선호도 변화
- 경쟁 브랜드의 신제품 동향
- 화해, Trendier 등 플랫폼의 인사이트

**리포트가 첨부되지 않은 경우**, 당신의 지식을 바탕으로 다음을 조사하여 반영하세요:
- 2025-2026년 최신 화장품 트렌드 (K-뷰티, 글로벌 시장)
- 화해, Trendier 등 플랫폼의 최신 리뷰 트렌드
- 인기 성분 및 제형 기술 (예: 발효 성분, 프로바이오틱스, 나이아신아마이드 등)
- MZ세대가 선호하는 제품 특징
- 지속가능성, 비건, 클린뷰티 등 윤리적 소비 트렌드

## 컨셉명 작성 가이드
- 영문+한글 조합 또는 순한글 모두 가능
- 제품의 핵심 효능이나 특징을 직관적으로 표현
- 올리브영 감성에 맞는 트렌디한 네이밍
- 예시: "아쿠아락 제로", "시카밤 리페어", "글로우 부스터" 등
- **영문 스타일**: Aqualock Zero, Glow Drop, Cica Calm 등
- **한글 스타일**: 물광젤리, 촉촉담, 진정수 등
- **혼합 스타일**: 수분락 제로, 글로우 물광팩 등

## 성분 제안 가이드
- 구체적인 성분명과 농도 제시 (예: Niacinamide 5%, Centella Asiatica Extract 10%)
- 성분의 효능과 근거 설명
- 제형 기술 구체적 제시 (예: 리포좀 캡슐화, 나노 에멀젼 등)
- 리서치 리포트의 트렌드 성분 반영 (첨부된 경우)

## 제품 스토리 가이드
- 창의적이고 감성적인 스토리텔링
- 예시:
  * "치앙마이 고산지대 사람들은 아침이슬로 세수하는 것이 피부 관리의 비결"
  * "신라시대 화랑은 '외면의 아름다움은 내면에 투영된다'고 믿었기에..."
  * "제주 화산송이의 미세한 기공은 피부 노폐물을 흡착하는 자연의 지혜"
- 브랜드 철학과 자연스럽게 연결
- 2-4문장으로 간결하게

각 아이디어는 구체적으로 작성해주세요.

## 출력 형식
응답은 반드시 다음 제목으로 시작해주세요:
# 🧴 신제품 아이디어 생성
"""

    # === 리서치 데이터 추가 (선택된 카테고리만) ===
    if selected_research_categories:
        # 카테고리명 매핑
        category_map = {
            "Trendier 리포트": "trendier",
            "화해 리포트": "hwahae",
            "딥리서치": "deepresearch"
        }

        # 선택된 카테고리만 필터링
        selected_keys = [category_map[cat] for cat in selected_research_categories if cat in category_map]

        research_data = load_all_research_files()
        filtered_data = {k: v for k, v in research_data.items() if k in selected_keys}

        research_section = format_research_section(filtered_data)
        md += research_section

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

    # 두 개의 버튼 나란히 배치
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📋 무료 (프롬프트 복사)")

        if st.button("프롬프트 생성", type="secondary", use_container_width=True,
                    help="프롬프트를 생성하여 화면에 표시"):
            # 버튼 클릭 시 입력값 파싱
            input_codes = parse_goodsno_input(goodsno_input) if goodsno_input else []

            if not input_codes:
                st.error("GOODSNO를 입력해주세요.")
            else:
                valid_codes = [c for c in input_codes if c in analyzed_codes]
                invalid_codes = [c for c in input_codes if c not in analyzed_codes]

                if invalid_codes:
                    st.warning(f"미분석 {len(invalid_codes)}개 제외")

                if not valid_codes:
                    st.error("분석 완료된 GOODSNO가 없습니다.")
                else:
                    with st.spinner("프롬프트 생성 중..."):
                        analyses = db.get_review_analyses_by_codes(valid_codes)

                    if analyses:
                        # 프롬프트 생성 (리서치 제외)
                        prompt = generate_oliveyoung_prompt(analyses)

                        # session_state에 저장
                        st.session_state['free_prompt'] = prompt
                        st.success(f"✅ {len(analyses)}개 제품 프롬프트 생성!")
                        st.rerun()
                    else:
                        st.error("분석 데이터를 가져오지 못했습니다.")

        # === 생성된 프롬프트 표시 ===
        if 'free_prompt' in st.session_state and st.session_state['free_prompt']:
            st.divider()

            prompt = st.session_state['free_prompt']

            # 프롬프트 표시 (접을 수 있는 expander)
            with st.expander("📄 프롬프트 미리보기", expanded=True):
                st.code(prompt, language="markdown")

            st.caption("💡 위 코드 블록 우측 상단의 복사 버튼을 클릭하여 복사하세요")

    with col2:
        st.markdown("#### 🚀 유료 (API 자동 생성)")

        # 리서치 선택 (멀티셀렉트)
        selected_research_api = st.multiselect(
            "포함할 리서치 선택",
            options=["Trendier 리포트", "화해 리포트", "딥리서치"],
            default=["Trendier 리포트", "화해 리포트", "딥리서치"],  # API는 모든 리서치 기본 선택
            help="선택한 리서치가 자동으로 AI에게 전달됩니다",
            key="research_api"
        )

        # 버튼 먼저 배치
        api_clicked = st.button("AI 아이디어 생성", type="primary", use_container_width=True,
                    help="AI API로 아이디어 자동 생성 (Claude/GPT)")

        # 모델 선택 (우측 하단에 작게 - 1/3 크기)
        _, model_col = st.columns([2, 1])
        with model_col:
            selected_model = st.selectbox(
                "모델",
                options=list(AI_MODELS.keys()),
                index=0,
                key="model_select",
                label_visibility="collapsed"
            )
            model_info = AI_MODELS[selected_model]
            st.caption(f"예상: {model_info['cost']}")

        if api_clicked:
            input_codes = parse_goodsno_input(goodsno_input) if goodsno_input else []

            if not input_codes:
                st.error("GOODSNO를 입력해주세요.")
            else:
                valid_codes = [c for c in input_codes if c in analyzed_codes]
                invalid_codes = [c for c in input_codes if c not in analyzed_codes]

                if invalid_codes:
                    st.warning(f"미분석 {len(invalid_codes)}개 제외")

                if not valid_codes:
                    st.error("분석 완료된 GOODSNO가 없습니다.")
                else:
                    thinking_budget = model_info.get('thinking_budget', 0)
                    thinking_msg = " (Extended Thinking)" if thinking_budget > 0 else ""
                    with st.spinner(f"{selected_model}로 아이디어 생성 중...{thinking_msg} (약 30-60초 소요)"):
                        analyses = db.get_review_analyses_by_codes(valid_codes)

                        if analyses:
                            prompt = generate_oliveyoung_prompt(analyses, selected_research_api)
                            result = call_ai_api(prompt, model_info)
                            st.session_state['api_result'] = result
                            st.session_state['oliveyoung_prompt'] = None  # 프롬프트 초기화

                            # 자동 저장 (저장된 제안 탭)
                            if result and not result.startswith("❌"):
                                proposal_title = f"AI 제안 ({selected_model}) - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                                db.add_proposal({
                                    'title': proposal_title,
                                    'category': '올리브영 분석',
                                    'concept_description': result,
                                    'key_features': [f"분석 제품: {len(valid_codes)}개", f"모델: {selected_model}"],
                                    'notes': f"GOODSNO: {', '.join(valid_codes[:5])}{'...' if len(valid_codes) > 5 else ''}"
                                })
                                st.session_state['last_saved_title'] = proposal_title
                                st.success(f"✅ AI 아이디어 생성 완료!{thinking_msg} (자동 저장됨)")
                            else:
                                st.error(result)
                        else:
                            st.error("분석 데이터를 가져오지 못했습니다.")

    # === 생성된 프롬프트 표시 (무료) ===
    if 'oliveyoung_prompt' in st.session_state and st.session_state['oliveyoung_prompt']:
        prompt = st.session_state['oliveyoung_prompt']

        st.divider()
        st.markdown("## 📋 Claude/Gemini/GPT 프롬프트")
        st.caption("오른쪽 상단 📋 버튼을 클릭하면 복사됩니다. → Claude/GPT에 붙여넣기 (Ctrl+V)")

        st.code(prompt, language="markdown")

    # === API 결과 표시 (유료) ===
    if 'api_result' in st.session_state and st.session_state['api_result']:
        result = st.session_state['api_result']

        st.divider()
        st.markdown("## 🚀 AI 생성 아이디어")

        # Markdown 다운로드 버튼
        col_title, col_download = st.columns([3, 1])
        with col_title:
            if 'last_saved_title' in st.session_state:
                st.caption(f"💾 저장됨: {st.session_state['last_saved_title']}")
        with col_download:
            # Markdown 파일 생성
            md_content = f"""# 신제품 아이디어
> 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

{result}
"""
            st.download_button(
                label="📥 Markdown 다운로드",
                data=md_content,
                file_name=f"신제품_아이디어_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown"
            )

        st.markdown(result)


def main():
    st.title("💡 신제품 아이디어 생성")

    # 통계 요약
    col1, col2 = st.columns(2)
    with col1:
        analyzed_count = len(db.get_analyzed_product_codes())
        st.metric("분석 완료 제품", f"{analyzed_count}개")
    with col2:
        proposals = db.get_proposals()
        st.metric("저장된 제안", f"{len(proposals)}개")

    st.divider()

    # 탭 구성
    tab_oliveyoung, tab_saved = st.tabs([
        "🛒 경쟁사 분석 기반", "💾 저장된 아이디어"
    ])

    with tab_oliveyoung:
        render_oliveyoung_tab()

    with tab_saved:
        st.subheader("저장된 신제품 아이디어")

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
