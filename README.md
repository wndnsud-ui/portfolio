# HY ARCHIVE

최혜영의 포트폴리오·기록 사이트. 프로젝트 케이스 스터디, Notes(직무·공부), Life, 독서 노트, 소개를 한 곳에서 보여 주고, 모든 콘텐츠를 사이트 안의 글쓰기 스튜디오에서 직접 쓰고 디자인한다.

> Problem → Structure → Result

## 구성

| 영역 | 기술 |
| --- | --- |
| 서버 | Python, Flask, Jinja2 |
| DB | Supabase(PostgreSQL) · 로컬은 SQLite. SQLAlchemy ORM, Flask-Migrate(Alembic) |
| 이미지 | Supabase Storage `media` 버킷 · 로컬은 `static/uploads/` |
| 보안 | 관리자 1명(환경변수), Flask-WTF CSRF, 로그인 5회 실패 시 10분 잠금 |
| 화면 | Vanilla CSS(`tokens.css` 변수) · Vanilla JS |
| 배포 | Railway (`gunicorn app:app`, 배포 전 `flask db upgrade`) |

## 화면

| 메뉴 | URL | 내용 |
| --- | --- | --- |
| 홈 | `/` | 첫 화면(사진·배지·대표 문장·WORK SYSTEM), 요약 카드 4, 프로젝트 3, 직접 운영하는 것들, 경력, 기술, 최근 기록 + 읽고 있는 책 |
| 프로젝트 | `/projects`, `/projects/<slug>` | 가로 카드 목록, 케이스 스터디(문제 · 구조 · 막힌 지점과 해결 · 결과 · 배운 점). 장문 포트폴리오는 `/portfolio` |
| 기록 | `/notes?type=study|reading|life`, `/notes/<slug>` | 공부·업무 / 독서 / 일상 탭, 검색·정렬·12개씩 페이지. 상세는 목차·함께 읽으면 좋은 기록·댓글 |
| 독서 | `/reading`, `/reading/books/<id>` | 책장(읽는 중 · 다 읽음 · 읽고 싶은)과 책별 독서 노트 |
| 소개·이력서 | `/about` | 회사에 보내는 한 페이지. 인쇄·PDF 저장용 스타일 포함 |
| 운영 중인 곳 | `/rest`, `/sofa` | 모모슬의 휴식도감(민트), 모두의 소파(라일락). 유튜브 썸네일을 누를 때만 플레이어를 불러온다 |
| 기타 | `/search`, `/sitemap.xml`, `/rss.xml` | 사이트 전체 검색, 검색엔진·구독용 |

예전 주소 `/archive`, `/blog`, `/records`, `/life`, `/reading/<글>`, `/momoseul`은 새 주소로 301 연결된다.

관리자: `/admin`(콘텐츠), `/admin/write?kind=project|notes|reading|about`(글쓰기), `/admin/showcases`(운영 중인 곳 · 영상), `/admin/comments`, `/admin/import`.

## 파일

```text
app.py                  공개 화면 라우트, 명령어(flask seed, flask hash-password)
books_api.py            카카오 책 검색·표지 가져오기
admin.py                관리자: 로그인, 콘텐츠 관리, 스튜디오 저장·자동 저장·업로드, 댓글, 가져오기
auth.py                 관리자 1명 로그인·잠금·@admin_required
content.py              블록·디자인 설정 검증, 분류 → 파스텔 색(CATEGORY_TINT), 목차·읽는 시간 계산
storage.py              이미지 저장 (Supabase Storage / 로컬)
models.py               SQLAlchemy 모델
migrations/             Alembic 마이그레이션 (0001 기존 구조, 0002 블록·디자인·공개 상태, 0003 pages, 0004 운영 중인 곳·영상·v3 칸)
migrate_to_supabase.py  SQLite → Supabase 일회성 이관
import_reading_data.py  노션 독서 기록 JSON·CSV 가져오기 (/admin/import에서도 사용)
notion_sync.py          노션 독서 DB → 책장·독서 노트 한 방향 동기화 (/admin/import 「지금 가져오기」, flask notion-sync)
seed.py                 빈 DB용 기본 데이터
templates/_components.html  아이콘·칩·카드·영상 카드·빈 상태·블록·연락 박스 등 공통 화면 조각
static/css/tokens.css   v3 색·파스텔·글꼴·간격·모서리 변수 (색은 여기서만 정한다)
static/css/site.css     공개 화면 / admin.css 관리자·스튜디오 / portfolio.css /portfolio 전용
static/js/home-interaction.js  홈 WORK SYSTEM 패널
static/js/studio.js     글쓰기 스튜디오 (블록 편집·디자인 즉시 반영·자동 저장)
```

