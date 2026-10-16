# 모두의 소파 — 팟캐스트 MVP

음성 파일을 올리면 화자별 Transcript를 만들고, 문장을 클릭하면 실제 오디오의 해당 시점으로 이동하는 AI 팟캐스트 제작 서비스.
업무지시서 v4와 Claude Design 캔버스 "모두의 소파 MVP 화면"(7개 화면)을 기준으로 구현했다.

```
frontend/  React + TypeScript + Vite, React Router, Axios, Zustand, Wavesurfer.js, Supabase JS
backend/   FastAPI, SQLAlchemy 2 + Alembic, Supabase Auth/Storage, FFmpeg, OpenAI
```

## 빠른 시작 (키 없이 로컬에서 전체 흐름 확인)

키가 하나도 없어도 **개발 모드**로 업로드 → 전처리 → STT → AI → 에디터까지 돌려볼 수 있다.

| 항목 | 키가 없을 때 | 키를 넣으면 |
|---|---|---|
| 로그인 | 개발용 계정 (`DEV_AUTH_ENABLED=true`) | 카카오 로그인 (Supabase Auth) |
| DB | `backend/data/dev.db` (SQLite) | `DATABASE_URL` (Supabase Postgres) |
| Storage | `backend/data/storage` + 서명 URL | Supabase Storage (private 버킷) |
| STT / LLM | 모의 결과 (`[모의 STT]`, `[모의 AI]`) | `gpt-4o-transcribe-diarize` / `OPENAI_LLM_MODEL` |

```bash
# 루트에 .env (예시는 .env.example). 로컬 개발이면 아래 두 줄이면 충분
#   DEV_AUTH_ENABLED=true
#   VITE_API_BASE_URL=http://localhost:8000

# Backend
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # macOS/Linux: .venv/bin/pip
.venv/Scripts/alembic upgrade head
.venv/Scripts/uvicorn app.main:app --port 8000

# Frontend (다른 터미널)
cd frontend
npm install
npm run dev        # http://localhost:5173
```

FFmpeg가 PATH에 없으면 `imageio-ffmpeg`에 포함된 바이너리를 쓴다(ffprobe는 `ffmpeg -i` 파싱으로 대체). Docker 이미지에는 정식 FFmpeg가 들어 있다.

Docker: `docker compose up --build` → Frontend `:5173`, Backend `:8000`.

## 실제 연동 설정 (착수 전 체크리스트)

1. **Supabase**
   - Storage에 **private** 버킷 생성 (`STORAGE_BUCKET`, 기본 `episodes`), 플랜의 파일 크기 제한 확인 (90분 WAV는 900MB가 넘을 수 있다)
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`(Backend 전용), `DATABASE_URL`
   - JWT: 레거시 HS256 프로젝트면 `SUPABASE_JWT_SECRET`, 비대칭 키 프로젝트면 비워 두면 JWKS로 검증
   - Frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
2. **카카오** (3장)
   - Kakao Developers 앱 등록 → 카카오 로그인 활성화 → Redirect URI `https://<project-ref>.supabase.co/auth/v1/callback`
   - Supabase → Authentication → Providers → Kakao에 REST API 키 / Client Secret 입력 (**코드·.env에 넣지 않는다**)
   - 이메일 동의항목은 심사가 필요할 수 있으므로 Kakao Provider의 **"Allow users without an email"** 을 켠다
   - Supabase → Authentication → URL Configuration에 Frontend 주소(`http://localhost:5173` 등)를 Redirect URL로 추가
3. **OpenAI**: `OPENAI_API_KEY`, `OPENAI_LLM_MODEL`. STT 모델 제한(25MB, 청크 길이)은 착수 시점 공식 문서로 재확인하고, 다르면 `STT_CHUNK_SEC`만 조정
4. **운영**: `DEV_AUTH_ENABLED=false`, `CORS_ORIGINS`를 Frontend 도메인으로

## 구조와 핵심 결정

