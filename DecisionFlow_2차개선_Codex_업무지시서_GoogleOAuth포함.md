# DecisionFlow 2차 개선 및 재배포 업무지시서 (Google OAuth 포함)

## 0. 가장 중요한 원칙

이 작업은 **기존 DecisionFlow 프로젝트를 새로 만드는 작업이 아니다.**

현재 로컬 및 Docker/Railway 배포까지 완료된 기존 프로젝트를 기준으로,
기능을 보완하고 다시 배포하는 것이 목적이다.

### 절대 금지
- 기존 프로젝트 전체 재작성
- 현재 동작하는 FastAPI 구조를 이유 없이 교체
- DB 구조 전체 초기화
- 기존 API 삭제 후 새 API로 전면 교체
- 기존 Docker 배포 구조 파괴
- 프론트엔드 전체 갈아엎기
- MVP 범위를 임의로 대폭 확장

### 작업 원칙
1. 현재 Repository 구조를 먼저 분석한다.
2. 기존 코드에서 재사용 가능한 부분을 최대한 유지한다.
3. 변경이 필요한 부분만 최소 단위로 수정한다.
4. DB migration이 필요한 경우 기존 데이터 보존을 전제로 한다.
5. 각 단계 완료 후 기존 기능이 정상 작동하는지 확인한다.
6. 최종적으로 Docker 이미지 재빌드 → Docker Hub push → Railway 재배포가 가능해야 한다.

---

# 1. 이번 개선의 핵심 목표

이번 버전의 핵심은 아래 5가지다.

## 목표 1. 회원가입 시 사용자별 API / Notion 설정 저장

회원가입 또는 최초 설정 과정에서 사용자가 다음 정보를 한 번에 저장할 수 있도록 한다.

- OpenAI API Key
- Notion API Key
- Notion Database ID
- 필요 시 기타 사용자별 외부 서비스 설정

회원가입 시 입력한 설정은 **회원 계정과 연결하여 저장**한다.

로그아웃 후 다시 로그인하더라도 같은 사용자가 다시 API Key와 Notion 설정을 입력하지 않아도 되도록 한다.

## 목표 2. 로그인 시 회원별 설정 자동 복원

로그인 성공 후 서버에서 해당 회원의 설정을 조회하여 앱에서 자동으로 사용할 수 있도록 한다.

```text
회원가입
↓
API Key / Notion 정보 입력
↓
계정 생성
↓
설정 저장
↓
로그아웃
↓
다시 로그인
↓
기존 설정 자동 로드
↓
즉시 AI / Notion 기능 사용
```

사용자가 매번 설정 화면에서 다시 API Key를 입력해야 하는 현재 구조는 개선한다.

단, 설정 화면에서는 기존 값을 수정하거나 재연결할 수 있어야 한다.

## 목표 3. 모든 기록을 회원 계정에 연결

회의록, 프로젝트, Action Item, Decision 등 사용자가 생성한 모든 데이터를 반드시 해당 사용자 계정과 연결한다.

즉 다음 상황에서도 데이터가 유지되어야 한다.

- 로그아웃
- 브라우저 종료
- 다른 기기에서 로그인
- 다시 접속
- 서버 재시작

### 데이터 소유 관계 예시

```text
User
 │
 ├── AuthAccounts
 │
 ├── UserSettings
 │
 ├── Projects
 │     └── Meetings
 │           ├── Decisions
 │           └── ActionItems
 │
 └── BlogPosts
```

모든 조회 API는 로그인한 사용자 기준으로 데이터를 반환해야 한다.

다른 회원의 데이터가 노출되지 않도록 한다.

## 목표 4. Google OAuth 로그인 추가

기존 이메일/비밀번호 로그인은 유지한다.

추가로 **Google OAuth 2.0 / OpenID Connect 로그인**을 지원한다.

사용자 경험:

```text
로그인

[ Google로 계속하기 ]

──────── 또는 ────────

이메일
비밀번호
[로그인]
```

회원가입 화면에서도 동일하게:

```text
[ Google 계정으로 시작 ]

또는

이메일 / 비밀번호 회원가입
```

Google 로그인 성공 시:

1. Google 사용자 고유 ID와 이메일을 확인한다.
2. 기존 회원이면 로그인 처리한다.
3. 신규 회원이면 DecisionFlow User 계정을 자동 생성한다.
4. UserSettings는 기존 회원 설정 구조를 그대로 사용한다.
5. OpenAI / Notion 설정은 Google 계정이 아니라 DecisionFlow User에 연결한다.
6. 로그인 후 기존 회의록, 프로젝트, 블로그 기록을 자동 조회한다.

