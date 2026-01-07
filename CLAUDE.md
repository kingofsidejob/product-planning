# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

화장품 신제품 개발을 위한 시장 조사 분석 도구. Python + Streamlit 기반 개인 프로젝트.

## 개발 명령어

```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행
streamlit run app.py
```

## 아키텍처

### 핵심 구조
- `app.py` - Streamlit 메인 대시보드
- `pages/` - Streamlit 멀티페이지 (1_competitor_products, 2_legacy_products, 3_product_proposal)
- `modules/` - 비즈니스 로직 (competitor, legacy, proposal)
- `database/` - SQLite 연결 및 스키마 (db_manager, models)
- `config.py` - 분류표 스키마 및 상수 정의

### 데이터베이스
- SQLite 사용 (`database/cosmetics_research.db`)
- 3개 테이블: `competitor_products`, `legacy_products`, `product_proposals`
- 10가지 대분류 분석 항목은 JSON 형식으로 저장

### 분류 체계
`config.py`의 `CLASSIFICATION_SCHEMA`에 10가지 대분류 정의:
- 디자인/패키징, 사용자경험, 제형, 컬러, 향, 성분, 기술, 사용환경, 마케팅, 지속가능성

## 주요 기능

1. **경쟁사 제품 분석** - 상세페이지/블로그에서 장점, 리뷰에서 단점 수집
2. **과거 특이 제품 분석** - 실패 제품 중 부활 가능성 평가 (1-5점)
3. **신제품 제안** - 수집 데이터 요약 + 규칙 기반 매칭 + 마크다운 내보내기

## 참고

- 계획 파일: `.claude/plans/immutable-hatching-iverson.md`
- 한국어 프로젝트 (UI, 데이터, 주석 모두 한국어)