- **업로드**: 브라우저 1차 검증(형식·용량·가능하면 길이) → `upload-url`로 Signed Upload URL 발급 → Storage에 직접 PUT (진행률 표시를 위해 XHR 사용) → `upload-complete`에서 ffprobe로 형식·길이·실제 디코딩 확인
- **전처리**: 재생용 MP3 CBR 128kbps/44.1kHz, peaks JSON(초당 25포인트), STT용 모노 16kHz 64kbps 20분 청크(15초 겹침). 청크는 **재생용 파일에서 잘라** 재생 시각과 STT 시각의 기준을 맞춘다
- **STT**: 청크별 동시 2개, 최대 3회 지수 백오프 재시도, 원본 응답은 `stt_raw/`에 보관 → offset 보정 → 겹침 중간 시각 기준으로 중복 제거 → 겹침 구간에서 가장 많이 겹치는 화자끼리 통합 (`transcription_service.merge_chunks`)
- **재생**: `<audio>` 하나. Wavesurfer는 `media` 옵션으로 같은 요소에 연결하고 서버 peaks만 그린다. 현재 문장은 "현재 시각 이전에 시작한 마지막 Segment"를 이진 탐색(`findActiveSegment`)으로 찾고, 사용자가 스크롤 중이면 4초간 자동 스크롤을 멈춘다
- **AI**: 입력은 `[seg=N][mm:ss.s][화자] 문장` 형식, Structured Outputs(JSON Schema strict). **LLM에게는 Segment의 `seq` 번호를 Segment ID로 보여주고**, Backend가 존재 여부를 검증한 뒤 시간을 Segment에서 확정한다. 하이라이트 인용문은 Backend가 실제 Segment 텍스트를 이어 붙여 만든다. 유효 항목이 모자라면 1회 재요청 후 실패. 120,000자를 넘으면 구간별 처리 후 합친다
- **상태**: `status`(오디오/STT)와 `ai_status` 분리. 작업 시작은 조건부 UPDATE로 선점, 서버 시작 시 멈춘 작업을 `failed`로 정리
- **접근 제어**: 모든 조회에 `user_id` 조건, 남의 리소스는 404

### 업무지시서에서 추가하거나 구체화한 것

- `speaker_merges` 테이블: 병합 되돌리기용(옮긴 Segment ID 목록 + 삭제된 화자 정보). 5장 스키마에는 없던 테이블
- `episodes.original_filename`: 업로드 화면·카드에 파일 이름을 보여주기 위해 추가
- 화자 응답에 `suspect`(의심 화자): 첫 청크 이후에 처음 등장했거나 비중 5% 미만인 화자를 노란 테두리로 강조
- `GET /api/episodes/{id}` 응답에 `stt_chunk_sec`, `stt_overlap_sec`: 진행 화면의 "구간 2 / 3 · 19:45 ~ 39:45" 표시용
- 개발 모드(로컬 Storage, SQLite, 모의 STT/LLM, 개발용 로그인)

## 테스트

```bash
cd backend && .venv/Scripts/python -m pytest -q     # 14개: 화자 통합·겹침 제거, AI 검증, 실제 WAV로 전체 API 흐름
cd frontend && npm test                              # 현재 문장 이진 탐색
cd frontend && npm run build                         # 타입 체크 + 빌드
```

Backend의 `test_api_flow.py`는 FFmpeg로 실제 오디오를 만들어 업로드 → 전처리 → STT(모의) → AI(모의) → 수정/삭제/복원 → 화자 이름·병합·되돌리기 → 제목 선택 → 재분석 → 삭제까지 확인하고, 접근 제어 404, Range 요청 206, 서버 재시작 정리, 중복 실행 방지도 확인한다.

### 16장 검증 중 실제 키·파일이 있어야 하는 항목 (아직 미확인)

- 1 카카오 로그인 (Supabase/Kakao 키 필요)
- 6·8 실제 STT 품질, 청크 경계 누락·중복, **Seek 오차 0.5초 이내** (실제 40분 이상 팟캐스트 파일 + OpenAI 키 필요, 13장 1순위 완료 후 검증 항목)
- 13~15 실제 LLM 결과 품질

## 2차 기능: 자르기 · 내보내기 · 보정 · AI 시작음

업무지시서 15장에서 MVP 제외였던 기능 중 일부를 범위에 넣었다.

