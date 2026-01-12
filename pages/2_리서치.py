"""
리서치 탭 - 시장 분석 리포트 관리
"""
import streamlit as st
from pathlib import Path
from datetime import datetime

# 페이지 설정 (기존 패턴 유지)
st.set_page_config(
    page_title="리서치",
    page_icon="📊",
    layout="wide"
)

# 리포트 저장 경로
REPORTS_DIR = Path(__file__).parent.parent / "reports"
TRENDIER_DIR = REPORTS_DIR / "trendier"
HWAHAE_DIR = REPORTS_DIR / "hwahae"
DEEPRESEARCH_DIR = REPORTS_DIR / "deepresearch"


def render_report_tab(tab_name: str, report_dir: Path):
    """
    리포트 탭 렌더링 (파일 업로드/목록/표시/삭제)

    Args:
        tab_name: 탭 이름 (예: "Trendier")
        report_dir: 리포트 저장 디렉토리 경로
    """
    st.subheader(f"{tab_name} 리포트")

    # 디렉토리 확인 및 생성
    report_dir.mkdir(parents=True, exist_ok=True)

    # 1️⃣ 파일 업로드 섹션
    with st.expander("📁 새 리포트 업로드", expanded=False):
        uploaded_file = st.file_uploader(
            "마크다운 파일 업로드 (.md)",
            type=["md"],
            key=f"uploader_{tab_name}",
            help="분석 리포트 md 파일을 업로드하세요"
        )

        if uploaded_file:
            # 파일명 중복 체크
            file_path = report_dir / uploaded_file.name

            if file_path.exists():
                st.warning(f"⚠️ '{uploaded_file.name}' 파일이 이미 존재합니다.")
                overwrite = st.checkbox("덮어쓰기", key=f"overwrite_{tab_name}")
                if not overwrite:
                    st.stop()

            # 저장 버튼
            if st.button("💾 저장", key=f"save_{tab_name}"):
                file_path.write_bytes(uploaded_file.getvalue())
                st.success(f"✅ '{uploaded_file.name}' 저장 완료!")
                st.rerun()

    st.divider()

    # 2️⃣ 저장된 리포트 목록
    md_files = sorted(report_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not md_files:
        st.info(f"📭 저장된 {tab_name} 리포트가 없습니다. 파일을 업로드해주세요.")
        return

    # 파일 선택
    file_options = [f.name for f in md_files]
    selected_file_name = st.selectbox(
        f"📄 리포트 선택 ({len(md_files)}개)",
        options=file_options,
        key=f"select_{tab_name}"
    )

    selected_file = report_dir / selected_file_name

    # 파일 내용 먼저 읽기 (다운로드 버튼용)
    try:
        content = selected_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # UTF-8 실패 시 cp949 시도 (한글 Windows 환경)
        try:
            content = selected_file.read_text(encoding="cp949")
        except Exception as e:
            st.error(f"❌ 파일 인코딩을 읽을 수 없습니다: {e}")
            return
    except Exception as e:
        st.error(f"❌ 파일을 읽는 중 오류 발생: {e}")
        return

    # 파일 정보 표시
    file_stat = selected_file.stat()
    file_size_kb = file_stat.st_size / 1024
    modified_time = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M")

    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        st.metric("📦 파일 크기", f"{file_size_kb:.1f} KB")
    with col2:
        st.metric("🕐 최종 수정", modified_time)
    with col3:
        # 다운로드 버튼
        st.download_button(
            label="📥",
            data=content,
            file_name=selected_file_name,
            mime="text/markdown",
            key=f"download_{tab_name}",
            help="리포트 다운로드",
            use_container_width=True
        )
    with col4:
        # 삭제 버튼
        if st.button("🗑️", key=f"delete_{tab_name}", type="secondary", help="리포트 삭제", use_container_width=True):
            selected_file.unlink()
            st.success(f"✅ '{selected_file_name}' 삭제 완료!")
            st.rerun()

    st.divider()

    # 3️⃣ 마크다운 내용 렌더링 (스크롤 가능)
    with st.container(height=600):
        st.markdown(content, unsafe_allow_html=False)


def main():
    st.title("📊 리서치")
    st.caption("시장 분석 리포트 및 트렌드 연구")

    # 3개 탭 구성
    tab1, tab2, tab3 = st.tabs([
        "🔍 Trendier 리포트",
        "💧 화해 리포트",
        "🤖 딥리서치 (Claude Code)"
    ])

    with tab1:
        render_report_tab("Trendier", TRENDIER_DIR)

    with tab2:
        render_report_tab("화해", HWAHAE_DIR)

    with tab3:
        render_report_tab("딥리서치", DEEPRESEARCH_DIR)


if __name__ == "__main__":
    main()
