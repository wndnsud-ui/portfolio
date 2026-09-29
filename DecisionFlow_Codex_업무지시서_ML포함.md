# DecisionFlow 개발 업무지시서

## 1. 프로젝트 개요

### 프로젝트명
**DecisionFlow**

### 프로젝트 한 줄 정의
회의록을 저장·조회하고, AI가 회의에서 결정사항과 Action Item을 구조화하며, 사용자가 원할 경우 최종 회의록을 Notion Database로 전송할 수 있는 FastAPI 기반 서비스.

향후 Action Item 이력이 충분히 축적되면 머신러닝을 활용하여 **업무 지연 위험도 예측 기능**까지 확장한다.

---

## 2. 프로젝트 모티브

이 프로젝트는 AI 회의록 서비스 **다글로(Daglo)**에서 아이디어를 얻었다.

단, 다글로의 기능이나 UI를 그대로 복제하는 것이 목적은 아니다.

다글로가 개별 회의의 녹취·요약·정리에 강점을 둔다면 DecisionFlow는 다음에 더 집중한다.

- 회의록 자체 저장
- 프로젝트별 회의 이력 관리
- 결정사항 관리
- Action Item 관리
- 이전 회의와 현재 회의의 연결
- 결정 변경 이력 관리
- 회의 기록 검색
- Notion Database 연동
- Action Item 지연 위험 분석 및 향후 머신러닝 예측

핵심 철학은 다음과 같다.

> 회의를 기록하는 것에서 끝내지 않고, 회의에서 무엇이 결정되었고 이후 어떤 실행이 필요한지를 관리한다.

---

# 3. 개발 우선순위

이 프로젝트에서 가장 중요한 것은 **FastAPI 백엔드 구조와 PostgreSQL 데이터 설계**다.

개발 우선순위는 아래 순서를 따른다.

1. FastAPI 아키텍처
2. PostgreSQL 데이터 모델
3. API 구조
4. 회의록 저장 및 조회
5. AI 분석
6. 결정사항 / Action Item 구조화
7. Notion 연동
8. Rule-Based Risk Score
9. 머신러닝 지연 위험 예측
10. 프론트엔드 고도화

프론트엔드는 과도하게 복잡하게 만들지 않는다.

---

# 4. 기술 스택

## Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Alembic
- PostgreSQL
- Uvicorn

## AI

- OpenAI API
- AI 호출 로직은 FastAPI Router에 직접 작성하지 않는다.
- 별도의 `ai_service.py`에서 관리한다.

## Machine Learning

초기 MVP에서는 머신러닝 모델을 바로 학습하지 않는다.

1차 구현:
- Rule-Based Risk Score

향후 고도화:
- Logistic Regression
- Random Forest
- Gradient Boosting 계열 중 데이터 규모에 적합한 모델 검토

ML 관련 코드는 FastAPI Router와 분리한다.

예:

```text
ml/
├── train.py
├── features.py
├── predictor.py
└── models/
```

서비스 호출은:

```text
services/
└── ml_service.py
```

를 통해 수행한다.

## External Integration

- Notion API

## Frontend

React 또는 Next.js 사용 가능.

프론트엔드는 가능한 단순하게 구성하고, 프로젝트의 핵심은 백엔드와 데이터 구조에 둔다.

---

# 5. UI 디자인 기준

기존 개인 프로젝트 **MoodCode 수준의 단순한 UI**를 기준으로 한다.

- 복잡한 애니메이션 금지
- 과도한 인터랙션 금지
- 대형 타이포 최소화
- 카드 중심 UI
- 충분한 여백
- 오프화이트 계열 배경
- 흰색 카드
- 얇은 border
- 작은 radius
- 명확한 정보 위계
- 모바일 대응
- 데스크톱 우선 설계

Tailwind CSS 사용 가능.

목표:

> Notion과 Linear 사이 정도의 단정한 업무도구 느낌.

특정 서비스 UI를 그대로 복제하지 않는다.

---

# 6. 핵심 사용자 시나리오

## Scenario 1 — 프로젝트 생성

사용자는 먼저 프로젝트를 생성한다.

예:

```text
프로젝트명
FastAPI Portfolio

설명
FastAPI 기반 개인 프로젝트 개발
```

프로젝트 하위에 여러 개의 회의가 누적될 수 있다.

## Scenario 2 — 회의록 등록

사용자는 회의를 생성한다.