Google OAuth는 기존 인증 체계에 **추가**하는 기능이며,
기존 인증 기능을 삭제하거나 전면 재작성하지 않는다.

## 목표 5. 기술 블로그 기능 추가

DecisionFlow에서 작성하거나 정리한 내용을 기술 블로그 콘텐츠로 변환하고 배포할 수 있도록 한다.

블로그는 단순 외부 링크가 아니라 DecisionFlow 내부 기능으로 구현한다.

초기 목표:

```text
회의록 / 프로젝트 기록 / 학습 정리
↓
블로그 초안 생성
↓
사용자 수정
↓
게시
↓
공개 블로그 화면 노출
```

향후 Notion에 저장된 내용을 가져와 블로그 초안으로 변환하는 기능도 고려한다.

---

# 2. 현재 프로젝트의 역할 유지

DecisionFlow의 핵심 정체성은 변경하지 않는다.

> 회의와 프로젝트에서 발생한 기록을 저장하고,
> AI를 이용해 결정사항 및 Action Item을 구조화하며,
> 필요 시 Notion으로 전송하고,
> 이후 실행 흐름을 관리하는 서비스.

이번 업데이트는 이 핵심 서비스 위에
**회원별 개인 워크스페이스 + Google 로그인 + 블로그 발행 기능**을 추가하는 작업이다.

---

# 3. 회원 시스템

## 3.1 회원가입

회원가입 화면에는 최소 다음 필드를 제공한다.

```text
이메일
비밀번호
닉네임
```

추가 설정 섹션:

```text
OpenAI API Key
Notion API Key
Notion Database ID
```

API 관련 값은 회원가입 시 선택 입력 가능하게 한다.

즉 API Key가 없어도 회원가입 자체는 가능해야 한다.

회원가입 이후 설정 화면에서 추가할 수도 있어야 한다.

## 3.2 로그인

로그인 방식:

```text
1. Google OAuth
2. Email / Password
```

로그인 성공 후 인증 토큰을 사용하여 현재 사용자를 식별한다.

FastAPI 인증 구조를 명확하게 분리한다.

예:

```text
api/auth.py
services/auth_service.py
services/google_oauth_service.py
core/security.py
```

## 3.3 인증 API

기존 이메일/비밀번호 로그인:

```http
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
POST /api/auth/logout
```

필요 시:

```http
POST /api/auth/refresh
```

Google OAuth:

```http
GET /api/auth/google/login
GET /api/auth/google/callback
```

필요하다면 OAuth 완료 후 Frontend로 redirect한다.

---

# 4. Google OAuth 데이터 구조

Google 관련 필드를 User에 직접 넣는 방식보다,
향후 다른 Social Login 추가가 가능하도록 `AuthAccount` 테이블을 분리하는 것을 우선 검토한다.

예:

```text
AuthAccount

id
user_id
provider
provider_account_id
provider_email
created_at
updated_at
```

예시:

```text
provider = google
provider_account_id = Google sub
```

향후 다음과 같은 로그인 확장 가능:

```text
google
github
kakao
naver
```

단, 현재 MVP에서는 Google만 구현한다.

---

# 5. Google OAuth 환경변수

배포 환경에서는 다음 환경변수를 사용한다.

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
```

로컬 예시:

```text
http://localhost:8001/api/auth/google/callback
```

배포 예시:

```text
https://decisionflow-production.up.railway.app/api/auth/google/callback
```

환경별 Redirect URI를 명확하게 구분한다.

실제 secret 값은 코드에 하드코딩하지 않는다.

---

# 6. 사용자 설정 저장

## UserSettings 모델

사용자별 설정을 별도 엔터티로 분리한다.

예:

```text
UserSettings

id
user_id
openai_api_key_encrypted
notion_api_key_encrypted
notion_database_id
created_at
updated_at
```

## 매우 중요: API Key 평문 저장 금지

OpenAI / Notion API Key를 DB에 평문으로 저장하지 않는다.

서버의 `SECRET_KEY` 또는 별도 암호화 키를 이용하여 암호화 저장한다.

가능하면 Fernet 등 검증된 방식을 사용한다.

```text
사용자 입력
↓
FastAPI
↓
암호화
↓
DB 저장
↓
필요한 API 호출 시 복호화
↓
외부 API 요청
```

API 응답에서는 전체 Key를 반환하지 않는다.

설정 화면에는 masking만 제공한다.

예:

```text
OpenAI API Key
sk-••••••••••••••93kd

