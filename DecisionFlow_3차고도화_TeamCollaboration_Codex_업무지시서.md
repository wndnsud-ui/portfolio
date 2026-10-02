# DecisionFlow 3차 고도화 업무지시서
## GitHub-style Team Collaboration + Decision Execution Workflow

---

# 0. 프로젝트 방향

이번 작업은 기존 DecisionFlow를 새로 만드는 것이 아니다.

현재까지 구현된 FastAPI, 회원/로그인, 사용자별 설정, 회의록 저장, AI 회의 분석, Decision, Action Item, Notion Sync, Blog, Docker, Docker Hub, Railway 배포 구조를 유지하면서 **팀 협업형 프로젝트 실행 관리 기능을 추가**한다.

---

# 1. 제품 차별화 정의

기존 AI 회의록 서비스가 주로 다음에 집중한다.

```text
회의
↓
녹취
↓
요약
↓
회의록
```

DecisionFlow는 다음 단계까지 연결한다.

```text
회의
↓
AI 분석
↓
Decision 추출
↓
Action Item 추출
↓
담당자 배정
↓
팀원이 업무 수락
↓
업무 진행
↓
완료
↓
다음 회의에서 결과 확인
```

핵심 문장:

> 다글로가 회의를 기록한다면, DecisionFlow는 회의에서 나온 결정과 업무를 팀에 배포하고 완료까지 추적한다.

---

# 2. GitHub 방식에서 가져올 개념

GitHub 구조:

```text
Organization
↓
Repository
↓
Member
↓
Issue / PR / Commit
```

DecisionFlow 구조:

```text
Workspace
↓
Project
↓
Member
↓
Meeting
↓
Decision
↓
Action Item
```

GitHub UI나 기능을 복제하지 않는다.

참고하는 것은 아래 개념뿐이다.

- 팀 단위 Workspace
- 프로젝트 단위 권한
- 구성원 초대
- 담당자 지정
- 업무 상태 추적
- 변경 이력
- 활동 로그

---

# 3. Workspace 개념

사용자는 개인 계정으로 로그인한 후 하나 이상의 Workspace에 참여할 수 있다.

예:

```text
혜영님의 Workspace

AI 프로젝트팀
사주 팟캐스트팀
개인 프로젝트
```

Workspace는 팀 단위의 최상위 협업 공간이다.

---

# 4. Workspace Role

최소 3개 역할을 제공한다.

```text
OWNER
ADMIN
MEMBER
```

## OWNER

- Workspace 생성
- Workspace 설정 변경
- 팀원 초대
- 팀원 제거
- ADMIN 지정
- Project 생성
- 모든 Project 접근
- Workspace 삭제

## ADMIN

- Project 생성
- Project Member 관리
- Meeting 생성
- Decision 승인
- Action Item 배정
- 프로젝트 설정 수정

## MEMBER

- 자신이 참여한 Project 조회
- Meeting 조회
- 자신에게 배정된 Action Item 조회
- 업무 상태 변경
- 댓글 또는 진행 내용 작성
- 허용된 범위의 Meeting 작성

---

# 5. Project 단위 권한

Workspace에 들어왔다고 해서 모든 Project를 볼 수 있게 하지 않는다.

예:

```text
Workspace
AI 프로젝트팀

Project A
DecisionFlow
→ 혜영, 민지

Project B
Calorie Detect
→ 혜영, 현수

Project C
Portfolio
→ 현수
```

각 Project에 참여 Member를 별도로 지정한다.

---

# 6. 핵심 사용자 시나리오

## 시나리오 1 — 팀장 Workspace 생성

```text
Google 로그인
↓
Workspace 생성
↓
"AI 프로젝트팀"
```

## 시나리오 2 — 팀원 초대

OWNER 또는 ADMIN이 이메일로 팀원을 초대한다.

```text
hye***@gmail.com
```

초대받은 사용자가 로그인하면:

```text
AI 프로젝트팀에 초대되었습니다.

[참여]
[거절]
```

## 시나리오 3 — Project 생성

```text
Project Name
DecisionFlow

Description
AI 기반 회의 실행 관리 서비스
```

## 시나리오 4 — Project Member 지정

```text
혜영
민지
현수
```

## 시나리오 5 — Meeting 생성

입력:

```text
회의 제목
회의 날짜
참석자
회의 원문
```

## 시나리오 6 — AI 분석

AI는 최소 다음을 추출한다.

```text
Summary
Discussion
Decision Candidates
Action Items
Undecided Topics
```

## 시나리오 7 — Decision 승인

```text
AI Decision Candidate

"Google 로그인 기능 추가"

[승인]
[수정]
[논의사항으로 변경]
[삭제]
```