입력값:

- 회의 제목
- 프로젝트
- 회의 날짜
- 참석자
- 회의 원문

초기 MVP에서는 음성 파일 업로드 및 STT 기능을 구현하지 않는다.

입력 데이터는 다음만 지원한다.

- 직접 텍스트 입력
- TXT
- Markdown

향후 음성 업로드 기능을 확장할 수 있도록 구조만 고려한다.

---

# 7. 데이터 저장 원칙

회의록과 모든 핵심 서비스 데이터는 PostgreSQL에 저장한다.

Notion은 메인 데이터 저장소로 사용하지 않는다.

### 원칙

```text
PostgreSQL = Source of Truth
Notion = 외부 Publish / Sync Destination
```

모든 서비스 데이터의 기준은 PostgreSQL이다.

---

# 8. AI 회의 분석

사용자가 회의록 저장 후 `AI 분석` 버튼을 선택하면 회의 내용을 분석한다.

최소 다음 내용을 추출한다.

### Summary
회의 전체 요약

### Discussion
주요 논의사항

### Decisions
실제로 결정된 내용

### Action Items

```json
{
  "task": "DB Schema 설계",
  "assignee": "혜영",
  "due_date": "2026-10-02",
  "status": "todo"
}
```

### Undecided Topics
논의는 되었지만 결정되지 않은 내용

---

# 9. AI 결과 검토 구조

AI 분석 결과를 바로 확정 데이터로 처리하지 않는다.

```text
AI ANALYZED
↓
DRAFT
↓
USER REVIEW
↓
CONFIRMED
```

사용자는 AI가 추출한 다음 항목을 수정할 수 있어야 한다.

- Summary
- Decision
- Action Item
- 담당자
- 기한
- 우선순위

사용자가 `확정` 버튼을 눌러야 최종 데이터로 사용한다.

---

# 10. Decision 관리

Decision은 별도 엔터티로 관리한다.

Meeting 내용 안에 단순 텍스트로만 저장하지 않는다.

예:

```text
Decision
Topic: Backend Framework
Value: FastAPI
Status: Confirmed
Meeting: 2026-09-28 MVP 기획회의
```

---

# 11. Decision History

프로젝트 진행 중 기존 결정이 변경될 수 있다.

```text
2026-09-20
Flask 검토
↓
2026-09-28
FastAPI 확정
```

DecisionHistory 필드:

- id
- decision_id
- previous_value
- new_value
- changed_at
- meeting_id

MVP에서는 단순 비교 수준으로 구현하고, 향후 AI 기반 변경 탐지로 확장 가능하게 한다.

---

# 12. Action Item 관리

Action Item은 별도 엔터티로 만든다.

필드 예시:

```text
id
project_id
meeting_id
task
assignee
due_date
status
priority
risk_score
risk_level
created_at
updated_at
completed_at
```

Status:

```text
todo
in_progress
done
cancelled
```

Priority:

```text
low
medium
high
```

Risk Level:

```text
low
medium
high
```

프로젝트별, 회의별, 상태별, 담당자별 조회가 가능해야 한다.

---

# 13. 앱 내부 회의록 보관

DecisionFlow 자체가 회의 저장소 역할을 해야 한다.

Notion을 사용하지 않더라도 서비스가 정상적으로 작동해야 한다.

사용자는 앱 안에서 언제든 과거 회의를 조회할 수 있어야 한다.

---

# 14. 검색

앱 내부에서 회의 검색을 지원한다.

MVP에서는 PostgreSQL 기반 일반 텍스트 검색으로 구현한다.

검색 대상:

- 회의 제목
- Summary
- Discussion
- Decision
- Action Item
- Transcript

향후 확장:

```text
일반 검색
↓
PostgreSQL Full Text Search
↓
Vector Search
↓
의미 기반 검색
```

Vector DB / RAG는 초기 MVP 범위에서 제외한다.

---

# 15. 주요 화면

## 15.1 Dashboard

표시 항목:

- 전체 프로젝트 수
- 최근 회의
- 이번 주 회의 수
- 미완료 Action Item
- 최근 결정사항
- 지연 위험 Action Item

```text
Dashboard

Projects          3
Meetings         12
Open Tasks        7
High Risk Tasks   2
```

## 15.2 Projects

각 프로젝트 카드에:

- 프로젝트명
- 최근 회의일
- 회의 수
- 미완료 Action Item 수
- High Risk Action Item 수

