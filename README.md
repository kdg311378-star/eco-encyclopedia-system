# 🌿 생물 도감 데이터 자동 수집 플랫폼 (Bio Encyclopedia Collector)

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B)
![Playwright](https://img.shields.io/badge/Playwright-Crawler-2EAD33)
![MySQL](https://img.shields.io/badge/MySQL-Database-4479A1)

> **위키백과(Wikipedia)**, **위키미디어 커먼즈(Wikimedia Commons)**, 그리고 **GBIF(세계 생물다양성 정보기구)**를 연동하여 특정 생물 종(Species)의 족보(Taxonomy), 서식지 정보, 고해상도 이미지를 원클릭으로 자동 수집하고 DB에 적재하는 파이프라인 플랫폼입니다.

---

## ✨ 주요 기능 (Key Features)

### 1. 🖥️ 직관적인 웹 대시보드 (Streamlit)
- 복잡한 터미널 명령어 없이 깔끔한 웹 환경에서 수집을 제어합니다.
- 수집된 생물 도감을 **갤러리 형태**로 시각화하여 조회합니다.
- 데이터베이스를 **인터랙티브 표(Dataframe)**로 열람하고 클릭 한 번에 **엑셀(CSV)로 내보낼 수 있습니다.**

### 2. 🤖 지능형 크롤링 및 중복 검증 시스템
- **단일 입력 지원**: 학명 또는 국명 중 하나만 입력해도 찰떡같이 알아듣고 알아서 수집합니다.
- **크롤링 사전 방어선**: 웹으로 데이터를 긁어오기 직전, 우리 DB를 먼저 탐색하여 이미 존재하는 생물이면 리소스 낭비를 막고 즉시 스킵합니다.
- **이미지 pHash 중복 검사**: 이미지의 색상이나 크기가 미세하게 달라도, 64비트 Perceptual Hash를 계산해 동일한 사진(해밍거리 $\le 5$)이면 저장하지 않고 필터링합니다.

### 3. 🚀 GBIF 기반 Top-Down 대규모 배치 수집
- 단순히 한 마리씩 찾는 것을 넘어, **"포유강(Mammalia)에 속한 생물 다 찾아줘!"**가 가능합니다.
- GBIF 공공 API를 통해 수천 개의 학명 리스트를 추출하고, 이를 큐(Queue)에 담아 밤새 연속으로 자동 수집(Batch)을 돌릴 수 있습니다.

### 4. 🗜️ 이미지 자동 최적화 및 명명 규칙
- 수집된 원본 이미지는 무거운 원본 대신 초고효율의 `WebP` 포맷으로 자동 압축됩니다.
- 파일명은 임의의 암호문이 아닌, 직관적인 **`수집일자_영문학명(국문명)_순번.webp`** 형태로 예쁘게 정리되어 로컬에 저장됩니다.

---

## 🛠 환경 설정 및 설치 가이드

### 1. 패키지 설치
이 프로젝트는 Python 3.11 이상의 환경을 권장합니다.
```bash
# 필수 라이브러리 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정
프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 MySQL DB 접속 정보를 입력합니다.
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_username
DB_PASSWORD=your_db_password
DB_NAME=bio_encyclopedia
```

### 3. 데이터베이스 초기화
최초 실행 시, 제공된 스크립트를 사용하여 테이블 스키마를 초기화합니다.
```bash
python init_db.py
```

---

## 💻 사용 방법 (How to use)

가장 강력하고 편리한 방법은 **Streamlit 웹 대시보드**를 이용하는 것입니다.

### 1️⃣ 웹 대시보드 모드 (권장)
터미널에 아래 명령어를 입력하면 브라우저가 열리며 대시보드가 나타납니다.
```bash
python -m streamlit run app.py
```

![웹 대시보드 메인 화면](assets/dashboard_screenshot.png)
- **탭 1 (단일 종 수집)**: `뉴트리아`, `Rhinella marina` 처럼 단어를 치고 🖱️[수집 시작]을 누릅니다.
- **탭 2 (갤러리 및 표)**: 지금까지 수집한 동물/식물의 멋진 도감을 감상하고 엑셀(CSV)로 다운로드합니다.
- **탭 3 (대규모 수집)**: GBIF 연동을 통해 특정 '과/목/강' 에 속한 동물들을 대량으로 긁어옵니다.

### 2️⃣ CLI (터미널) 모드
웹을 띄우지 않고 백그라운드 서버 스크립트나 터미널에서 직접 실행할 수도 있습니다.
```bash
# 학명이나 국명 중 하나만 입력해도 무방합니다.
python run_pipeline.py "황소개구리"
python run_pipeline.py "Ursus arctos" "불곰" NATIVE
```

---

## 📂 디렉토리 및 아키텍처 구조

```text
c:\project\eco_encyclopedia_system\
├── app.py                 # 🌟 Streamlit 웹 대시보드 진입점 (Main)
├── run_pipeline.py        # ⚙️ 파이프라인 배치 실행 진입점 (CLI)
├── config/
│   └── database.py        # DB 환경변수 래퍼 및 커넥션 설정
├── core/
│   ├── crawler.py         # Playwright 기반 비동기 웹 크롤러 엔진
│   ├── parser.py          # Wikipedia/Commons DOM 구조 파서
│   ├── processor.py       # WebP 변환 및 이미지 pHash 계산
│   ├── gbif_api.py        # GBIF 대규모 종 리스트 추출 API 연동 모듈
│   └── db_manager.py      # MySQL 트랜잭션 및 조회/저장 쿼리 관리
├── sql/
│   └── schema.sql         # DB 구조를 정의하는 DDL 스크립트
├── static/
│   └── images/
│       └── species/       # 수집된 WebP 물리적 이미지 저장 폴더
├── init_db.py             # DB 스키마 초기화 스크립트
├── requirements.txt       # 의존성 패키지 리스트
└── README.md              # 프로젝트 안내 문서 (현재 파일)
```
