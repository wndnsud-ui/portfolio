# DecisionFlow 4차 고도화 Codex 업무지시서
## 회의록 담당자 → 팀장 검토 → 업무 배분 → 팀원 수행 → 결재 → 최종 결과 게시

---

# 0. 프로젝트 방향

이번 작업은 기존 DecisionFlow를 새로 만드는 작업이 아니다.

현재까지 구축/계획된 다음 구조를 유지한다.

- FastAPI
- PostgreSQL
- 이메일 로그인
- Google OAuth
- 사용자별 OpenAI / Notion 설정
- Workspace / Project / Member
- Meeting
- AI 분석
- Decision
- Action Item
- Notion Sync
- Blog
- Docker
- Docker Hub
- Railway 배포

이번 고도화의 목적은 DecisionFlow를 단순 AI 회의록 서비스가 아니라
**실제 조직의 업무 배포·수행·결재까지 연결되는 협업 시스템**으로 발전시키는 것이다.

---

# 1. 제품 정의

DecisionFlow의 핵심 정의:

> 회의록 담당자가 회의를 구조화하고,
> 팀장이 결정과 업무를 확정·배포하며,
> 팀원이 업무를 수행하고 결재를 받아,
> 최종 결과까지 기록하는 AI 업무 실행 시스템.

단순 흐름:

```text
회의
↓
전사 / 텍스트 입력
↓
AI 분석
↓
회의록 담당자 1차 정리
↓
팀장 검토
↓
Workspace 게시
↓
업무 배분
↓
팀원 업무 수락
↓
업무 수행
↓
결재 요청
↓
팀장 승인
↓
최종 결과 게시
↓
다음 회의 Follow-up
```

---

# 2. 가장 중요한 개발 원칙

절대 금지:

- 기존 프로젝트 전체 재작성
- 기존 API 전면 삭제
- 기존 DB 초기화
- 기존 Docker / Railway 배포 구조 파괴
- 기존 사용자 데이터 삭제
- 기존 Notion 기능 삭제
- 기존 Google 로그인 구조 무시
- 기존 AI 분석 로직 전체 교체
- 한 번에 모든 기능 대량 구현

작업 원칙:

1. Repository 구조를 먼저 분석한다.
2. 기존 기능 재사용 여부를 확인한다.
3. DB 변경은 Alembic migration으로 처리한다.
4. 권한은 Frontend가 아니라 Backend에서 검증한다.
5. 기능별 Phase 단위로 구현한다.
6. 각 Phase 완료 후 테스트 결과를 보고한다.
7. 기존 기능 Regression Test를 반드시 수행한다.
8. 최종적으로 Docker Hub → Railway 재배포 가능 상태를 유지한다.

---

# 3. 로그인 구조

로그인 시스템 자체는 하나로 유지한다.

지원 방식:

```text
Google OAuth
Email / Password
```

로그인 후 사용자 Role에 따라 다른 Dashboard와 권한을 제공한다.

예:

```text
Login
↓
Role 확인
↓
OWNER / MANAGER / MEMBER
↓
각 Role Dashboard
```

팀장 전용 계정 시스템과 팀원 전용 계정 시스템을 별도로 복제하지 않는다.

같은 User 시스템을 사용하고 Role로 화면과 권한을 분기한다.

---

# 4. 역할 구조

기본 Role:

```text
OWNER
MANAGER
MEMBER
```

회의 단위 역할:

```text
RECORDER
```

RECORDER는 고정 직급이 아니라 Meeting 단위 지정 가능하도록 설계한다.

---

# 5. OWNER 권한

- Workspace 생성
- Workspace 설정 변경
- 팀원 초대 / 제거
- MANAGER 지정
- 모든 Project 접근
- 모든 Meeting 접근
- 모든 업무 조회
- Workspace 삭제
- 결재 / 승인 가능

---

# 6. MANAGER 권한

MANAGER는 팀장 역할이다.

권한:

- Project 생성
- Project Member 지정
- Meeting 생성
- Recorder 지정
- 회의록 검토
- 화자 이름 수정
- Decision 승인 / 수정 / 반려
- Action Item 수정
- 담당자 지정
- 기한 지정
- Workspace 게시
- 팀원 업무 배정
- 결재 승인
- 수정 요청
- 반려
- 최종 결과 게시

