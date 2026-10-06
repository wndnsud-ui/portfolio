# DecisionFlow

## 회의 없는 업무지시 · 결과물 제출

- 팀장/소유자: 협업 화면의 **업무 · 결재함 → 회의 없이 업무지시**에서 프로젝트, 담당 팀원, 업무 제목, 지시 내용, 마감일과 우선순위를 입력합니다. 담당 팀원은 먼저 해당 프로젝트에 등록되어 있어야 합니다.
- 팀원: **내 업무**에서 업무를 열어 **업무 수락 → 업무 시작** 후 결과 파일을 업로드하고 결과 설명을 작성해 **결재 요청**합니다.
- 팀장: 업무 상세에서 파일을 확인하고 승인 또는 수정 요청합니다. 승인한 업무는 **최종 결과**에서 다시 열 수 있습니다.
- PDF, PNG/JPG, TXT/MD는 화면 미리보기를 지원하며 Word(DOCX), Excel(XLSX)은 다운로드해 확인합니다. 파일당 최대 20MB입니다.

## 팀장·팀원 테스트 계정

아래 명령으로 현재 `DATABASE_URL`의 DB에 테스트 계정과 공용 테스트 프로젝트를 생성합니다. 먼저 `python -m alembic upgrade head`를 실행하세요. 재실행해도 계정과 프로젝트가 중복 생성되지 않으며 기존 계정의 비밀번호를 덮어쓰지 않습니다.

```powershell
python -m scripts.seed_test_accounts
# Docker DB에 생성할 경우
docker compose exec decisionflow python -m scripts.seed_test_accounts
```

| 구분 | 로그인 아이디(이메일) | 비밀번호 | Workspace 권한 |
| --- | --- | --- | --- |
| 팀장 | `leader@decisionflow.test` | `LeaderTest123!` | `MANAGER` |
| 팀원 | `member@decisionflow.test` | `MemberTest123!` | `MEMBER` |

로그인 후 `권한 테스트 Workspace`와 `팀장·팀원 권한 테스트` 프로젝트를 선택하세요. 두 계정은 같은 프로젝트에 참여하며 팀장 계정에는 프로젝트 관리 권한이 있습니다. Workspace 소유자(`OWNER`) 권한과는 별개입니다.

계정은 명령을 실행한 DB에만 생성됩니다. 운영 환경에서는 명시적으로 `--allow-production`을 지정해야 하며, 공개된 비밀번호이므로 테스트 후 계정을 삭제하거나 비밀번호를 변경하세요.

## 4차 고도화: 회의 검토·업무 결재

Workspace와 프로젝트 멤버를 등록한 뒤 회의 담당자 검토 → 팀장 승인·게시 → 실제 사용자 업무 배정 → 수락·수행·결과 제출 → 승인·최종 결과 게시 흐름을 사용합니다. 로그인 후 Workspace를 선택하고 **검토 · 결재 · 알림** 화면에서 진행합니다.

구현·검증·운영 제한 사항은 [구현 보고서](docs/phase2-v4-implementation-report.md)에 정리했습니다.

```powershell
docker compose up --build -d
# 로컬 Python 환경에서 API·마이그레이션 회귀 검증
python -m unittest discover -s tests -v
```

앱 시작 시 Alembic을 최신 리비전으로 적용합니다. 기존 운영 DB는 먼저 백업하세요. 운영 설정은 `APP_ENV=production`, PostgreSQL `DATABASE_URL`, 별도 `SECRET_KEY`를 요구합니다. `ATTACHMENT_DIR=/data/attachments`를 영구 볼륨에 연결하고 기존 암호화·서명 키를 유지하세요. 개인 OpenAI/Notion 키는 로그인 후 설정에서 저장합니다.

운영 서비스: https://decisionflow-production.up.railway.app/ · Docker 이미지: `wndnsud/decisionflow:v4-20261006-r2`.

DecisionFlow는 회의 기록을 프로젝트별로 관리하고, 결정사항과 Action Item을 추적하는 FastAPI 기반 백엔드 서비스입니다. 현재 MVP는 규칙 기반 지연 위험도 계산을 제공하며 AI 분석, Notion 연동, ML 예측을 확장할 수 있도록 서비스 계층이 분리되어 있습니다.

## 주요 기능

