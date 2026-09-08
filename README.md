# 🌿 생물 도감 데이터 자동 수집 백엔드 파이프라인 (Bio Encyclopedia Collector)

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-Serverless-FF9900)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI/CD-2088FF)
![MySQL](https://img.shields.io/badge/MySQL-Database-4479A1)

> **위키백과(Wikipedia)**, **위키미디어 커먼즈(Wikimedia Commons)**, 그리고 **GBIF(세계 생물다양성 정보기구)**를 연동하여 특정 생물 종(Species)의 족보(Taxonomy), 서식지 정보, 고해상도 이미지를 자동 수집하고 클라우드(S3 및 RDS)에 적재하는 서버리스(Serverless) 데이터 파이프라인 플랫폼입니다.

---

## ✨ 핵심 아키텍처 (AWS Serverless)

본 프로젝트는 무거운 컨테이너(Docker)나 항상 켜져 있는 서버(EC2) 없이, **AWS SAM (Serverless Application Model)** 을 활용한 완전 관리형 서버리스 아키텍처로 구동됩니다.

1.  **Crawling Lambda**: GBIF 또는 트리거를 통해 학명을 전달받아 위키백과(HTML) 및 커먼즈(API) 데이터를 즉시 수집하고 원시 데이터를 S3(`raw/`)에 저장합니다.
2.  **Extract Lambda**: S3의 원본 데이터에서 BeautifulSoup을 사용해 Taxonomy(분류계통)와 서식지만 추출하고 정제하여 S3(`interim/`)에 넘깁니다.
3.  **Preprocess Lambda**: 이미지 다운로드, WebP 고효율 압축 변환 및 pHash(64비트 지문) 알고리즘을 통한 이미지 완전 중복 차단을 수행하고 S3(`processed/`)에 보관합니다.
4.  **Load Lambda**: 최종 완성된 정제 데이터와 S3 이미지 링크를 프라이빗 VPC 내부에 위치한 **AWS RDS (MySQL)** 데이터베이스에 안전하게 꽂아 넣습니다.

---

## 🚀 왜 Playwright 대신 API를 선택했는가?

기존 브라우저 자동화 도구(Playwright)는 무거운 Docker 이미지를 요구하며 AWS Lambda의 구동 속도를 크게 저하시켰습니다. 이를 해결하기 위해:
*   위키백과는 초경량 **`BeautifulSoup`** 파서로 대체.
*   커먼즈 미디어는 마우스 클릭 대신 **`Wikimedia REST API`**로 통신.
*   **결과**: 람다 함수 용량이 불과 수 MB 단위로 줄어들었으며 수집 속도는 수십 배 빨라졌습니다.

---

## 🛠 환경 설정 및 설치 가이드 (로컬 테스트용)

클라우드에 배포하기 전, 로컬에서 터미널을 통해 파이프라인 단계를 테스트할 수 있습니다.

### 1. 패키지 설치
```bash
# 필수 라이브러리 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정
프로젝트 최상단에 `.env` 파일을 만들고 로컬 또는 테스트 DB 접속 정보를 적습니다.
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_username
DB_PASSWORD=your_db_password
DB_NAME=bio_encyclopedia
```

### 3. 데이터베이스 초기화
```bash
python init_db.py
```

### 4. 로컬 파이프라인 실행
```bash
python run_pipeline.py "황소개구리"
python run_pipeline.py "Ursus arctos" "불곰" NATIVE
```

---

## 🔒 배포 가이드 (CI/CD)

이 저장소는 GitHub Actions와 AWS OIDC(OpenID Connect)를 통해 안전하게 AWS 클라우드로 배포됩니다. `.env` 파일은 깃허브에 절대 올라가지 않으며, 프로덕션 환경 변수는 **GitHub Secrets**를 통해 주입됩니다.�다.

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