## 15.3 Project Detail

- 최근 회의
- 현재 Decision
- Action Item
- 지연 위험 업무

## 15.4 Meetings

회의 목록.
검색 및 프로젝트 Filter 제공.

## 15.5 Meeting Detail

```text
회의 제목
날짜
프로젝트
참석자

Summary
Discussion
Decisions
Action Items
Original Transcript
Notion Sync
```

Original Transcript는 기본적으로 접혀 있어도 된다.

## 15.6 Action Items

Filter:

- Project
- Status
- Assignee
- Due Date
- Risk Level

## 15.7 Decisions

프로젝트별 결정사항 조회.
향후 DecisionHistory 타임라인 추가 가능.

---

# 16. Notion 연동

Notion은 선택 기능이다.

Notion을 연결하지 않은 사용자도 모든 핵심 기능을 사용할 수 있어야 한다.

초기 개인 프로젝트에서는 개발자 개인 Integration Token 기반 방식으로 시작 가능하다.

향후 Multi-user OAuth 방식으로 확장할 수 있도록 Notion Service를 별도 모듈로 분리한다.

```text
services/
notion_service.py
```

---

# 17. Notion Database 구조

## Meeting Database

Properties:

```text
Title
Project
Meeting Date
Status
Participants
Decision Count
Open Action Count
```

페이지 본문:

```text
Summary
Discussion
Decisions
Action Items
Original Transcript
```

## Action Item Database

Properties:

```text
Task
Project
Meeting
Assignee
Due Date
Status
Priority
Risk Level
```

---

# 18. Notion 전송

Meeting Detail에 다음 버튼을 제공한다.

```text
[Notion으로 보내기]
```

동작 흐름:

```text
PostgreSQL
↓
FastAPI
↓
Notion Formatter
↓
Notion API
↓
Notion Database
```

---

# 19. Notion Sync 상태

각 Meeting에 다음 상태를 관리한다.

```text
NOT_CONNECTED
NOT_SYNCED
SYNCED
OUTDATED
ERROR
```

회의록이 Notion에 전송된 이후 앱에서 변경되면 `OUTDATED` 상태로 변경한다.

초기 MVP에서는 양방향 동기화하지 않는다.

```text
DecisionFlow → Notion
```

단방향 Sync만 구현한다.

---

# 20. Rule-Based Risk Score

머신러닝 학습 데이터가 충분하지 않은 초기 단계에서는 Rule-Based 방식으로 Action Item 위험도를 계산한다.

예시 규칙:

```text
마감일 초과                  +40
우선순위 HIGH                +20
3일 이상 상태 변경 없음      +20
과거 지연률 높음             +20
```

점수 예:

```text
0 ~ 30   LOW
31 ~ 60  MEDIUM
61 ~ 100 HIGH
```

해당 규칙은 Service Layer로 분리한다.

```text
services/
risk_service.py
```

Rule 기반 점수 계산과 향후 ML 모델 예측을 동일한 인터페이스로 교체할 수 있도록 설계한다.

---

# 21. 머신러닝 고도화

충분한 Action Item 완료 이력이 축적된 이후 머신러닝 기능을 추가한다.

## ML 목표

> Action Item이 기한 내 완료되지 못할 가능성을 예측한다.

초기에는 Binary Classification 문제로 설계한다.

```text
0 = 기한 내 완료
1 = 지연 완료 또는 미완료
```

---

# 22. 머신러닝 Feature 후보

```text
days_until_due
priority
task_age_days
days_without_status_change
project_duration
open_task_count
assignee_open_task_count
previous_delay_rate
meeting_frequency
decision_change_count
```

텍스트 자체를 처음부터 모델에 직접 넣지 않는다.

초기에는 구조화된 수치/범주형 데이터 중심으로 시작한다.

---

# 23. ML 모델 후보

우선순위:

1. Logistic Regression
2. Decision Tree
3. Random Forest
4. Gradient Boosting 계열

딥러닝은 사용하지 않는다.

데이터 규모와 문제 복잡도가 충분하지 않으면 복잡한 모델을 사용하지 않는다.

---

# 24. ML 평가

최소 다음 지표를 확인한다.

- Accuracy
- Precision
- Recall
- F1 Score
- Confusion Matrix

업무 지연 탐지 목적상 Accuracy만 보지 않는다.