- 프로젝트 CRUD
- 프로젝트 상세에서 회의 원문, 결정사항, Action Item 통합 조회
- 회의 및 회의록 CRUD, 검색
- 결정사항 CRUD 및 변경 이력 저장
- Action Item CRUD 및 상태/담당자/위험도 필터링
- 마감일, 우선순위, 상태 변경일 기반 위험 점수 계산
- 회의록 AI 결정사항 후보 추출, 근거/신뢰도 검토 및 사용자 확정
- Notion 동기화, ML 위험 예측 확장 인터페이스
- Swagger/OpenAPI 문서

## 기술 스택

- Python 3.11+
- React 19, TypeScript, Vite
- TanStack Query, Lucide Icons
- FastAPI, Uvicorn
- SQLAlchemy 2
- PostgreSQL, psycopg 3
- Alembic
- Pydantic Settings

## 프로젝트 구조

```text
frontend/
|-- src/          # React 컴포넌트, 화면, API 클라이언트
|-- dist/         # 프로덕션 빌드 결과
`-- package.json

app/
|-- api/          # FastAPI 엔드포인트
|-- core/         # 환경설정, 예외 처리
|-- db/           # DB 세션 및 마이그레이션
|-- ml/           # ML 특징 추출, 예측, 학습 진입점
|-- models/       # SQLAlchemy 모델
|-- schemas/      # 요청/응답 스키마
|-- services/     # 비즈니스 로직 및 외부 연동
`-- main.py       # FastAPI 진입점 및 React 빌드 제공
```

## Docker 실행

Docker Desktop이 실행 중이어야 합니다. 최초 실행 전 `.env`가 없다면 예제 파일을 복사하고 필요한 연동 키를 입력합니다.

Docker Compose는 FastAPI/React 애플리케이션과 PostgreSQL 17을 함께 실행합니다. 최초 실행 전 `.env`의 `POSTGRES_PASSWORD`를 로컬 기본값이 아닌 별도 비밀번호로 변경하세요.

```dotenv
POSTGRES_DB=decisionflow
POSTGRES_USER=decisionflow
POSTGRES_PASSWORD=change-this-password
```

Windows CMD:

```bat
copy .env.example .env
docker compose up --build
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

실행 후 `http://127.0.0.1:8001/`에서 화면을 확인하고 `http://127.0.0.1:8001/health`에서 컨테이너 상태를 확인합니다. 종료하려면 다음 명령을 사용합니다.

```bat
docker compose down
```

8001 포트를 이미 사용 중이면 다른 호스트 포트를 지정할 수 있습니다.

Windows CMD:

```bat
set APP_PORT=8011 && docker compose up --build
```

Windows PowerShell:

```powershell
$env:APP_PORT="8011"
docker compose up --build
```

기본 구성은 React를 빌드한 FastAPI 컨테이너와 PostgreSQL 컨테이너로 이루어집니다. PostgreSQL 데이터는 Docker의 `postgres_data` 볼륨에 저장되어 컨테이너를 다시 만들어도 유지됩니다. 데모 데이터를 추가하려면 실행 중인 컨테이너에서 다음 명령을 실행합니다. 같은 데모 데이터가 이미 있으면 중복 생성하지 않습니다.

```bat
docker compose exec decisionflow python -m scripts.seed_demo
```

데이터베이스까지 완전히 초기화할 때만 다음 명령을 사용합니다. 이 명령은 PostgreSQL 볼륨의 모든 데이터를 삭제합니다.

```bat
docker compose down -v
```

프론트엔드와 백엔드를 서로 다른 도메인에 배포할 때는 빌드 시 `VITE_API_BASE_URL`에 `/api`를 포함한 공개 Backend 주소를 지정합니다. 동일 도메인으로 제공할 때는 기본값 `/api`를 그대로 사용합니다.

```powershell
$env:VITE_API_BASE_URL="https://api.example.com/api"
docker compose build --no-cache
docker compose up
```

`.env`, 로컬 SQLite 파일, 가상환경, `node_modules`와 기존 빌드 결과는 `.dockerignore`에서 제외됩니다. `.env`는 이미지에 복사하지 않고 컨테이너 시작 시 `/app/.env`로 마운트됩니다. 실제 API 키와 PostgreSQL 비밀번호가 들어 있는 `.env`는 Git에 커밋하지 마세요.