---

# 7. MEMBER 권한

- 자신이 참여한 Project 조회
- Meeting 조회
- 자신에게 배정된 업무 조회
- 업무 수락
- 업무 진행 상태 변경
- 업무 진행 내용 작성
- 업무 댓글 작성
- 파일 첨부
- 결재 요청
- 수정 요청 확인
- 재제출

---

# 8. RECORDER 역할

Meeting 생성 시 Recorder를 지정 가능하게 한다.

예:

```text
Meeting Owner
김팀장

Recorder
최혜영

Participants
민지
현수
```

Recorder 권한:

- 음성 / 전사 파일 등록
- 텍스트 입력
- AI 분석 실행
- Speaker Label 정리
- 회의록 초안 수정
- Decision Candidate 정리
- Action Item Candidate 정리
- 팀장에게 검토 요청

Recorder는 Decision을 최종 확정하거나 업무를 최종 배정하지 않는다.

---

# 9. 회의 입력 방식

Meeting 생성 시 다음 입력을 모두 지원한다.

```text
1. 직접 녹음
2. 음성 파일 업로드
3. 전사 텍스트 파일 업로드
4. 텍스트 직접 붙여넣기
```

초기 파일 지원:

```text
Audio:
mp3
m4a
wav
mp4

Text:
txt
md
```

후속 지원:

```text
docx
pdf
```

---

# 10. 입력 방식별 처리

## 음성 입력

```text
Audio Upload
↓
Transcription
↓
Transcript Save
↓
AI Analysis
```

## 전사 텍스트 파일

```text
TXT / MD Upload
↓
Text Parsing
↓
Text Normalization
↓
AI Analysis
```

이미 텍스트가 존재하는 경우 STT를 다시 실행하지 않는다.

## 직접 붙여넣기

```text
Text Paste
↓
Normalization
↓
AI Analysis
```

---

# 11. 전사 상태

```text
UPLOADED
TRANSCRIBING
TRANSCRIBED
ANALYZING
REVIEW_READY
FAILED
```

전사 진행률 표시 가능 구조를 유지한다.

Chunk 기반 전사가 구현되어 있다면 완료된 Chunk부터 저장/노출한다.

---

# 12. AI 분석 결과

AI는 최소 다음 구조를 반환한다.

```text
Summary
Discussion
Speaker Segments
Decision Candidates
Action Item Candidates
Undecided Topics
Follow-up Topics
```

AI 결과는 자동 확정하지 않는다.

사람이 반드시 검토한다.

---

# 13. 회의록 상태 머신

Meeting 또는 MeetingReport 상태:

```text
DRAFT
TRANSCRIBING
AI_ANALYZED
RECORDER_REVIEW
MANAGER_REVIEW
CHANGES_REQUESTED
APPROVED
PUBLISHED
```

흐름:

```text
DRAFT
↓
AI_ANALYZED
↓
RECORDER_REVIEW
↓
MANAGER_REVIEW
↓
APPROVED
↓
PUBLISHED
```

수정 요청 시:

```text
MANAGER_REVIEW
↓
CHANGES_REQUESTED
↓
RECORDER_REVIEW
```

---

# 14. 회의록 담당자 1차 검토

Recorder 화면에서 다음을 수정 가능하게 한다.

```text
회의 제목
회의 날짜
참석자
화자 이름
Summary
Discussion
Decision Candidate
Action Item Candidate
Undecided Topic
```

버튼:

```text
[초안 저장]
[팀장 검토 요청]
```

---

# 15. 화자 이름 매핑

전사 결과 예:

```text
Speaker 1
Speaker 2
Speaker 3
```

MANAGER 또는 Recorder가:

```text
Speaker 1 → 김팀장
Speaker 2 → 최혜영
Speaker 3 → 민지
```

로 일괄 매핑 가능하게 한다.

매핑 후 전체 Transcript에 반영한다.

권장 모델:

```text
MeetingSpeaker

id
meeting_id
speaker_label
display_name
user_id nullable
created_at
updated_at
```

---

# 16. 팀장 회의록 검토 화면

MANAGER는 다음을 검토한다.