## 로컬 실행

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdir -p ~/Desktop/프로젝트/포트폴리오 && chmod 700 ~/Desktop/프로젝트/포트폴리오
cp .env.example ~/Desktop/프로젝트/포트폴리오/env.txt && chmod 600 ~/Desktop/프로젝트/포트폴리오/env.txt
```

`~/Desktop/프로젝트/포트폴리오/env.txt`를 채운다. 프로젝트 폴더가 iCloud에 있어서 비밀값은 iCloud 밖에 둔다.
읽는 순서: `ENV_FILE` 환경변수로 지정한 파일 → `~/Desktop/프로젝트/포트폴리오/env.txt` → 프로젝트 폴더의 `.env`.

```bash
python -c "import secrets; print(secrets.token_hex(32))"   # → SECRET_KEY
flask hash-password                                          # 비밀번호 입력 → ADMIN_PASSWORD_HASH
```

`ADMIN_USERNAME`은 원하는 아이디. `DATABASE_URL`을 비워 두면 `instance/portfolio.db`(SQLite)를 쓴다.

```bash
flask db upgrade     # 테이블 만들기/갱신
flask seed           # 빈 DB일 때만 기본 데이터 (데이터가 있으면 아무것도 안 함)
flask run
```

> 0002 이전부터 쓰던 SQLite 파일이 있으면 처음 한 번만 `flask db stamp 0001_baseline` 후 `flask db upgrade`.

## 스키마 바꾸기

SQL을 직접 쓰지 않는다. `models.py`를 고친 뒤:

```bash
flask db migrate -m "무엇을 바꿨는지"   # migrations/versions/에 파일 생성 — 열어서 확인
flask db upgrade
```

## Supabase 전환

1. Supabase 프로젝트 생성(리전 서울 ap-northeast-2). Connect → **Session pooler(5432)** 주소를 `.env`(`~/Desktop/프로젝트/포트폴리오/env.txt`)의 `DATABASE_URL`에.
2. Storage에서 퍼블릭 버킷 `media` 생성. Project Settings → API의 URL과 `service_role` 키를 `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`에 (서버 환경변수에만 둔다).
3. `flask db upgrade` — 빈 테이블 생성, 모든 테이블에 RLS가 켜진다(정책 없음 → 공개 API 차단, Flask 직접 접속은 영향 없음).
4. 배포 중인 사이트의 SQLite 파일을 받아 이관(원본은 건드리지 않는다):

```bash
python migrate_to_supabase.py --source 받은파일.db                     # 미리보기: 테이블별 건수
python migrate_to_supabase.py --source 받은파일.db --apply --images    # 복사 + 이미지 Storage 이전
```

id를 그대로 복사하고 시퀀스를 맞춘 뒤 원본·대상 건수를 비교해 출력한다. 대상 테이블이 비어 있지 않으면 멈춘다.

## 배포 (Railway)

- 저장소 연결 → `main` 푸시 시 자동 배포. `railway.json`이 배포 전 `flask db upgrade`, 실행 `gunicorn app:app`을 지정한다.
- 환경변수: `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `KAKAO_REST_API_KEY`, `SESSION_COOKIE_SECURE=1`.
- `DATABASE_URL`이 있는데 `SECRET_KEY`가 없으면 앱이 시작하지 않는다(세션 위조 방지).
- 도메인 연결 후 HTTPS 확인.

## 백업

`.github/workflows/backup.yml` — 매주 월요일 03:00(KST) `pg_dump` → gpg 암호화 → Actions 아티팩트(90일).
저장소 Secrets에 `DATABASE_URL`, `BACKUP_PASSPHRASE`를 넣는다. Actions 탭에서 수동 실행도 된다.

복원 리허설(빈 DB에):

```bash
gpg -d hy-archive-YYYYMMDD.sql.gz.gpg | gunzip | psql "빈_DB_주소"
```

## 글쓰기 스튜디오

- 가운데: 공개될 모습 그대로 쓰는 흰 종이 / 오른쪽: 무엇을 쓸까요(프로젝트·기록·독서·소개), 커버, 포인트 색, 본문 폭·글자 크기, 발행.
- 블록: 문단, 소제목(목차 자동), 이미지, 이미지 2단, 인용, 강조, 구분, 마크다운, 유튜브, 인스타그램. 블록을 누르면 위로·아래로·삭제. 이미지는 끌어다 놓기.
- 디자인: 커버(없음·큰 커버), 포인트 색(버터·민트·하늘·핑크), 본문 폭(좁게 700·넓게 860), 글자 크기(16·17·19). 글꼴은 사이트 톤을 위해 고정. 목록 밖의 값은 서버가 기본값으로 바꾼다.
- 기록: 분류를 「일상」 쪽(맛집·여행·사주 연구·독서 모임·일상)으로 고르면 일상 탭에, 나머지는 공부·업무 탭에 들어간다.
- 독서: 「카카오에서 책 검색」으로 고르면 제목·저자·출판사가 채워지고 표지는 Storage(`covers/`)로 복사된다. `KAKAO_REST_API_KEY` 필요. 키는 서버에서만 쓴다.
- 소개: 이름·직무 한 줄·한 줄 소개(`==단어==`는 형광펜)·잘하는 것 4·경력/교육·기술. 오른쪽에서 연락처·사진·이력서 PDF·홈 대표 문장·요약 카드 4장.
- 발행: 분류·태그·홈에 고정·공개 예약(한국 시간). 임시저장 글은 방문자에게 보이지 않는다.
- 자동 저장: 입력을 멈추고 3초 뒤 임시저장. 공개 중인 글은 브라우저에만 보관하고 「고친 내용 공개」로 반영한다.