## 로컬 실행

### 1. 가상환경 생성 및 활성화

Windows CMD:

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
```

`py` 명령을 찾을 수 없다면 Python 설치 후 터미널을 다시 열거나, 설치된 `python` 명령으로 `python -m venv .venv`를 실행합니다.

Windows PowerShell을 사용하는 경우 활성화 명령은 다음과 같습니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 패키지 설치

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 환경변수 설정

Windows CMD:

```bat
copy .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

`.env`의 기본값:

```dotenv
DATABASE_URL=sqlite:///./decisionflow.db
OPENAI_API_KEY=
TRANSCRIPTION_MODEL=gpt-transcribe
DECISION_ANALYSIS_MODEL=gpt-4o-mini
NOTION_API_KEY=
NOTION_DATABASE_ID=
SECRET_KEY=change-me
ML_MODEL_PATH=app/ml/models/delay_risk.joblib
```

로컬 개발에서는 별도 DB 설치 없이 SQLite 파일 `decisionflow.db`를 사용합니다. 실제 운영 환경에서는 `SECRET_KEY`를 충분히 긴 임의 값으로 교체해야 합니다.

음성 회의록 기능을 사용하려면 OpenAI Platform에서 발급한 API 키를 `.env`의 `OPENAI_API_KEY`에 입력합니다. 키는 따옴표 없이 입력하고 Git에 커밋하지 않습니다.

```dotenv
OPENAI_API_KEY=sk-...
TRANSCRIPTION_MODEL=gpt-transcribe
DECISION_ANALYSIS_MODEL=gpt-4o-mini
```

서버 실행 후 사이드바의 `설정` 화면에서도 OpenAI API Key, Notion API Key, Notion Database ID를 입력할 수 있습니다. 입력값은 비밀번호 필드로 가려지며 저장 후 실제 값은 화면이나 설정 조회 API로 다시 전송되지 않습니다. 빈 입력란은 기존 설정을 유지합니다.

설정 화면에서 저장한 값은 서버의 `.env`에 기록되고 현재 실행 중인 연동에도 즉시 반영됩니다. 현재 로컬 MVP에는 사용자 인증이 없으므로 외부 네트워크에 공개할 때는 설정 API에 관리자 인증을 먼저 적용해야 합니다.

PostgreSQL을 사용하려면 데이터베이스와 계정을 만든 뒤 `DATABASE_URL`을 실제 접속 정보로 변경합니다.

```dotenv
DATABASE_URL=postgresql+psycopg://사용자:비밀번호@localhost:5432/decisionflow
```

### 4. 서버 실행

React 프로덕션 빌드를 갱신합니다.

```bat
frontend-build.cmd
```

그다음 FastAPI를 실행하면 빌드된 React 화면과 API가 함께 제공됩니다.

```bat
python -m uvicorn app.main:app --reload --port 8001
```

프론트엔드를 수정하면서 즉시 확인하려면 FastAPI를 실행한 상태에서 새 CMD 창을 열고 React 개발 서버를 실행합니다.

```bat
frontend-dev.cmd
```

개발 서버 주소는 `http://127.0.0.1:5173`이며 `/api` 요청은 FastAPI의 8001번 포트로 전달됩니다.

데모 화면을 위한 샘플 데이터를 넣으려면 다음 명령을 한 번 실행합니다. 같은 데모 데이터가 이미 있으면 중복 생성하지 않습니다.

```bat
python -m scripts.seed_demo
```

서버 시작 시 SQLAlchemy 모델에 정의된 테이블이 자동 생성됩니다.

실행 후 확인 주소:

- DecisionFlow 화면: http://127.0.0.1:8001/
- API 상태: http://127.0.0.1:8001/health
- Swagger UI: http://127.0.0.1:8001/docs
- ReDoc: http://127.0.0.1:8001/redoc

상태 확인 예시:

```bat
curl http://127.0.0.1:8001/health
```

정상 응답:

```json
{
  "status": "ok"
}
```

## 주요 API