Notion API Key
ntn_••••••••••••••32sa
```

---

# 7. 사용자 설정 API

최소 다음 API를 제공한다.

```http
GET   /api/settings
PATCH /api/settings
POST  /api/settings/test-openai
POST  /api/settings/test-notion
```

`GET /api/settings`에서는 실제 secret 값을 반환하지 않는다.

예:

```json
{
  "openai_connected": true,
  "notion_connected": true,
  "notion_database_id": "...",
  "openai_key_masked": "sk-••••••••93kd",
  "notion_key_masked": "ntn_••••••32sa"
}
```

---

# 8. 로그인 후 설정 자동 복원

로그인 성공 후 다음 흐름으로 진행한다.

```text
로그인
↓
GET /api/auth/me
↓
GET /api/settings
↓
사용자 설정 상태 확인
↓
AI / Notion 기능 사용 가능 여부 반영
```

실제 secret 값은 프론트로 재전송하지 않아도 된다.

프론트에는 연결 여부와 masking 정보만 제공한다.

---

# 9. 회원별 데이터 영속성

현재 회의록/프로젝트 기록이 브라우저 상태나 임시 데이터에 의존하고 있다면 서버 DB 중심 구조로 변경한다.

## 모든 핵심 엔터티에 user_id 연결

최소:

```text
Project.user_id
Meeting.user_id 또는 Project를 통한 소유권
ActionItem.user_id 또는 Project를 통한 소유권
Decision.user_id 또는 Project를 통한 소유권
BlogPost.user_id
```

중복 user_id가 불필요한 경우 관계를 통한 ownership으로 처리 가능하나,
권한 검증이 명확해야 한다.

---

# 10. 로그인 후 데이터 조회

로그인 성공 시 Dashboard에서 자동으로 현재 사용자의 데이터를 조회한다.

```text
로그인
↓
GET /api/auth/me
↓
GET /api/projects
GET /api/meetings
GET /api/action-items
↓
Dashboard 표시
```

localStorage를 서비스 원본 DB처럼 사용하지 않는다.

localStorage는 인증 토큰 또는 최소한의 UI 상태 저장에만 사용한다.

---

# 11. 데이터 접근 권한

모든 사용자 데이터 API에서 ownership 검증을 수행한다.

예:

```text
User A의 Meeting ID = 10
User B가 /api/meetings/10 요청
↓
403 또는 404
```

다른 사용자 데이터를 ID만 알고 있다고 조회할 수 없어야 한다.

---

# 12. 데이터베이스

프로토타입에서 SQLite를 사용 중이라면,
회원별 데이터와 설정을 영구 보관하기 위해 PostgreSQL 전환을 우선 검토한다.

## 원칙

```text
PostgreSQL = 서비스 Source of Truth
Notion = 선택적 외부 Sync Destination
```

Railway PostgreSQL을 사용할 수 있도록 구성한다.

기존 SQLite 데이터가 있다면 migration 또는 초기 데이터 이전 방법을 문서화한다.

---

# 13. 블로그 기능

이번 버전에서 블로그 기능의 기본 골격을 추가한다.

## 목적

사용자가 DecisionFlow 안에서 정리한:

- 회의 기록
- 기술 프로젝트 기록
- 학습 기록
- AI 분석 결과
- Notion 정리 내용

등을 기술 블로그 글로 재구성하여 게시할 수 있도록 한다.

---

# 14. BlogPost 모델

```text
BlogPost

id
user_id
title
slug
summary
content
category
tags
thumbnail_url
status
source_type
source_id
published_at
created_at
updated_at
```

Status:

```text
draft
review
published
```

Source Type:

```text
meeting
project
notion
manual
```

---

# 15. 블로그 작성 흐름

기본 흐름:

```text
회의록 또는 프로젝트 기록 선택
↓
[블로그 글 만들기]
↓
AI가 블로그 초안 생성
↓
편집 화면
↓
사용자 수정
↓
미리보기
↓
게시
```

AI가 자동으로 공개 게시하지 않는다.

최종 게시 버튼은 반드시 사용자가 직접 누른다.

---

# 16. 블로그 AI 생성

사용자가 콘텐츠 유형을 선택할 수 있도록 한다.

예:

```text
기술 블로그
개발 회고
학습 기록
프로젝트 진행기
튜토리얼
```

기술 블로그 형식 예:

```text
제목
도입
문제 또는 학습 배경
핵심 개념
구현 과정
코드 / 예시
문제 및 해결
배운 점
마무리
```

원문의 사실관계를 유지하고,
AI가 존재하지 않는 기술 사실이나 개발 경험을 임의로 만들지 않도록 프롬프트를 설계한다.

---

# 17. 블로그 API

```http
POST   /api/blog
GET    /api/blog
GET    /api/blog/{slug}
PATCH  /api/blog/{id}
DELETE /api/blog/{id}