```text
화자 이름
Summary
Discussion
Decision
Action Item
담당자
기한
미결사항
```

버튼:

```text
[승인]
[수정 요청]
[반려]
```

승인 후 Workspace 게시 가능.

---

# 17. Workspace 게시

회의록 승인 후:

```text
[팀 Workspace에 게시]
```

게시 시:

- Meeting 공개
- Confirmed Decision 공개
- Assigned Action Item 공개
- Participants에게 알림 생성

---

# 18. Decision Workflow

AI 생성:

```text
Decision Candidate
```

상태:

```text
CANDIDATE
CONFIRMED
REJECTED
CHANGED
```

MANAGER만 최종 Confirm 가능.

Decision History 유지.

예:

```text
09/29 Google OAuth 검토
09/30 Google OAuth 적용 결정
10/01 Email Login 병행 결정
```

---

# 19. Action Item 생성

회의에서 확정된 Action Item은 Task로 생성한다.

필수 필드:

```text
id
project_id
meeting_id
title
description
assignee_id
assigned_by
due_date
status
priority
created_at
updated_at
```

---

# 20. 업무 상태 머신

Action Item 상태:

```text
ASSIGNED
ACCEPTED
IN_PROGRESS
BLOCKED
READY_FOR_REVIEW
CHANGES_REQUESTED
APPROVED
CANCELLED
```

기본 흐름:

```text
ASSIGNED
↓
ACCEPTED
↓
IN_PROGRESS
↓
READY_FOR_REVIEW
↓
APPROVED
```

수정 요청:

```text
READY_FOR_REVIEW
↓
CHANGES_REQUESTED
↓
IN_PROGRESS
↓
READY_FOR_REVIEW
```

업무 차단:

```text
IN_PROGRESS
↓
BLOCKED
```

---

# 21. 업무 수락

팀원에게 업무가 배정되면:

```text
새 업무가 배정되었습니다.

Google OAuth 설정

담당자
최혜영

기한
10/07

[수락]
[담당 변경 요청]
```

수락:

```text
ASSIGNED → ACCEPTED
```

---

# 22. 업무 상세 화면

업무 상세는 작은 협업 공간으로 구성한다.

예:

```text
#DF-024
Google OAuth 구현

Project
DecisionFlow

담당자
최혜영

Status
IN_PROGRESS

Due
10/07
```

하단:

```text
설명
진행 기록
댓글
첨부파일
Activity
```

---

# 23. 업무 진행 기록

팀원은 업무 수행 중 진행 내용을 작성할 수 있다.

예:

```text
10/04 14:20
Google Cloud OAuth Client 생성 완료

10/05 09:30
Callback URI 설정 중
```

권장 모델:

```text
TaskProgress

id
task_id
user_id
content
created_at
updated_at
```

---

# 24. 업무 댓글 기능

Task마다 댓글 작성 가능.

예:

```text
김팀장
배포 환경 Redirect URI도 확인해주세요.

최혜영
네, Railway 주소까지 추가하겠습니다.
```

권장 모델:

```text
TaskComment

id
task_id
user_id
content
created_at
updated_at
deleted_at nullable
```

기능:

- 댓글 작성
- 댓글 수정
- 댓글 삭제
- 작성자 표시
- 작성 시간 표시

---

# 25. @Mention

댓글에서:

```text
@혜영 Railway 배포 결과 확인해주세요.
```

지원.

Mention 대상 사용자에게 앱 내부 알림 생성.

권장 모델:

```text
CommentMention

id
comment_id
mentioned_user_id
created_at
```

---

# 26. 업무 파일 첨부

Task에 파일 첨부 가능하게 한다.

초기:

```text
pdf
docx
xlsx
png
jpg
txt
md
```

권장 모델:

```text
TaskAttachment

id
task_id
uploaded_by
file_name
file_url
file_type
created_at
```

파일 저장 방식은 현재 인프라 구조를 먼저 분석한 후 결정한다.

---

# 27. 결재 요청

팀원은 업무가 끝났다고 바로 APPROVED 처리하지 않는다.

버튼:

```text
[결재 요청]
```

동작:

```text
IN_PROGRESS
↓
READY_FOR_REVIEW
```

결재 요청 시 팀장에게 알림.