| 기능 | 메서드 | 경로 |
| --- | --- | --- |
| 상태 확인 | `GET` | `/health` |
| 프로젝트 관리 | `POST`, `GET` | `/api/projects` |
| 프로젝트 상세/수정/삭제 | `GET`, `PATCH`, `DELETE` | `/api/projects/{project_id}` |
| 회의 관리 및 검색 | `POST`, `GET` | `/api/meetings` |
| 회의 상세/수정/삭제 | `GET`, `PATCH`, `DELETE` | `/api/meetings/{meeting_id}` |
| 회의 분석 | `POST` | `/api/meetings/{meeting_id}/analyze` |
| 결정사항 후보 추출 | `POST` | `/api/meetings/{meeting_id}/decision-candidates` |
| 검토한 결정사항 확정 | `POST` | `/api/meetings/{meeting_id}/decisions/confirm` |
| 음성 파일 전사 | `POST` | `/api/transcriptions` |
| 결정사항 생성 | `POST` | `/api/decisions` |
| 프로젝트 결정사항 조회 | `GET` | `/api/projects/{project_id}/decisions` |
| Action Item 관리 | `POST`, `GET` | `/api/action-items` |
| Action Item 상세/수정/삭제 | `GET`, `PATCH`, `DELETE` | `/api/action-items/{action_item_id}` |
| 위험도 조회 | `GET` | `/api/action-items/{action_item_id}/risk` |
| 위험도 예측 | `POST` | `/api/action-items/{action_item_id}/predict-risk` |
| 프로젝트 위험 항목 조회 | `GET` | `/api/projects/{project_id}/risk-items` |
| Notion 연결 상태 | `GET` | `/api/notion/status` |
| Notion 연결 검증 | `POST` | `/api/notion/connect` |
| 데모 회의 일괄 전송 | `POST` | `/api/notion/sync-demo` |

요청 및 응답 필드의 전체 명세와 직접 실행 기능은 Swagger UI에서 확인할 수 있습니다.

## 음성 회의록

상단의 `음성 회의` 또는 `회의` → `+ 새 회의`를 선택하면 마이크로 바로 녹음하거나 기존 음성 파일을 첨부할 수 있습니다. 실시간 녹음은 시작, 일시정지, 재개, 정지와 미리듣기를 지원합니다. 녹음을 마친 뒤 `음성 전사`를 누르면 변환 결과가 회의 원문에 입력됩니다.

녹음을 종료하면 `저장` 버튼으로 브라우저에서 음성 원본을 내려받을 수 있습니다. 회의 창을 닫기 전에 필요한 원본을 저장하세요.

- 지원 형식: FLAC, MP3, MP4, MPEG, MPGA, M4A, OGG, WAV, WEBM
- 앱 업로드 최대 크기: 250MB
- 음성 파일은 모델의 토큰 한도를 넘지 않도록 서버에서 5분 단위 MP3로 자동 압축·분할한 뒤 순서대로 전사
- 전사는 화자 분리 모델을 사용하며 원문에 화자 번호와 발화 시간이 Markdown으로 기록됨
- 분할된 음성은 기본 3개씩 병렬 처리하며 `TRANSCRIPTION_CONCURRENCY`로 동시 처리 수를 조정할 수 있음
- 기본 모델: `gpt-transcribe`
- API 키는 서버의 `.env`에서만 사용되며 브라우저에는 전달되지 않습니다.
- 브라우저 마이크 권한이 필요하며 `localhost` 또는 HTTPS 환경에서 사용해야 합니다.
- 현재는 녹음 종료 후 전사합니다. 녹음 중 자막 형태의 스트리밍 전사는 후속 기능입니다.

## AI 결정사항 검토

회의 목록에서 `AI 결정 검토`를 누르면 회의 원문에서 명시적으로 합의, 승인, 선택된 내용만 후보로 추출합니다. 각 후보에는 결정 주제, 확정 내용, 원문 근거, AI 신뢰도가 표시됩니다.

1. 후보별 체크박스로 확정 대상을 선택합니다.
2. 필요한 경우 결정 주제와 확정 내용을 직접 수정합니다.
3. `선택 항목 확정`을 누르면 선택한 항목만 결정사항에 `confirmed` 상태로 저장됩니다.

제안, 질문, 검토 예정, 미해결 논의는 후보에서 제외하도록 구성했습니다. AI 결과를 바로 저장하지 않고 사용자가 검토한 뒤 확정하므로 원문 해석 오류를 최종 저장 전에 바로잡을 수 있습니다. 같은 회의에서 주제와 내용이 모두 동일한 항목은 중복 저장하지 않습니다.

