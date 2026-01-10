"""
화장품 신제품 개발 시장 조사 분석 도구 - 메인 대시보드
"""
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from PIL import Image

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
    st.title("💄 SKINNERD 신제품 개발 솔루션")

    # ===== 회사 사진 자동 재생 캐러셀 =====
    st.divider()

    # 자동 새로고침 (3초마다)
    count = st_autorefresh(interval=3000, key="image_refresh")

    # 이미지 경로 설정
    IMAGE_FOLDER = "상품개발홈페이지용사진"
    IMAGE_COUNT = 9

    # 세션 스테이트 초기화
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0
        st.session_state.last_refresh_count = 0

    # 자동 전환 (새로고침될 때마다 인덱스 증가)
    if count != st.session_state.last_refresh_count:
        st.session_state.current_image_index = (st.session_state.current_image_index + 1) % IMAGE_COUNT
        st.session_state.last_refresh_count = count

    # 현재 인덱스 계산
    current_idx = st.session_state.current_image_index

    # 슬라이드쇼: 중앙에 1개 이미지만 표시
    current_image_path = f"{IMAGE_FOLDER}/{current_idx + 1}.jpg"
    try:
        img = Image.open(current_image_path)
        st.image(img, width='stretch')
    except FileNotFoundError:
        st.error(f"이미지를 찾을 수 없습니다: {current_image_path}")

    # 페이지 인디케이터 (중앙 정렬)
    st.markdown(
        f"<p style='text-align: center; color: gray; font-size: 14px;'>{current_idx + 1} / {IMAGE_COUNT}</p>",
        unsafe_allow_html=True
    )

    # CSS로 이미지 스타일링 (Fade 애니메이션)
    st.markdown(
        """
        <style>
        /* 이미지 스타일 */
        img {
            width: 100%;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            animation: fadeIn 0.8s ease-in-out;
        }

        /* Fade In 애니메이션 정의 */
        @keyframes fadeIn {
            from {
                opacity: 0;
            }
            to {
                opacity: 1;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # 사이드바 안내
    with st.sidebar:
        st.header("📌 사용 방법")
        st.markdown("""
        1. **경쟁사 상품분석**: 베스트 상품 수집 및 리뷰 분석
        2. **신제품 아이디어 생성**: 데이터 기반 아이디어 도출

        ---

        💡 **팁**: 올리브영 리뷰에서 USP와 유니크 포인트를 발굴하세요.
        """)


if __name__ == "__main__":
    main()