---

# 28. 팀장 결재

MANAGER 화면:

```text
결재 요청

Google OAuth 구현
담당: 최혜영

진행 기록
첨부파일
댓글
결과 내용
```

버튼:

```text
[승인]
[수정 요청]
[반려]
```

승인:

```text
READY_FOR_REVIEW → APPROVED
```

수정 요청:

```text
READY_FOR_REVIEW → CHANGES_REQUESTED
```

---

# 29. 최종 결과 게시

APPROVED 된 Task는 Project의 Final Results 영역에 게시한다.

예:

```text
Google OAuth 구현
완료

담당
최혜영

승인
김팀장

완료일
2026.10.07
```

Project에서 완료 결과를 누적 조회 가능하게 한다.

---

# 30. 다음 회의 Follow-up

새 Meeting 생성 시:

```text
이전 회의 미완료 Action Item
최근 승인된 결과
Blocked Task
Changes Requested Task
```

를 자동 조회한다.

예:

```text
지난 회의 후속 업무

Google OAuth
APPROVED

모바일 UI
IN_PROGRESS

Blog 화면
CHANGES_REQUESTED
```

---

# 31. 역할별 Dashboard

## MANAGER Dashboard

상단 KPI:

```text
검토 대기 회의록
결재 대기 업무
미수락 업무
진행 중 업무
지연 업무
미확정 Decision
```

영역:

```text
회의록 검토 대기
업무 결재 요청
팀원별 업무 현황
최근 Decision
프로젝트 진행 현황
```

## MEMBER Dashboard

상단 KPI:

```text
새 업무
오늘 마감
진행 중
수정 요청
결재 대기
```

영역:

```text
내 업무
내 프로젝트
최근 회의
내 댓글/멘션
```

## RECORDER Dashboard

상단 KPI:

```text
정리 대기 회의
전사 중
AI 분석 완료
팀장 검토 요청 전
수정 요청
게시 완료
```

---

# 32. 앱 내부 알림

Notification 유형:

```text
workspace_invite
project_assigned
meeting_review_requested
meeting_changes_requested
meeting_published
task_assigned
task_accepted
task_comment
task_mention
task_review_requested
task_changes_requested
task_approved
task_due_soon
```

권장 모델:

```text
Notification

id
user_id
type
title
message
target_type
target_id
is_read
created_at
```

---

# 33. Workspace / Project 권한

권한은 Backend에서 반드시 검증한다.

FastAPI Dependency 예:

```text
get_current_user
require_workspace_member
require_workspace_manager
require_project_member
require_project_manager
require_meeting_recorder
```

Frontend에서 버튼을 숨기는 것만으로 권한을 처리하지 않는다.

---

# 34. 데이터 구조 확장

기존 모델과 충돌 여부를 먼저 분석한다.

추가 검토 모델:

```text
MeetingSpeaker
MeetingReview
TaskProgress
TaskComment
CommentMention
TaskAttachment
TaskReview
Notification
FinalResult
```

---

# 35. API 설계

## Meeting Review

```http
POST /api/meetings/{meeting_id}/submit-review
POST /api/meetings/{meeting_id}/approve
POST /api/meetings/{meeting_id}/request-changes
POST /api/meetings/{meeting_id}/publish
```

## Speaker Mapping

```http
GET   /api/meetings/{meeting_id}/speakers
PATCH /api/meetings/{meeting_id}/speakers
```

## Task Assignment

```http
POST /api/tasks/{task_id}/accept
POST /api/tasks/{task_id}/request-reassignment
POST /api/tasks/{task_id}/start
POST /api/tasks/{task_id}/block
```

## Task Progress

```http
GET  /api/tasks/{task_id}/progress
POST /api/tasks/{task_id}/progress
```

## Task Comment

```http
GET    /api/tasks/{task_id}/comments
POST   /api/tasks/{task_id}/comments
PATCH  /api/task-comments/{comment_id}
DELETE /api/task-comments/{comment_id}
```

## Task Review

```http
POST /api/tasks/{task_id}/submit-review
POST /api/tasks/{task_id}/approve
POST /api/tasks/{task_id}/request-changes
POST /api/tasks/{task_id}/reject
```

## Notification

