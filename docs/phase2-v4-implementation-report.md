# DecisionFlow 4차 고도화 구현·검증 보고서

작성일: 2026-10-04. Phase 1 설계 확인 후 구현했다.

## 구현 결과

| 단계 | 반영 내용 |
|---|---|
| 2 역할·로그인 | Workspace OWNER/MANAGER/MEMBER, 프로젝트 멤버십, 이메일에 묶인 만료 초대, 로그아웃 캐시·선택 상태 초기화 |
| 3 회의 입력 | 붙여넣기, TXT/MD, 오디오·녹음, 전사 작업 진행률과 청크·부분 결과 저장 |
| 4 담당자 검토 | recorder_id, 원문을 유지하는 화자 매핑, 요약·토론·미결·후보 수정, 검토 요청 |
| 5 팀장 검토 | 승인·수정 요청·반려·게시, 상태 전이 검증과 검토 이력, 승인 전 확정 차단 |
| 6 업무 배분 | 실제 프로젝트 사용자 지정, 기한·설명, 배정 알림, 수락·시작·재배정 요청 |
| 7 협업 | 진행 기록, 댓글 수정·soft delete, 멘션 알림, 인증된 첨부 다운로드 |
| 8 결재 | 결과 제출·승인·수정 요청·반려, 중복 승인 방지, 최종 결과 스냅샷과 승인자 |
| 9 알림 | 사용자별 읽음 처리, 배정·검토·결재·댓글·멘션, 마감 알림 중복 방지 |
| 10 후속 회의 | 프로젝트 미완료 업무와 최근 최종 결과 조회 |
| 11 화면 | 역할별 대시보드, 회의 검토함·업무 결재함·결과·팀·알림, 모바일 화면, 지연 로딩 |
| 12 회귀 검증 | 권한·상태·데이터 보존 API 테스트, PostgreSQL 검증, 실제 Edge 브라우저 검증 |

개인 OpenAI/Notion 설정을 요청 단위로 적용한다. 다른 사용자의 키나 전역 키로 대신 호출하지 않는다. Notion은 게시된 회의만 동기화한다. Blog AI 생성은 게시 승인 회의와 승인된 최종 결과를 근거로 초안을 만든다.

## 마이그레이션과 운영

- 0001은 초기 스키마를 고정한다. 0002는 Workspace/멤버십을 추가하고 소유자가 있는 기존 프로젝트를 소유자의 Workspace에 연결한다.
- 0003은 회의 검토·업무 결재·협업·알림·전사 작업 테이블을 추가한다. 기존 완료 업무를 자동 승인하거나 이름으로 담당자를 연결하지 않는다.
- 앱 시작 시 Alembic head를 적용한다. 운영 APP_ENV=production은 PostgreSQL과 별도 SECRET_KEY를 요구한다.
- `scripts/import_legacy_sqlite.py`는 읽기 전용 SQLite 백업을 **빈 PostgreSQL**로만 복사한다. 알 수 없는 테이블·컬럼과 필수 컬럼 누락은 중단하며, 테이블별 행 수를 확인한다.
- 운영 서비스의 기존 SQLite를 먼저 백업했다. 영구 볼륨 연결 시 컨테이너가 재시작되어 임시 SQLite가 초기화됐고, 연결 전에 확보한 원본으로 복원했다. 프로젝트 1건·회의 1건·전사 1건을 PostgreSQL `decisionflow_preserved`에 보존했다. 기존 DB에는 사용자 소유권 정보가 없으므로 이 자료를 새 계정에 임의로 귀속시키지 않았다.
- 원본 백업: 로컬 `.tools/decisionflow-before-v4.db`, 운영 영구 볼륨 `/data/backups/decisionflow-before-v4-20261004.db`. 백업에는 회의 내용이 있으므로 공개 저장소에 올리지 않는다.
- 첨부파일은 `/data/attachments`, PostgreSQL은 별도 영구 볼륨을 사용한다.
- 검증된 게시 이미지: `wndnsud/decisionflow:v4-20261004`, digest `sha256:0a90de5620bad89373bbd18e609bf6dd214fb1144f16afc5aae53d74e7445a03`. 운영 이미지 교체 후 상태는 아래 기록을 따른다.