- **편집 (비파괴)**: 에디터 상단 **편집** → 파형 드래그 또는 문장 클릭(Shift+클릭으로 범위)으로 **구간 선택** → **이 구간 삭제 / 여기만 살리기 / 되살리기 / 선택 듣기**. 시작·끝 시각 직접 입력과 ±0.1초 조정, **문장에 맞추기**, 파형 확대(최대 약 100배), 되돌리기/다시하기(Ctrl+Z / Ctrl+Shift+Z), Delete 키로 선택 삭제. 잘린 구간은 가장자리를 끌어 조정. `audio_cuts`에 잘린 구간만 저장하고 원본·재생 파일·Segment 시간은 바꾸지 않는다 → 대본 동기화(8장) 유지. 미리 듣기는 잘린 구간을 건너뛰고, 대본에는 "잘림/일부 잘림"으로 표시
- **내보내기**: 원본 파일에 자르기 → (AI 잡음 제거) → (음량·잡음 보정) → 시작음 크로스페이드 → 라우드니스 -16 LUFS → MP3 192kbps. `{prefix}/exports/{id}.mp3`에 저장하고 다운로드 링크 제공
- **음량 맞추기 · 잡음 제거**: FFmpeg `highpass` + `afftdn` + 3kHz EQ + `loudnorm`
- **AI 잡음 제거**: FFmpeg `arnndn`(RNNoise 신경망), 모델 `backend/app/assets/rnnoise/sh.rnnn` ([GregorR/rnnoise-models](https://github.com/GregorR/rnnoise-models) somnolent-hogwash, 저작권 대상 아님으로 명시). 로컬 처리, 추가 비용 없음
- **AI 시작음**: [ElevenLabs Music API](https://elevenlabs.io/docs/api-reference/music/compose) `POST /v1/music` (`force_instrumental`). 프롬프트는 AI 키워드로 초안을 만들고 사용자가 수정. 사용자 단위로 보관해 다른 에피소드에서도 재사용. `ELEVENLABS_API_KEY`가 없으면 FFmpeg 합성 차임(모의)

```text
ELEVENLABS_API_KEY=
ELEVENLABS_MUSIC_MODEL=music_v1
INTRO_PROVIDER=auto   # auto | elevenlabs | mock
```

| Method | Path | 설명 |
|---|---|---|
| GET/PUT | `/api/episodes/{id}/cuts` | 잘라낼 구간 조회 / 전체 교체 (겹치면 합침) |
| GET/POST | `/api/episodes/{id}/exports` | 내보내기 목록 / 시작 `{apply_cuts, enhance, ai_denoise, intro_id}` |
| GET | `/api/episodes/{id}/exports/{export_id}/download` | 다운로드 서명 URL |
| DELETE | `/api/episodes/{id}/exports/{export_id}` | 내보낸 파일 삭제 |
| POST | `/api/episodes/{id}/cancel` | 진행 중인 분석 취소 |
| GET | `/api/episodes/{id}/intro-prompt` | 시작음 프롬프트 초안 |
| GET/POST/DELETE | `/api/intros` | AI 시작음 목록 / 생성 / 삭제 |

## API

| Method | Path | 설명 |
|---|---|---|
| POST/GET | `/api/episodes` | 생성 / 목록 (상태·카운트 포함) |
| GET/PATCH/DELETE | `/api/episodes/{id}` | 상세(+재생 Signed URL) / 수정 / 삭제(DB+Storage) |
| POST | `/api/episodes/{id}/upload-url` | 확장자·용량 검증 후 Signed Upload URL |
| POST | `/api/episodes/{id}/upload-complete` | ffprobe 검증 → 전처리+STT 시작 |
| POST | `/api/episodes/{id}/transcribe` | 재분석 (수정 내용 초기화) |
| GET | `/api/episodes/{id}/transcript` | segments + speakers |
| PATCH | `/api/transcripts/{segment_id}` | `edited_text`, `speaker_id` |
| POST | `/api/transcripts/{segment_id}/revert` · `/restore` | 원문으로 / 삭제 복원 |
| DELETE | `/api/transcripts/{segment_id}` | Soft Delete |
| GET | `/api/episodes/{id}/speakers` | 문장 수·비율·대표 구간·의심 여부 + 직전 병합 |
| PATCH | `/api/speakers/{speaker_id}` | 이름·색 |
| POST | `/api/episodes/{id}/speakers/merge` · `/merge/undo` | 병합 / 되돌리기 |
| POST | `/api/episodes/{id}/ai/analyze` | AI 분석 (즉시 응답, Background) |
| GET | `/api/episodes/{id}/ai` | 요약·키워드·제목 후보·챕터·하이라이트 |
| POST | `/api/episodes/{id}/ai/title` | 선택한 제목 저장 |