```http
GET   /api/notifications
PATCH /api/notifications/{notification_id}/read
POST  /api/notifications/read-all
```

---

# 36. Meeting 입력 API

기존 Meeting API를 유지하고 입력 유형을 확장한다.

예:

```text
input_type

audio
text_file
text_paste
recording
```

필드:

```text
source_file_url
raw_text
transcript_text
```

기존 구조와 중복 여부를 먼저 확인한다.

---

# 37. UI 필수 신규 화면

반드시 추가 검토:

```text
1. 로그인 화면
2. MANAGER Dashboard
3. MEMBER Dashboard
4. RECORDER Dashboard
5. 회의 자료 등록
6. 전사 진행
7. 화자 이름 매핑
8. 회의록 1차 검토
9. 팀장 회의록 검토
10. Workspace 게시
11. 업무 상세
12. 업무 댓글
13. 업무 진행 기록
14. 결재 요청
15. 팀장 결재
16. 최종 결과
17. 알림
```

---

# 38. 로그인 / 로그아웃 UX

Header 또는 Profile Menu:

```text
프로필
설정
Workspace 전환
로그아웃
```

로그아웃 시:

- 인증 토큰 제거
- 사용자 캐시 초기화
- 로그인 화면 이동

단, DB 데이터는 삭제하지 않는다.

재로그인 시 사용자 데이터 자동 복원.

---

# 39. 모바일 Navigation

권장:

```text
홈
프로젝트
+
업무
더보기
```

MANAGER의 `더보기`:

```text
회의록 검토
결재함
팀원
Decision
알림
설정
로그아웃
```

MEMBER의 `더보기`:

```text
참여 회의
댓글/멘션
알림
설정
로그아웃
```

---

# 40. Notion 역할

원칙 유지:

```text
DecisionFlow = Source of Truth
Notion = 선택적 Publish / Sync Destination
```

게시 승인된 Meeting이나 Final Result만 Notion으로 Sync할 수 있도록 한다.

초안 상태 자동 Sync 금지.

---

# 41. Blog 연계

승인된 Project 결과 기반으로:

```text
Meeting
Decision
Action Item
Final Result
Activity
```

를 활용해 AI가 프로젝트 회고 초안 생성.

자동 게시 금지.

---

# 42. PostgreSQL

Production에서는 SQLite를 Source of Truth로 사용하지 않는다.

회원별 / 팀별 / 결재 데이터 영속성 보장을 위해 PostgreSQL을 사용한다.

---

# 43. Migration

Alembic 사용.

기존 테이블 삭제 금지.

Migration 시:

- 기존 Meeting 유지
- 기존 ActionItem 유지
- 기존 Decision 유지
- 기존 User 유지

확장 컬럼 또는 신규 테이블 중심으로 처리한다.

---

# 44. Activity Log

다음 이벤트 기록:

```text
meeting_created
transcription_completed
recorder_review_submitted
meeting_changes_requested
meeting_approved
meeting_published
task_assigned
task_accepted
task_started
task_progress_added
task_commented
task_review_requested
task_changes_requested
task_approved
final_result_published
```

---

# 45. 보안

반드시 확인:

- Role 기반 접근 제어
- 다른 Workspace 데이터 접근 방지
- 다른 Project 데이터 접근 방지
- 다른 User Task 수정 방지
- API Key 암호화
- Google OAuth state 검증
- Password hashing
- Secret 로그 출력 금지
- Attachment 접근 권한
- Comment 삭제 권한

---

# 46. 개발 우선순위

## Phase 1 — 현재 코드 분석

먼저 보고:

```text
현재 User / Role 구조
현재 Workspace 구조
현재 Project 구조
현재 Meeting 구조
현재 Transcription 구조
현재 Decision 구조
현재 ActionItem 구조
현재 Auth 구조
현재 PostgreSQL 상태
현재 Notion 상태
현재 UI 구조
```

추가로:

```text
기존 기능과 이번 요구사항의 충돌 지점
재사용 가능한 코드
신규 모델 필요 여부
```

## Phase 2 — Role / Login UX
- OWNER / MANAGER / MEMBER Role 점검
- Recorder 지정 구조
- Role별 Dashboard 분기
- Login / Logout UX