## 운영 중인 곳 · 영상

- `/admin/showcases`에서 휴식도감·모두의 소파의 소개 문장, 상태(운영 중/준비 중), 주소, 안내 카드 3장, 도감 카드·진행자를 고친다. 상태를 바꾸면 홈 카드·푸터·이력서에 바로 반영된다.
- 유튜브 주소(`watch?v=`, `youtu.be/`, `shorts/`)를 붙여 넣으면 영상 ID를 뽑아 썸네일 카드를 만든다. 제목·날짜·길이는 직접 적는다. 순서 변경·숨김·삭제 가능.

## 노션 동기화

1. notion.so/profile/integrations에서 내부 통합을 만들고 시크릿을 복사한다.
2. 독서 DB 오른쪽 위 ··· › 연결에서 그 통합을 추가한다.
3. `NOTION_TOKEN`, `NOTION_READING_DB`(DB 주소)를 env.txt와 Railway 변수에 넣는다.
4. `flask notion-sync --check`로 속성 연결을 확인하고, /admin/import 「지금 가져오기」나 `flask notion-sync`로 가져온다.

- DB 페이지 1개 = 책 1권. 제목·저자·출판사·장르·상태·시작일·완독일(또는 기간)·별점·한줄평·표지 속성을 이름으로 찾는다.
- 페이지 본문은 독서 노트로 옮긴다. 새 노트는 임시저장으로 들어오므로 확인 후 발행한다.
- 노션에서 고친 시간이 같으면 건너뛴다. 노션 파일(표지·본문 이미지)은 Storage `notion/`에 다시 올린다.

## ChatGPT 웹에서 독서 초안 저장

관리자 `/admin/chatgpt`에서 연결 키를 발급하고, ChatGPT 웹의 비공개 전용 GPT Actions에 연결한다.
기존 관리자 비밀번호·노션 키·Supabase 키를 GPT에 넣지 않는다. 서버는 OpenAI API를 호출하지 않으며,
정리는 ChatGPT 대화에서 수행하고 홈페이지에는 비공개 독서 초안만 저장한다.

1. 관리자 → **ChatGPT 연결** → 연결 키 발급. 원문 키는 발급 응답에서 한 번만 보이며 DB에는 SHA-256 해시만 저장한다.
2. 전용 GPT의 지침에 같은 화면의 지침을 붙인다 (`integrations/chatgpt-instructions.md`).
3. Actions 스키마를 `https://배포주소/api/chatgpt/openapi.json`에서 가져온다.
4. 인증을 API Key / Bearer로 설정하고 발급한 홈페이지 연결 키를 입력한다. GPT 공유 범위는 본인만으로 둔다.
5. `책 제목 기록을 찾아서 정리하고 홈페이지에 초안으로 저장해 줘`라고 요청한다.

- 관리자 **노션 가져오기**에서 책을 먼저 가져온다. `NOTION_TOKEN`이 있으면 해당 책의 실제 노션 본문/하위 페이지를 읽는다.
  없으면 이미 가져온 원문만 사용하고 `source_mode=imported_copy`를 반환한다.
- 초안 API는 전용 Bearer 키만 허용한다. 관리자 세션 쿠키로 호출할 수 없으며, CSRF 예외는 `/api/chatgpt` 블루프린트에만 적용한다.
  키 발급·폐기 관리자 폼의 CSRF 보호는 유지한다.
- 원문·사진 목록을 서명한 `source_token`은 1시간 유효하다. 원문에서 선택한 사진만 복사하며 임의 URL 다운로드는 받지 않는다.
- 사진 자동 복사는 알려진 노션 파일 호스트·Unsplash와 기존 사이트 이미지에 한정한다. 외부 사진은 직접 업로드한다.
  서버는 선택된 이미지만 Supabase Storage로 복사한다. 리디렉션 다운로드는 허용하지 않으며 이미지당 최대 6MB이다.
- 같은 책/원문에 대한 재전송은 기존 초안을 확인한다. 기존 글 수정에는 최신 revision이 필요하고, 이미 공개했거나 예약한 글은 수정하지 않는다.
- 공개·삭제 API는 없다. 최종 공개는 홈페이지 관리자에서 한다. 원본 노션과 기존 노션 가져오기 글은 변경하지 않는다.
- GPT 생성·Actions 사용 가능 여부는 사용 중인 계정에서 확인해야 한다. 일반 ChatGPT 대화나 이 Codex 대화에 자동 연결되지는 않는다.
- 연결 해시는 기존 `Profile.extra`의 `chatgpt_connection` 키에 저장한다. 소개 페이지를 수정해도 해당 키를 보존한다.
  새로운 테이블이나 DB 마이그레이션은 필요 없다.
- 회귀 검사: `python -m unittest discover -s tests -v` (격리 SQLite와 모의 Notion/Storage 사용, 실제 비밀값 미사용).

공식 설정 안내: https://developers.openai.com/api/docs/actions/getting-started