승인 시:

```text
CONFIRMED DECISION
```

## 시나리오 8 — Action Item 배정

```text
Task #24

Google OAuth 설정

Project
DecisionFlow

Assignee
혜영

Due Date
10/03

Status
TODO
```

---

# 7. Action Item 상태

```text
TODO
ACCEPTED
IN_PROGRESS
BLOCKED
DONE
CANCELLED
```

기본 흐름:

```text
TODO
↓
ACCEPTED
↓
IN_PROGRESS
↓
DONE
```

문제 발생 시:

```text
IN_PROGRESS
↓
BLOCKED
```

---

# 8. 업무 수락 개념

팀장이 업무를 배정했다고 해서 바로 진행 중으로 처리하지 않는다.

팀원 화면:

```text
새 업무가 배정되었습니다.

Google OAuth 설정

[수락]
[담당 변경 요청]
```

수락 시:

```text
TODO → ACCEPTED
```

---

# 9. My Tasks

각 팀원에게 개인 업무 화면을 제공한다.

```text
My Tasks

오늘 마감 1
진행 중 3
대기 2
지연 1
```

업무 카드:

```text
Google OAuth 설정
DecisionFlow
Due 10/03
IN_PROGRESS
```

---

# 10. 역할별 Dashboard

## OWNER / ADMIN Dashboard

```text
Projects
Meetings This Week
Open Tasks
Overdue Tasks
Pending Decisions
Blocked Tasks
```

추가:
- 최근 Project
- 최근 Meeting
- 팀원별 업무 상태

## MEMBER Dashboard

```text
My Projects
My Tasks
Today Due
Overdue
Recent Meetings
```

관리 기능보다 실행 기능을 우선 노출한다.

---

# 11. Meeting → Task 자동 생성

회의 분석 결과:

```text
Action Item

Task:
회원가입 UI 수정

Assignee:
혜영

Due:
10/05
```

사용자 승인 시:

```text
ActionItem 생성
↓
Project 연결
↓
Member 연결
↓
My Tasks 표시
```

---

# 12. 다음 회의 자동 Follow-up

새 Meeting 생성 시 이전 Meeting의 미완료 Action Item을 자동 표시한다.

예:

```text
지난 회의 미완료 업무

Google OAuth 설정
담당: 혜영
Status: IN_PROGRESS

모바일 UI 수정
담당: 민지
Status: BLOCKED
```

---

# 13. Decision History

Decision은 단순 텍스트로 저장하지 않는다.

예:

```text
Backend Framework

09/20 Flask 검토
09/28 FastAPI 확정
10/02 FastAPI 유지
```

기존 Decision이 변경될 경우 History 생성.

---

# 14. Activity Log

팀 프로젝트의 주요 변경을 기록한다.

예:

```text
09:20 혜영이 Task #24를 완료했습니다.
09:15 민지가 Decision #7을 승인했습니다.
08:50 현수가 Meeting을 생성했습니다.
```

Activity Type:

```text
meeting_created
decision_approved
task_assigned
task_accepted
task_started
task_blocked
task_completed
member_invited
member_joined
```

---

# 15. Workspace Invite

초대 방식:

```text
Email Invite
Invite Link
```

예:

```text
https://decisionflow.../invite/abc123
```

초대 링크 사용 흐름:

```text
Invite Link
↓
Google 로그인
↓
Workspace 확인
↓
[참여]
```

---

# 16. Google OAuth 연결

기존 Google OAuth 계획을 유지한다.

```http
GET /api/auth/google/login
GET /api/auth/google/callback
```

Google 신규 사용자 로그인 시:

```text
Google 인증
↓
User 생성
↓
Invite 조회
↓
Workspace 가입
```

---

# 17. 데이터 구조

권장 관계:

```text
User
 │
 ├── AuthAccount
 ├── UserSettings
 └── WorkspaceMembership
          │
          ▼
      Workspace
          │
          ├── WorkspaceMembers
          │
          └── Projects
                 │
                 ├── ProjectMembers
                 ├── Meetings
                 │     ├── Decisions
                 │     └── ActionItems
                 │
                 └── ActivityLogs
```

---

# 18. 신규 모델

최소 검토:

```text
Workspace
WorkspaceMember
WorkspaceInvite
ProjectMember
ActivityLog
```

---

# 19. Workspace 모델 예시

```text
Workspace

id
name
owner_id
description
created_at
updated_at
```

---

# 20. WorkspaceMember 모델

```text
WorkspaceMember

id
workspace_id
user_id
role
joined_at
```

Role:

```text
owner
admin
member
```

---

# 21. ProjectMember 모델

```text
ProjectMember

id
project_id
user_id
role
joined_at
```