## Phase 3 — Meeting Input 확장
- Audio
- Recording
- TXT
- MD
- Text Paste

## Phase 4 — Recorder Workflow
- AI 분석
- Speaker Mapping
- Recorder Review
- Manager Review 요청

## Phase 5 — Manager Meeting Approval
- 승인
- 수정 요청
- 게시
- Decision Confirm

## Phase 6 — Task Assignment
- 담당자
- 기한
- Assignment
- Acceptance

## Phase 7 — Task Collaboration
- 진행 기록
- 댓글
- Mention
- Attachment

## Phase 8 — Approval Workflow
- 결재 요청
- Manager Review
- 승인
- 수정 요청
- 재제출
- Final Result

## Phase 9 — Notification
- 업무 배정
- 댓글
- Mention
- 회의록 검토
- 결재

## Phase 10 — Follow-up
- 다음 회의 이전 업무
- 미완료 업무
- 승인 결과
- Blocked 업무

## Phase 11 — UI 정리
- Manager Dashboard
- Member Dashboard
- Recorder Dashboard
- Review Screens
- Task Detail
- Approval

## Phase 12 — Regression Test
반드시 확인:

```text
Email Login
Google Login
Logout
User Settings
OpenAI
Transcription
Text Upload
Meeting
Decision
Task
Comments
Approval
Notion
Blog
Swagger
Docker
Railway
```

## Phase 13 — 배포

```text
docker compose build
↓
local smoke test
↓
docker tag
↓
docker push
↓
Railway redeploy
↓
Production smoke test
```

---

# 47. MVP 범위 제한

이번 버전에서 구현하지 않는다.

- 실시간 공동 문서 편집
- 화상 회의
- Slack 전체 연동
- Discord 전체 연동
- 복잡한 HR 평가
- 팀원 점수화
- Git Branch / PR 복제
- 무제한 자동 Email
- 복잡한 BPMN Workflow Designer

---

# 48. 완료 기준

다음이 실제로 가능해야 한다.

1. 이메일 / Google 로그인
2. 로그아웃
3. Role별 Dashboard 분리
4. Meeting Recorder 지정
5. 음성 파일 업로드
6. TXT / MD 전사 파일 업로드
7. Text Paste
8. AI 분석
9. 화자 이름 매핑
10. Recorder 1차 검토
11. 팀장 검토 요청
12. 팀장 수정 요청
13. 팀장 승인
14. Workspace 게시
15. Decision Confirm
16. Action Item 담당자 배정
17. 팀원 업무 수락
18. 업무 진행 기록
19. 업무 댓글
20. @Mention 알림
21. 파일 첨부
22. 결재 요청
23. 팀장 승인 / 수정 요청
24. 승인된 최종 결과 게시
25. 다음 회의 Follow-up
26. PostgreSQL 영속화
27. 기존 Notion 정상
28. 기존 Blog 정상
29. Docker 정상
30. Railway 정상

---

# 49. Codex 작업 방식

바로 전체 구현하지 않는다.

먼저 다음을 사용자에게 보고한다.

```text
1. 현재 Repository 구조
2. 기존 모델
3. 신규 모델 제안
4. ERD 변경안
5. Role / Permission Matrix
6. Meeting 상태 머신
7. Task 상태 머신
8. API 변경안
9. Migration 계획
10. UI 변경 대상
11. 구현 순서
12. 위험 요소
```

사용자 확인 후 Phase별로 구현한다.

각 Phase 완료 시:

```text
변경 파일
구현 내용
Migration
API
테스트 결과
남은 문제
```

를 요약한다.

---

# 최종 서비스 흐름

```text
Login
↓
Workspace
↓
Meeting
↓
Audio / Text Input
↓
AI Analysis
↓
Recorder Review
↓
Manager Review
↓
Publish
↓
Decision Confirm
↓
Task Assignment
↓
Member Accept
↓
Work Progress
↓
Comment / Mention / Attachment
↓
Approval Request
↓
Manager Approval
↓
Final Result
↓
Next Meeting Follow-up
```

DecisionFlow의 핵심은
**회의록 작성 자체가 아니라 회의에서 나온 결정과 업무가 실제 조직의 실행과 결재까지 이어지도록 만드는 것**이다.