## 프로젝트 상세

`프로젝트` 화면의 `프로젝트 열기`를 누르면 해당 프로젝트의 회의 기록, 진행 중인 Action Item, 확정된 결정사항을 한 화면에서 확인할 수 있습니다. 최근 13주의 회의, 업무, 결정 활동은 GitHub 기여도 그래프와 비슷한 활동 현황으로 표시됩니다.

회의 기록은 최신 일자부터 날짜별로 구분됩니다. 각 회의를 펼치면 회의 원문과 그 회의에서 생성된 결정 및 Action Item이 함께 표시됩니다.

회의 원문은 Markdown으로 저장하고 표시합니다. 회의 작성·수정 화면의 `작성`과 `미리보기` 탭에서 결과를 확인할 수 있으며 제목, 목록, 체크박스, 표, 인용문, 코드 블록과 링크 등 GitHub Flavored Markdown 문법을 지원합니다. 기존 일반 텍스트 회의록도 그대로 표시됩니다.

대시보드의 `최근 회의`, `주의할 업무`, `최근 결정사항`을 누르면 관련 프로젝트 상세로 바로 이동합니다. 출처 회의가 있는 항목은 해당 회의가 자동으로 펼쳐지고 선택한 업무 또는 결정이 강조 표시됩니다.

회의 안의 `Action Item 추가`를 사용하면 프로젝트와 출처 회의가 자동 연결됩니다. 프로젝트 상단의 `Action Item` 버튼은 특정 회의에 속하지 않는 프로젝트 공통 업무를 등록할 때 사용합니다.

### 모바일 앱 방향

현재 화면은 모바일 폭에 대응하며 모바일 브라우저에서도 녹음할 수 있습니다. 네이티브 앱을 추가할 때는 FastAPI API를 공통 백엔드로 유지하고 React Native 또는 Expo 클라이언트를 별도로 연결하는 구조를 권장합니다. 모바일 운영 환경에서는 마이크 권한 선언, 백그라운드 녹음 정책, HTTPS API 주소, 대용량 파일 분할 업로드를 추가로 구성해야 합니다.

## Notion 동기화

`.env`에 Integration Token과 회의 데이터베이스 ID를 설정하고, 해당 데이터베이스를 Integration에 연결합니다.

```dotenv
NOTION_API_KEY=ntn_...
NOTION_DATABASE_ID=...
NOTION_API_VERSION=2026-03-11
```

회의 목록의 `Notion 전송` 버튼으로 개별 회의를 보낼 수 있습니다. 전송된 페이지에는 회의 요약, 핵심 쟁점, 미결 사항, 결정사항, 후속 액션만 포함되며 회의 원문은 전송하지 않습니다. 성공한 회의는 앱 DB에 Notion 페이지 ID와 `SYNCED` 상태를 기록하므로 같은 회의를 다시 전송해도 중복 페이지를 만들지 않습니다.

시드로 만든 데모 회의를 한 번에 전송하려면 다음 API를 사용합니다.

```bat
curl -X POST http://127.0.0.1:8001/api/notion/sync-demo
```

## 위험 점수 규칙

Action Item의 위험 점수는 현재 다음 규칙을 합산합니다.

- 마감일 초과: `+40`
- 높은 우선순위: `+20`
- 3일 이상 상태 변경 없음: `+20`

점수 구간은 `0~30` 낮음, `31~60` 보통, `61 이상` 높음으로 분류합니다. ML 모델이 준비되기 전까지 예측 API는 이 규칙 점수를 확률 형태로 반환합니다.

## DB 마이그레이션

개발 초기에는 서버 시작 시 테이블을 자동 생성합니다. 스키마 변경 이력을 관리할 때는 Alembic 리비전을 생성하고 적용합니다.

```bat
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## 개발 상태

- AI 결정사항 추출과 사용자 검토/확정 흐름이 구현되어 있습니다.
- Notion API는 연결 정보와 동기화 흐름을 위한 기본 구현 상태입니다.
- ML 학습 파이프라인과 실제 모델 파일은 후속 단계에서 추가합니다.

## UX/UI 설계

화면 구성, 데이터 기준과 후속 구현 범위는 [UX/UI 설계 문서](docs/UX-UI-design.md)를 참고하세요.
