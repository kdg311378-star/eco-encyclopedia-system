# 생태계 백과사전 데이터 수집 파이프라인 (Eco Encyclopedia Pipeline)

GBIF(Global Biodiversity Information Facility) API와 Wikipedia, Wikimedia Commons를 연동하여 전 세계 생물 종(Species)의 정보와 이미지를 수집하고, AWS Serverless 환경에서 단계별로 정제 및 처리하는 대규모 데이터 수집 파이프라인 프로젝트입니다.

현재 프로젝트는 **AWS Serverless (EventBridge + Step Functions + Lambda)** 구조를 기반으로 완전 자동화된 수집 파이프라인을 제공합니다.

- **AWS 파이프라인**: Dispatcher Lambda → Step Functions Map State → [ Crawling Lambda → S3 Raw → Extract Lambda → S3 Interim → Preprocess Lambda → S3 Processed → Load Lambda → Amazon RDS MySQL ]

또한 `pytest`, `Ruff`, GitHub Actions를 이용하여 코드 품질과 테스트를 자동으로 검증(CI)하며, AWS SAM을 이용하여 인프라(Lambda, S3, Step Functions 등)를 깃허브에서 직접 배포(CD)합니다. Load 및 Dispatcher 단계에서는 AWS Secrets Manager의 RDS 관리형 Secret과 VPC 네트워크 구성을 이용해 Private RDS MySQL에 안전하게 통신합니다.

---

## 1. 프로젝트 목표

이 프로젝트의 주요 목표는 다음과 같습니다.

- GBIF API에서 겹치지 않는 신규 생물 종 데이터를 지속적으로 수집합니다. (Infinite Polling)
- 한 번의 수집(크롤링~적재) 단계를 `batch_id` 기준으로 안전하게 추적 및 관리합니다.
- 원본 HTML/JSON, 파싱 데이터, 전처리 데이터를 S3의 단계별 폴더(`raw`, `interim`, `processed`)로 분리 저장합니다.
- AWS 환경에서 Lambda별 책임을 철저히 분리하고 S3를 단계 간 대용량 데이터 전달 저장소로 활용합니다.
- Step Functions의 Map State를 활용하여 한 번에 여러 생물 종 데이터를 병렬(Concurrent)로 빠르게 처리합니다.
- S3 텍스트뿐만 아니라 생물의 이미지(phash 중복 제거 적용)까지 추출하여 저장합니다.
- `pytest`와 `Ruff`를 이용해 깃허브에 코드가 올라갈 때마다 코드 포맷팅과 테스트를 자동 검증(CI)합니다.
- AWS SAM 및 OIDC를 활용하여 깃허브 환경에서 안전하고 자동화된 배포(CD)를 구성합니다.

---

## 2. 전체 구성

### AWS 서버리스 파이프라인

현재 AWS 환경에서는 스케줄러를 통해 지휘관 람다(Dispatcher)가 깨어나고, Step Functions를 통해 하위 작업들이 병렬로 실행됩니다.

```text
EventBridge (매일 0시)
       ↓
Dispatcher Lambda (GBIF 신규 생물 탐색 및 MySQL 오프셋 기록)
       ↓
AWS Step Functions (Map State)
       │
       ├─▶ Crawling Lambda (위키백과 HTML & 위키미디어 API 요청)
       │          ↓
       │   Amazon S3 (raw/{batch_id}/)
       │          ↓
       ├─▶ Extract Lambda (HTML 파싱, Taxobox 및 이미지 주소 추출)
       │          ↓
       │   Amazon S3 (interim/{batch_id}/)
       │          ↓
       ├─▶ Preprocess Lambda (데이터 클렌징, 이미지 pHash 계산)
       │          ↓
       │   Amazon S3 (processed/{batch_id}/)
       │          ↓
       └─▶ Load Lambda (RDS MySQL 적재)
                  ↓
       AWS Secrets Manager (DB 비밀번호 조회)
                  ↓
           Amazon RDS MySQL
         (species, species_images 테이블 UPSERT)
```

---

## 3. 프로젝트 구조

```text
eco_encyclopedia_system/
│
├─ .github/
│  └─ workflows/
│     ├─ ci.yml             # 코드 품질 및 테스트 검증 워크플로우
│     └─ deploy.yml         # AWS SAM 기반 인프라 배포 워크플로우 (수동 트리거)
│
├─ handlers/
│  ├─ dispatcher_handler.py # 스케줄러 진입점 람다
│  ├─ crawling_handler.py   # 크롤링 람다
│  ├─ extract_handler.py    # 데이터 파싱 람다
│  ├─ preprocess_handler.py # 전처리 람다
│  └─ load_handler.py       # RDS 적재 람다
│
├─ src/
│  └─ eco_encyclopedia/
│     ├─ crawling.py
│     ├─ dispatch.py
│     ├─ extract.py
│     ├─ load.py
│     ├─ preprocess.py
│     ├─ s3_storage.py
│     └─ database.py
│
├─ sql/
│  └─ schema.sql            # RDS MySQL 테이블 (species, images, sync_state) 정의 
│
├─ tests/                   # pytest 모의(Mock) 테스트 코드
├─ .env.example             # 환경변수 예시
├─ pyproject.toml / .gitignore
├─ requirements.txt         # 프로덕션 패키지
├─ requirements-dev.txt     # 개발 및 테스트 패키지
└─ template.yaml            # AWS SAM 리소스 정의 템플릿
```

---

## 4. 주요 데이터 흐름 및 테이블

### MySQL 테이블 스키마 (`sql/schema.sql`)
1. **`species`**: 생물의 학명(scientific_name), 국명, 분류(계/문/강/목/과/속), 서식지 정보, S3 저장 경로 등 핵심 데이터를 담습니다.
2. **`species_images`**: 생물의 이미지 S3 경로, 저작권자, pHash(중복 제거용) 등을 저장합니다. (`species` 테이블과 1:N 관계)
3. **`sync_state`**: GBIF API에서 지금까지 어디까지 읽었는지(Offset) 기억하여 무한 루프 수집이 가능하게 하는 스케줄러 상태 테이블입니다.

### S3 데이터 구조
- `raw/{batch_id}/wikipedia.html`
- `raw/{batch_id}/commons.json`
- `interim/{batch_id}/parsed_metadata.json`
- `processed/{batch_id}/final_metadata.json`

---

## 5. AWS SAM 구성 (`template.yaml`)

- **`EcoDataBucket`**: 파이프라인 데이터를 단계별로 저장하는 S3 버킷
- **`DataPipelineStateMachine`**: Map 상태를 통해 종(Species) 목록을 받아 병렬 크롤링을 관장하는 AWS Step Functions
- **`DispatcherFunction`**: EventBridge 룰에 의해 매일 트리거되어 타겟 생물 목록을 찾아 State Machine에 던져주는 진입점 람다
- **`Crawling / Extract / Preprocess / Load Functions`**: 각각의 역할을 수행하는 람다 함수들. (`Load`와 `Dispatcher`는 RDS 접근을 위해 VPC/서브넷에 위치)

배포는 GitHub Actions의 `Deploy Serverless Pipeline` 탭에서 수동(`workflow_dispatch`)으로 트리거할 수 있으며, 배포 시 환경 변수로 주입되는 Secret ARN과 서브넷 정보를 기반으로 AWS 클라우드에 자동 구성됩니다.