POST /api/blog/generate
POST /api/blog/{id}/publish
POST /api/blog/{id}/unpublish
```

공개 게시글 조회 API와 로그인 사용자의 편집용 API를 구분한다.

---

# 18. 기술 스택 현황 페이지

DecisionFlow 프로젝트 자체의 개발 현황을 공개하는 기술 블로그/프로젝트 페이지도 만들 수 있도록 한다.

예:

```text
DecisionFlow 개발기

v0.1
FastAPI 기본 API
Docker 배포

v0.2
회원가입 / 로그인
사용자별 설정
Notion 연결

v0.3
Google OAuth
회원별 회의 기록
PostgreSQL

v0.4
기술 블로그 기능
```

기술 스택 표시 예:

```text
Backend
FastAPI
Python
SQLAlchemy
Pydantic

Database
PostgreSQL

Auth
JWT
Google OAuth 2.0

AI
OpenAI API

Integration
Notion API

Infra
Docker
Docker Hub
Railway
```

이 페이지는 포트폴리오로 활용할 수 있도록 공개 URL에서 접근 가능하게 한다.

---

# 19. 프론트엔드 디자인 개선

## 디자인 목표

첨부된 레퍼런스 이미지처럼
**모바일에서 매우 깔끔하고 간결한 서비스 UI**를 지향한다.

단, 특정 서비스의 UI를 그대로 복제하지 않는다.

참고할 요소:

- 명확한 아이콘 중심 네비게이션
- 흰색 또는 오프화이트 배경
- 큰 여백
- 카드 단위 정보 배치
- 짧고 명확한 제목
- 일관된 border-radius
- 가벼운 그림자
- 컬러는 포인트 용도로 제한
- 텍스트보다 아이콘을 활용할 수 있는 부분은 아이콘 사용
- 모바일 Bottom Navigation
- 데스크톱에서는 Sidebar 또는 Top Navigation
- 빈 화면을 과도한 장식으로 채우지 않음

---

# 20. 로그인 화면 디자인

로그인 화면은 단순하고 직관적으로 구성한다.

예:

```text
DecisionFlow

[ G Google로 계속하기 ]

──────── 또는 ────────

이메일
비밀번호

[로그인]

계정이 없나요? 회원가입
```

Google 버튼은 공식 브랜드 가이드라인을 해치지 않는 범위에서 구현한다.

로그인 화면에 과도한 설명이나 큰 Hero 문구를 넣지 않는다.

---

# 21. 최초 로그인 후 설정 UX

Google 신규 로그인 또는 이메일 회원가입 직후에는 다음처럼 설정 마법사를 제공한다.

```text
Step 1
계정 생성 완료

Step 2
OpenAI API Key
Notion API Key
Notion Database ID

[나중에 설정]
[저장하고 시작]
```

로그인과 외부 서비스 설정을 한 화면에 과도하게 몰아넣지 않는다.

---

# 22. 모바일 네비게이션

첨부 레퍼런스의 장점을 참고하여 하단 Navigation을 정리한다.

권장 예:

```text
홈
회의
+
블로그
더보기
```

가운데 `+`는 새 기록/회의 생성 버튼으로 사용한다.

---

# 23. 아이콘

텍스트 이모지 대신 일관된 SVG Icon Library를 사용한다.

예:
- Lucide
- Heroicons

중 현재 프론트 기술과 잘 맞는 하나만 선택한다.

아이콘 라이브러리를 여러 개 혼용하지 않는다.

주요 아이콘:

```text
Home
Folder
Mic
FileText
Sparkles
Settings
User
BookOpen
Plus
Search
ExternalLink
Calendar
CheckCircle
Clock
LogIn
LogOut
```

---

# 24. 홈 화면

홈 화면은 장식보다 현재 상태를 빠르게 보여준다.

예:

```text
안녕하세요, 혜영님