실제 지연 업무를 놓치지 않는 것이 중요한 경우 Recall을 함께 확인한다.

---

# 25. ML Prediction API

```http
POST /api/action-items/{action_item_id}/predict-risk
GET /api/projects/{project_id}/risk-items
```

응답 예:

```json
{
  "action_item_id": 12,
  "delay_probability": 0.73,
  "risk_level": "high",
  "model_version": "v1"
}
```

Prediction 결과에는 모델 버전을 함께 저장한다.

---

# 26. PostgreSQL Data Model

최소 엔터티:

```text
User
Project
Meeting
Transcript
MeetingSummary
Decision
DecisionHistory
ActionItem
NotionConnection
NotionSyncLog
```

향후 ML 기능 추가 시:

```text
ActionItemPrediction
```

추가.

관계 예:

```text
User
 └── Project
      ├── Meeting
      │    ├── Transcript
      │    ├── MeetingSummary
      │    ├── Decision
      │    └── ActionItem
      └── Decision
           └── DecisionHistory

ActionItem
 └── ActionItemPrediction
```

---

# 27. FastAPI Architecture

```text
app/

├── main.py
├── api/
│   ├── projects.py
│   ├── meetings.py
│   ├── decisions.py
│   ├── action_items.py
│   ├── risk.py
│   └── notion.py
├── models/
├── schemas/
├── services/
│   ├── ai_service.py
│   ├── meeting_service.py
│   ├── decision_service.py
│   ├── notion_service.py
│   ├── risk_service.py
│   └── ml_service.py
├── repositories/
├── ml/
│   ├── train.py
│   ├── features.py
│   ├── predictor.py
│   └── models/
├── db/
│   ├── base.py
│   ├── session.py
│   └── migrations/
└── core/
    ├── config.py
    ├── security.py
    └── exceptions.py
```

Router / Schema / Model / Service 역할은 분리한다.

---

# 28. 주요 API 예시

## Projects