### Phase 13 배포 확인

Railway `celebrated-communication` 프로젝트의 `production / decisionflow` 서비스를 위 고정 태그로 교체했다. 배포 ID는 `e7028a84-8860-4297-9543-fb3a73b536fb`, 최종 상태는 SUCCESS이며 실제 실행 digest도 일치한다. `latest` 태그는 덮어쓰지 않았다.

`scripts/verify_deployment.py https://decisionflow-production.up.railway.app --browser` 통과: health·홈·OpenAPI 200, Workspace/업무/알림/회의 승인/대시보드 경로 존재, 미로그인 API 접근 401. 실제 Edge에서 로그인 화면이 표시되고 모바일 가로 넘침·JavaScript 오류가 없었다. 운영 계정을 임의로 생성하거나 테스트 업무를 운영 DB에 넣지 않았다.

운영 PostgreSQL 조회에서도 프로젝트·회의·전사 각 1건 및 `0003_approval_workflow`를 확인했다. 실사용자의 운영 로그인 이후 업무 수행은 로컬 브라우저 검증과 구분한다.

## 검증 증거

- `python -m unittest discover -s tests -v`: 15개 통과. 접근 차단, 역할, 승인 우회, 중복 승인, 재검토, 초대, 댓글·파일, 키 분리, 전사 청크, 화자 원문 보존, Notion/Blog 근거 검사, 마감 알림을 확인했다.
- SQLite 신규·기존 DB 업그레이드와 기존 사용자·프로젝트 보존을 확인했다.
- 격리된 PostgreSQL 17에서 신규/기존 마이그레이션 및 업무 수락→수행→제출→승인→최종 결과를 확인했다.
- 실제 운영 백업을 격리된 로컬 PostgreSQL에 옮긴 뒤 행 수와 head 업그레이드를 확인하고 운영 이전을 실행했다.
- Docker 빌드에서 TypeScript 검사와 Vite 빌드 통과. 초기 JS 487.15KB, 업무 화면 별도 청크 25.84KB.
- `scripts/browser_smoke.py http://127.0.0.1:61665`: MEMBER 수락·시작·결과 제출, OWNER 승인·결과 조회, 로그아웃 토큰 삭제, 390px 모바일 넘침 없음, JavaScript 오류 없음.

## 남아 있는 범위

- 유료 OpenAI 전사·분석, 실제 Notion 쓰기, Google 브라우저 로그인은 실계정으로 검증하지 않았다. 외부 호출 테스트는 mock으로 검증했다.
- 전사 작업은 FastAPI BackgroundTasks다. 청크와 상태는 저장되지만 프로세스 재시작 시 자동 재개하는 외부 작업 큐는 없다.
- 음성 원본 파일 영구 보관과 전사 재시도 UI는 없다. 회의 참석자는 기존 문자열이며 별도 MeetingParticipant 모델은 이번 구현에 포함하지 않았다.
- Notion 최종 결과 단독 동기화는 아직 없다. 게시된 회의 동기화 경로를 구현했다.
- 운영의 기존 소유자 없는 자료는 보존했지만 로그인 사용자의 목록에 노출되지 않는다. 사용자가 소유 계정으로 `wndnsud@gmail.com`을 지정했고, 회원가입·연결은 **나중에 진행**하기로 했다. 해당 계정 가입 후 운영 환경에서 `python scripts/claim_legacy_projects.py wndnsud@gmail.com 1`을 실행하면 복원된 프로젝트 1번과 연결된 회의·업무·결정의 소유권을 연결한다. 기존 소유자가 있으면 실행을 중단하며 계정을 임의 생성하지 않는다. 도구는 저장소에 있으므로 다음 운영 작업에서 업로드해 사용한다.
- 자동 downgrade로 데이터를 삭제하지 않는다. 되돌리려면 검증된 DB 백업과 이전 이미지로 복원해야 한다.