---

# 22. WorkspaceInvite 모델

```text
WorkspaceInvite

id
workspace_id
email
token
role
status
expires_at
created_at
```

Status:

```text
pending
accepted
expired
cancelled
```

---

# 23. ActionItem 확장

기존 ActionItem에 다음 필드를 검토한다.

```text
assignee_id
assigned_by
accepted_at
started_at
blocked_at
completed_at
blocked_reason
```

---

# 24. Decision 승인 정보

Decision 확장:

```text
status
approved_by
approved_at
source_meeting_id
```

Status:

```text
candidate
confirmed
rejected
changed
```

---

# 25. FastAPI API 구조

## Workspace

```http
POST /api/workspaces
GET  /api/workspaces
GET  /api/workspaces/{workspace_id}
PATCH /api/workspaces/{workspace_id}
```

## Workspace Member

```http
GET    /api/workspaces/{workspace_id}/members
POST   /api/workspaces/{workspace_id}/invite
PATCH  /api/workspaces/{workspace_id}/members/{user_id}
DELETE /api/workspaces/{workspace_id}/members/{user_id}
```

## Invite

```http
GET  /api/invites/{token}
POST /api/invites/{token}/accept
POST /api/invites/{token}/reject
```

## Project

```http
POST /api/workspaces/{workspace_id}/projects
GET  /api/workspaces/{workspace_id}/projects
```

## Project Member

```http
GET    /api/projects/{project_id}/members
POST   /api/projects/{project_id}/members
DELETE /api/projects/{project_id}/members/{user_id}
```

## Decision

```http
POST /api/decisions/{decision_id}/approve
POST /api/decisions/{decision_id}/reject
```

## Task

```http
GET   /api/tasks/my
PATCH /api/tasks/{task_id}
POST  /api/tasks/{task_id}/accept
POST  /api/tasks/{task_id}/start
POST  /api/tasks/{task_id}/block
POST  /api/tasks/{task_id}/complete
```

---

# 26. 권한 Dependency

FastAPI Dependency를 적극 활용한다.

예:

```text
get_current_user
require_workspace_member
require_workspace_admin
require_project_member
require_project_admin
```

Router 안에서 권한 로직을 반복 작성하지 않는다.

---

# 27. 권한 규칙

반드시 서버에서 검증한다.

Frontend에서 버튼을 숨기는 것만으로 권한을 구현하지 않는다.

예:

```text
MEMBER가 DELETE Workspace 요청
↓
403
```

---

# 28. UI 구조

Desktop:

```text
Workspace Sidebar

Dashboard
Projects
Meetings
My Tasks
Decisions
Blog
Members
Settings
```

Mobile Bottom Navigation:

```text
홈
프로젝트
+
업무
더보기
```

---

# 29. Project Detail

```text
DecisionFlow

Overview
Meetings
Decisions
Tasks
Members
Activity
```

---

# 30. Team Member 화면

```text
혜영
MEMBER

Active Tasks 3
Done 7
Blocked 1
```

개인 성과 평가나 점수화 기능은 MVP에서 구현하지 않는다.

---

# 31. 알림

초기 MVP에서는 앱 내부 알림만 구현한다.

예:

```text
새 프로젝트 초대
새 업무 배정
Decision 승인 요청
Due Date 임박
```

Email / Push / Slack 알림은 후속 기능.

---

# 32. Notion 역할

Notion은 계속 선택적 외부 출력처다.

```text
DecisionFlow = Source of Truth
Notion = Publish / Sync Destination
```

Workspace 또는 Project 단위로 Notion DB를 연결할 수 있도록 향후 확장 가능하게 설계한다.

---

# 33. Blog 연결

Project 완료 후:

```text
Project
+
Meeting
+
Decision History
+
Action Item
+
Activity Log
```

를 기반으로 AI가 프로젝트 개발 회고 초안을 생성할 수 있도록 한다.

최종 공개는 사용자 승인 후 수행한다.

---

# 34. ML 연계

기존 ML 계획은 유지하되 이번 Team Collaboration MVP에서는 우선순위를 낮춘다.

향후:

```text
Action Item Delay Prediction
```

에 Workspace / Member / Project 데이터를 Feature로 활용할 수 있다.

---

# 35. PostgreSQL

Team Collaboration 기능을 구현하기 전에 PostgreSQL 구조를 안정화한다.

SQLite를 Production Source of Truth로 사용하지 않는다.

---

# 36. Migration

Alembic 사용.

추가 예상:

```text
workspaces
workspace_members
workspace_invites
project_members
activity_logs
```

기존 테이블 삭제 금지.

---

# 37. 보안

반드시 확인:

- 다른 Workspace 접근 방지
- 다른 Project 접근 방지
- Invite Token 유효기간
- Invite Token 재사용 방지
- Role 기반 권한
- API Key 암호화
- Google OAuth state 검증
- 비밀번호 hashing
- Secret 로그 출력 금지

---

# 38. 개발 순서

## Phase 1 — Repository 분석

먼저 현재 구조를 분석하고 보고한다.

```text
현재 인증
현재 User 모델
현재 Project 모델
현재 Meeting 모델
현재 ActionItem 모델
현재 DB
현재 Google OAuth 구현 상태
현재 Notion 구조
```

## Phase 2 — Workspace 모델

```text
Workspace
WorkspaceMember
```

구현.

## Phase 3 — Project Membership

```text
ProjectMember
```

추가.

기존 Project CRUD를 파괴하지 않는다.

## Phase 4 — Invite

```text
WorkspaceInvite
Email Invite
Invite Link
Accept
Reject
```

## Phase 5 — Role Permission

FastAPI Dependency 기반 권한 구현.

## Phase 6 — Action Item Assignment

기존 ActionItem을 팀 업무 시스템으로 확장.

## Phase 7 — Decision Approval

AI Decision Candidate → Admin Approval.

## Phase 8 — Dashboard

OWNER/ADMIN과 MEMBER Dashboard 분리.

## Phase 9 — Activity Log

프로젝트 주요 Event 기록.

## Phase 10 — Follow-up

새 회의 생성 시 이전 미완료 업무 표시.

## Phase 11 — UI 개선

GitHub 구조를 참고하되 UI 복제 금지.

DecisionFlow 자체 디자인 유지.

## Phase 12 — Regression Test

반드시 기존 기능 확인.

```text
Google Login
Email Login
Settings
OpenAI
Notion
Meeting
Decision
Action Item
Blog
Docker
Swagger
```

## Phase 13 — Docker / Railway 재배포

기존 방식 유지.

```text
docker compose build
↓
docker tag
↓
docker push
↓
Railway Redeploy
```

---

# 39. MVP 범위 제한

이번 Team Collaboration 버전에서 구현하지 않는다.

- Git branch 개념
- Pull Request
- Code Review
- Git commit 연동
- 복잡한 성과 평가
- 팀원 점수화
- Slack
- Discord
- Email 자동 리포트
- 실시간 공동 편집
- 화상 회의
- 음성 스트리밍

---

# 40. 완료 기준

다음이 모두 가능해야 한다.

1. 사용자가 Workspace 생성
2. 팀원 초대
3. Google 로그인 후 초대 수락
4. Project 생성
5. Project Member 지정
6. Meeting 생성
7. AI 분석
8. Decision Candidate 생성
9. ADMIN이 Decision 승인
10. Action Item 생성
11. 팀원에게 업무 배정
12. 팀원이 업무 수락
13. 업무 상태 변경
14. 팀장 Dashboard에서 전체 상태 확인
15. 팀원 Dashboard에서 My Tasks 확인
16. 다음 Meeting에서 미완료 업무 확인
17. 모든 데이터 PostgreSQL 저장
18. 기존 Notion 기능 정상
19. 기존 Blog 기능 정상
20. Docker/Railway 재배포 정상

---

# 41. Codex 작업 원칙

바로 전체 구현하지 않는다.

먼저 사용자에게 다음을 보고한다.

```text
1. 현재 코드 구조
2. 기존 모델과 충돌 가능성
3. 신규 모델 제안
4. ERD 변경안
5. API 변경안
6. Migration 계획
7. 작업 순서
8. 예상 위험 요소
```

사용자 확인 후 Phase 단위로 작업한다.

각 Phase 완료 후:

```text
변경 파일
구현 내용
테스트 결과
남은 문제
```

를 기록한다.

---

# 42. 최종 제품 정의

DecisionFlow는 최종적으로:

> **회의에서 나온 결정과 업무를 팀 프로젝트에 연결하고, 담당자에게 배정하며, 실행과 완료까지 추적하는 AI 협업 Workspace**

로 정의한다.

제품 흐름:

```text
Workspace
↓
Project
↓
Meeting
↓
AI Analysis
↓
Decision Approval
↓
Action Item Assignment
↓
Member Execution
↓
Progress Tracking
↓
Next Meeting Follow-up
↓
Project History
↓
Blog / Notion Publish
```

기술 중심:

```text
FastAPI
PostgreSQL
Google OAuth
OpenAI API
Notion API
Docker
Railway
```

UI는 단정하고 모바일 친화적으로 유지한다.

GitHub의 협업 개념은 참고하지만,
DecisionFlow만의 핵심은 **회의 → 결정 → 실행**의 연결이다.