```http
POST /api/projects
GET /api/projects
GET /api/projects/{project_id}
PATCH /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

## Meetings

```http
POST /api/meetings
GET /api/meetings
GET /api/meetings/{meeting_id}
PATCH /api/meetings/{meeting_id}
DELETE /api/meetings/{meeting_id}
```

## AI

```http
POST /api/meetings/{meeting_id}/analyze
```

## Decisions

```http
GET /api/projects/{project_id}/decisions
GET /api/decisions/{decision_id}
PATCH /api/decisions/{decision_id}
```

## Action Items

```http
GET /api/action-items
POST /api/action-items
PATCH /api/action-items/{action_item_id}
DELETE /api/action-items/{action_item_id}
```

## Risk

```http
GET /api/action-items/{action_item_id}/risk
POST /api/action-items/{action_item_id}/predict-risk
GET /api/projects/{project_id}/risk-items
```

## Notion

```http
GET /api/notion/status
POST /api/notion/connect
POST /api/meetings/{meeting_id}/notion-sync
GET /api/meetings/{meeting_id}/notion-sync-status
```

---

# 29. FastAPI 기능 적극 활용

반드시 고려할 항목:

- APIRouter
- Dependency Injection
- Pydantic Validation
- Response Model
- Exception Handling
- async endpoint
- Background Task 활용 가능 여부
- Middleware
- CORS
- OpenAPI / Swagger
- 환경변수 관리
- DB Session Dependency

Swagger `/docs`에서 API 테스트가 가능하도록 유지한다.

---

# 30. 에러 처리

예:

```text
AI_ANALYSIS_ERROR
NOTION_CONNECTION_ERROR
NOTION_SYNC_ERROR
ML_PREDICTION_ERROR
INVALID_MEETING
PROJECT_NOT_FOUND
ACTION_ITEM_NOT_FOUND
```

일관된 API Error Response 구조를 사용한다.

---

# 31. 환경변수

`.env`

```text
DATABASE_URL=
OPENAI_API_KEY=
NOTION_API_KEY=
NOTION_DATABASE_ID=
SECRET_KEY=
ML_MODEL_PATH=
```

API Key를 코드에 직접 작성하지 않는다.

`.env`는 Git에 커밋하지 않는다.
`.env.example` 파일 제공.

---

# 32. 개발 단계

## Phase 1 — FastAPI + PostgreSQL

- 프로젝트 CRUD
- 회의 CRUD
- Action Item CRUD
- Decision CRUD
- DB Migration
- Swagger 확인

## Phase 2 — Frontend

- Dashboard
- Projects
- Meetings
- Meeting Detail
- Action Items
- Decisions

## Phase 3 — AI 분석

- Summary
- Discussion
- Decisions
- Action Items
- Undecided Topics
- 사용자 검토 / 확정

## Phase 4 — Decision History

- 과거 Decision 비교
- 변경 이력 저장
- 프로젝트 Decision Timeline

## Phase 5 — Notion Integration

- Notion 연결
- Meeting DB 생성 또는 연결
- Action Item DB 생성 또는 연결
- 회의록 Publish
- Sync 상태 관리

## Phase 6 — Rule-Based Risk Score

- Action Item 위험도 계산
- Dashboard Risk 표시
- 프로젝트별 High Risk 조회

## Phase 7 — Machine Learning

충분한 학습 데이터가 확보된 경우에만 진행한다.

- Feature Engineering
- 학습 데이터셋 생성
- Logistic Regression baseline
- 평가
- 모델 저장
- FastAPI Prediction API 연결
- Rule-Based 방식과 비교

---

# 33. MVP 성공 기준

```text
프로젝트 생성
↓
회의록 등록
↓
앱 내부 저장
↓
AI 분석
↓
결정사항 / Action Item 확인
↓
사용자 수정
↓
확정
↓
앱에서 언제든 다시 조회
↓
필요한 회의록만 Notion으로 전송
```

여기까지가 핵심 MVP다.

Rule-Based Risk Score와 머신러닝은 MVP 이후 확장 기능으로 취급한다.

---

# 34. 이번 MVP에서 제외

- 실시간 음성 녹음
- STT 직접 구현
- 화자 음성 인식
- Slack 연동
- Google Calendar 연동
- Email 발송
- 실시간 공동편집
- 복잡한 권한 시스템
- Notion 양방향 동기화
- Vector DB
- RAG
- 딥러닝 기반 예측
- 모바일 Native App
- 과도한 UI 애니메이션

---

# 35. 개발 시 중요 원칙

1. 프론트엔드보다 백엔드 설계를 우선한다.
2. PostgreSQL을 서비스의 기준 DB로 사용한다.
3. Notion은 선택적 외부 연동 기능으로 사용한다.
4. AI 호출 코드를 Router에서 분리한다.
5. ML 기능도 Router와 분리한다.
6. 외부 API 호출 실패를 고려한다.
7. DB 모델 간 관계를 명확하게 설계한다.
8. 코드 구조를 읽기 쉽게 유지한다.
9. MVP 범위 밖 기능을 임의로 추가하지 않는다.
10. 데이터가 충분하지 않으면 머신러닝을 억지로 적용하지 않는다.
11. 초기에는 Rule-Based Risk Score를 사용한다.
12. 각 Phase 완료 후 실행 가능한 상태를 유지한다.

---

# 36. 작업 시작 순서

### Step 1
현재 Repository 구조 분석

### Step 2
Backend / Frontend Directory 구조 제안

### Step 3
PostgreSQL ERD 및 Model 설계

### Step 4
FastAPI API 명세 설계

### Step 5
Phase 1 구현

### Step 6
실행 및 오류 점검

### Step 7
Phase 2 이후 순차 진행

### Step 8
MVP 완성 후 Rule-Based Risk Score 추가

### Step 9
충분한 데이터가 확보된 이후 ML 적용 검토

기존 코드가 있는 경우 기존 구조를 최대한 보존하고 필요한 부분만 수정한다.

대규모 리팩터링이 필요한 경우 임의로 진행하지 말고 먼저 문제점과 변경 범위를 정리한다.

---

# 37. 최종 프로젝트 방향 요약

DecisionFlow는 단순 AI 회의록 생성기가 아니다.

```text
회의록
↓
FastAPI
↓
PostgreSQL
↓
AI 구조화
↓
Decision / Action Item
↓
사용자 검토
↓
앱 내부 누적 관리
↓
Notion 선택적 동기화
↓
Rule-Based Risk Score
↓
데이터 축적
↓
Machine Learning 기반 지연 위험 예측
```

프로젝트의 중심은 끝까지 **FastAPI + PostgreSQL 기반 서비스 설계**이며, AI, Notion, 머신러닝은 이 핵심 서비스 구조 위에 단계적으로 추가한다.