최근 회의
진행 중 Action Item
최근 프로젝트
최근 블로그 초안
```

상단에 과도한 Hero Text를 사용하지 않는다.

---

# 25. 최근 작업 카드

레퍼런스 이미지처럼 최근 작업을 카드로 노출한다.

각 카드:

```text
상태
제목
날짜
프로젝트
```

예:

```text
AI 분석 완료
FastAPI 배포 회의
2026.09.30
DecisionFlow
```

---

# 26. 블로그 화면

공개 블로그는 레퍼런스 이미지의 장점만 참고한다.

구조 예:

```text
DecisionFlow Blog

개발 기록과 기술 실험

[전체]
[개발일지]
[FastAPI]
[AI]
[Data]
```

아래에 블로그 카드 배치.

카드:

```text
Thumbnail
Category
Title
Summary
Date
```

---

# 27. 반응형

모바일 화면을 반드시 실제 폭에서 테스트한다.

기준:

```text
375px
390px
430px
768px
Desktop
```

가로 스크롤이 생기지 않아야 한다.

---

# 28. 기존 기능 보존

다음 기능은 업데이트 후에도 그대로 정상 작동해야 한다.

- FastAPI Swagger
- 프로젝트 CRUD
- 회의 CRUD
- AI 분석
- Action Item
- Decision
- Notion 연결
- Notion Sync
- Docker 실행
- Railway 배포

기존 기능 Regression Test를 수행한다.

---

# 29. FastAPI 구조

기존 구조를 우선 사용한다.

필요 시 아래 모듈을 추가한다.

```text
app/
├── api/
│   ├── auth.py
│   ├── settings.py
│   └── blog.py
│
├── models/
│   ├── user.py
│   ├── auth_account.py
│   ├── user_settings.py
│   └── blog_post.py
│
├── schemas/
│   ├── auth.py
│   ├── settings.py
│   └── blog.py
│
├── services/
│   ├── auth_service.py
│   ├── google_oauth_service.py
│   ├── encryption_service.py
│   └── blog_service.py
```

이미 동일 역할 모듈이 있다면 중복 생성 금지.

---

# 30. 보안 체크

반드시 확인한다.

- API Key 평문 저장 금지
- API Key 로그 출력 금지
- API Key API 응답 전체 노출 금지
- `.env` Git/Docker 이미지 포함 금지
- 비밀번호 평문 저장 금지
- 비밀번호 hashing 적용
- 로그인 사용자 ownership 검증
- Google OAuth state 검증
- OAuth callback validation
- CORS 설정 확인
- SECRET_KEY 배포환경 변수 사용
- GOOGLE_CLIENT_SECRET 코드 하드코딩 금지

---

# 31. 배포

기존 Docker/Railway 구조를 유지한다.

현재 배포 흐름:

```text
Code 수정
↓
docker compose build
↓
Docker 이미지 생성
↓
wndnsud/decisionflow:latest 태그
↓
Docker Hub Push
↓
Railway Redeploy
```

이번 작업 완료 후 동일 방식으로 재배포 가능해야 한다.

---

# 32. PostgreSQL 배포

회원 기록을 실제 서비스처럼 유지하려면 Railway PostgreSQL 연결을 준비한다.

Railway 환경에서는 SQLite를 장기 Source of Truth로 사용하지 않는다.

`DATABASE_URL` 환경변수만 변경하여 PostgreSQL로 전환 가능하도록 한다.

---

# 33. Migration

DB Schema 변경은 Alembic migration으로 관리한다.

예:

```text
users
auth_accounts
user_settings
blog_posts
```

추가.

기존 테이블을 삭제하고 다시 생성하는 방식은 금지한다.

---

# 34. 개발 진행 순서

한 번에 전체 구현하지 않는다.

## Phase 1 — 현재 코드 분석
- 현재 구조 파악
- 인증 구현 여부 확인
- 설정 저장 위치 확인
- localStorage 사용 여부 확인
- DB Schema 확인
- 기존 배포 방식 확인

분석 결과를 먼저 요약한다.

## Phase 2 — 회원/인증
- 회원가입
- 이메일 로그인
- 현재 사용자 조회
- 비밀번호 hashing
- 인증 Dependency

## Phase 3 — Google OAuth
- Google OAuth App 설정
- Login endpoint
- Callback endpoint
- 신규 사용자 자동 생성
- 기존 사용자 연결
- JWT 발급 또는 기존 인증체계 연동
- Frontend redirect

## Phase 4 — 사용자 설정
- UserSettings 모델
- API Key 암호화
- 설정 저장
- 로그인 후 자동 복원
- 설정 변경
- 연결 테스트

## Phase 5 — 기록 사용자 연결
- Project ownership
- Meeting ownership
- Decision ownership
- Action Item ownership
- 로그인 후 기록 복원

## Phase 6 — PostgreSQL
- Railway PostgreSQL 연결 구조
- Migration
- 기존 기능 테스트

## Phase 7 — UI 개선
- 로그인 화면
- Google 로그인 버튼
- 모바일 레이아웃
- 아이콘 통일
- 카드 구조 정리
- Bottom Navigation
- 설정/회원 화면 정리

기존 UI를 전체 삭제하지 말고 점진적으로 개선한다.

## Phase 8 — Blog
- BlogPost 모델
- Draft
- AI 초안 생성
- 편집
- 게시
- 공개 목록
- 공개 상세

## Phase 9 — 기술 스택 현황
- 공개 프로젝트 소개
- 기술 스택
- 개발 버전
- 개발 일지 연결

## Phase 10 — Regression Test

다음 전부 확인:

```text
이메일 회원가입
이메일 로그인
Google 로그인
Google 신규 사용자 생성
로그아웃
다시 로그인
설정 자동 복원
회의 생성
회의 조회
AI 분석
Notion 연결
Notion Sync
블로그 초안
블로그 게시
모바일 UI
Swagger
```

## Phase 11 — 재배포
- Docker build
- 로컬 실행
- Docker Hub push
- Railway redeploy
- Production smoke test

---

# 35. 완료 기준

이번 업데이트가 성공했다고 판단하는 기준:

1. 신규 사용자가 이메일 회원가입을 할 수 있다.
2. 사용자가 Google 계정으로 로그인할 수 있다.
3. Google 신규 사용자는 자동으로 DecisionFlow User로 생성된다.
4. 기존 이메일 로그인 기능이 유지된다.
5. 회원가입 또는 설정에서 OpenAI/Notion 정보를 저장할 수 있다.
6. API Key가 평문 DB로 저장되지 않는다.
7. 로그아웃 후 다시 로그인해도 설정이 자동으로 복원된다.
8. 회의록 및 프로젝트 기록이 계정별로 유지된다.
9. 다른 사용자 데이터에 접근할 수 없다.
10. 모바일 화면이 정돈되어 보인다.
11. 아이콘 스타일이 일관된다.
12. 기존 AI/Notion 기능이 유지된다.
13. 기록을 블로그 초안으로 만들 수 있다.
14. 블로그 글을 사용자 승인 후 게시할 수 있다.
15. 기술 스택/개발 현황을 공개 페이지에서 볼 수 있다.
16. Docker/Railway 재배포가 정상적으로 완료된다.

---

# 36. Codex 작업 방식

코드를 바로 대량 수정하지 않는다.

먼저 다음을 수행하고 사용자에게 보고한다.

```text
1. Repository 분석
2. 현재 구조 요약
3. 변경 대상 파일 목록
4. DB Migration 계획
5. Google OAuth 적용 계획
6. 구현 순서
7. 위험요소
```

그 후 Phase 2부터 순차적으로 구현한다.

각 Phase 완료 후:

```text
변경된 파일
구현 내용
테스트 결과
남은 문제
```

를 간단히 기록한다.

기존 정상 동작 코드를 무리하게 리팩터링하지 않는다.

---

# 37. 디자인 레퍼런스 해석

첨부 이미지는 UI를 그대로 복사하기 위한 자료가 아니다.

참고해야 할 핵심은:

```text
깔끔한 모바일 정보 위계
단순한 아이콘
큰 여백
카드 기반 정보 표시
짧은 메뉴 이름
명확한 CTA
하단 네비게이션
정돈된 블로그 카드
```

이다.

DecisionFlow 자체 브랜드와 색상 체계는 유지하되,
현재보다 가볍고 정돈된 화면으로 개선한다.

---

# 최종 방향

이번 버전에서 DecisionFlow는:

```text
개인 회의록 도구
↓
회원 기반 개인 Workspace
↓
이메일 / Google 로그인
↓
AI / Notion 설정 자동 복원
↓
개인 기록 영구 저장
↓
회의와 프로젝트 실행 관리
↓
기록을 기술 블로그 콘텐츠로 전환
↓
기술 스택과 개발 과정을 공개
```

하는 서비스로 발전한다.

중심은 끝까지 **FastAPI + PostgreSQL + Google OAuth + AI + Notion + Docker/Railway**이며,
프론트엔드는 이를 편하게 사용할 수 있도록 정돈하는 역할을 한다.
