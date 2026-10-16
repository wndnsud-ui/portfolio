# 모두의 소파 — 팟캐스트 MVP 개발 업무지시서 v4 (통합본)

> 작성일: 2026-10-16
> v3를 기준으로 v2의 기술 보완 사항(STT 파이프라인, 재생 정확도, 상태 관리, 보안)과 화면 설계(Claude Design 캔버스 "모두의 소파 MVP 화면")를 합친 최종 통합본이다.
> 서비스명은 **모두의 소파**이며, 기존 문서의 "CASTORY AI"는 모두 이 이름으로 대체한다.

---

## 0. v4 변경 요약

| 구분 | v3 | v4 |
|---|---|---|
| 서비스명 | CASTORY AI | **모두의 소파** |
| 로그인 | 정의 없음 | **카카오 로그인** (Supabase Auth Kakao Provider) |
| STT | "OpenAI STT" | `gpt-4o-transcribe-diarize` + `diarized_json` |
| 긴 오디오 | 단일 파일 그대로 처리 | FFmpeg 전처리 → 20분 분할 → offset 보정 → 화자 통합 |
| 재생 정확도 | 원본 재생 | 재생용 CBR 파일 + 단일 재생 소스 + 서버 peaks |
| 텍스트 저장 | `original_text` / `edited_text` | 유지 (v3 채택) |
| 화자 | `episode_speakers` | 유지 + **병합(merge) API** 추가 |
| AI 결과 저장 | 저장 위치 없음 | `ai_results` 테이블 추가 |
| 상태 | `status` 하나 + `error_stage` | `status`(오디오/STT) + `ai_status` 분리, `error_stage` 유지 |
| 멈춘 작업 | 대책 없음 | 서버 시작 시 `failed` 정리 + 중복 실행 방지 |
| 업로드 | FastAPI 경유 | Signed Upload URL로 Storage 직접 업로드 |
| 현재 문장 강조 | `start ≤ t < end` | "t 이전에 시작한 마지막 문장" 이진 탐색 (무음 구간 대응) |
| 화면 | 텍스트 레이아웃만 | 7개 화면 설계 완료 (14장) |
| 검증 | 합격 기준 일부 모호 | 수치 기준 명시 (seek 오차 0.5초 등) |

---

## 1. 프로젝트 개요

### 서비스명
**모두의 소파**

### 목적
사용자가 팟캐스트 음성 파일을 업로드하면 AI가 화자별 Transcript를 만들고, Transcript 문장을 클릭하면 실제 오디오의 해당 발언 시점으로 정확하게 이동하는 AI 팟캐스트 제작 서비스를 구현한다.

최종적으로는 텍스트 기반 오디오 편집, Short Clip 제작, 배포 기능으로 확장할 수 있도록 설계하되, 1차 MVP에서는 기능 범위를 제한한다.

### 핵심 흐름

```text
카카오 로그인
  ↓
대시보드 → 새 에피소드
  ↓
파일 선택 → 브라우저에서 1차 검증 (형식·용량)
  ↓
Signed URL로 Storage 직접 업로드
  ↓
업로드 완료 통보 → 서버 검증 (ffprobe: 실제 형식·길이·재생 가능)
  ↓
[Background] 전처리 (FFmpeg)
  ├ 재생용 CBR 파일
  ├ Waveform peaks
  └ STT용 20분 청크
  ↓
[Background] 청크별 STT → offset 보정 → 겹침 제거 → 화자 통합
  ↓
Segment / Speaker DB 저장 (status = transcribed)
  ↓
[Background] AI 분석 (요약·제목·챕터·하이라이트, ai_status)
  ↓
에디터: 문장 클릭 → 해당 시점 재생 / 화자 이름·병합 / 문장 수정
```

### 성공 기준

1. **사용자가 Transcript 문장을 클릭했을 때 실제 오디오의 해당 발언 시점으로 정확하게(오차 0.5초 이내) 이동한다.** 파일 후반부(30분 이후)에서도 동일해야 한다.
2. **AI는 Chapter와 Highlight의 시간을 만들지 않는다.** AI는 Segment ID만 고르고, 시간은 Backend가 DB에서 확정한다.

### MVP 완료 기준

1. 카카오 로그인, 본인 에피소드만 접근
2. MP3 / WAV / M4A 업로드 (최대 90분, 500MB)
3. 긴 오디오 포함 화자별 Transcript 생성
4. 문장 클릭 → 해당 시점 이동, 재생 중 문장 강조
5. 화자 이름 변경 / 병합
6. 문장 수정 (원문 보존), Soft Delete / 복원
7. AI 요약 · 키워드 · 제목 추천 · 챕터 · 하이라이트
8. 실패 시 재시도 (STT / AI 각각), 서버 재시작 시 작업 정리

---

## 2. 기술 스택

### Frontend
- React + TypeScript + Vite
- React Router
- Axios
- Zustand
- Wavesurfer.js (media element 연결, 서버 peaks 사용)
- Supabase JS Client (Kakao OAuth, Signed Upload)

### Backend
- FastAPI (Python 3.11+)
- PostgreSQL (Supabase DB)
- SQLAlchemy 2.x + Alembic
- Supabase Auth / Storage
- FFmpeg / ffprobe
- OpenAI API
  - STT: `gpt-4o-transcribe-diarize`, `response_format=diarized_json`
  - LLM: 요약·제목·챕터·하이라이트 (모델명은 환경변수)

### MVP에서 도입하지 않음
Redis, Celery, Kafka, 별도 Worker 서비스, 마이크로서비스, 실시간 협업 서버

### STT 모델 제약 (착수 시점에 공식 문서로 재확인)
- 요청당 파일 최대 25MB
- 30초 초과 입력 시 `chunking_strategy` 필요
- 청크 길이 제한 존재 (출시 당시 약 1400초) → **20분 단위 분할**
- prompt 파라미터 미지원
- 참조 음성 없이 호출하면 화자 라벨이 `A`, `B` 형태이며 **청크 간 라벨 일치 보장 없음**

---

## 3. 인증 — 카카오 로그인

### 방식
- **Supabase Auth의 Kakao Provider**를 사용한다. 자체 OAuth 서버를 만들지 않는다.
- 로그인 화면에는 **카카오 로그인 버튼 하나만** 둔다. 처음 로그인하면 자동 가입된다.
- Frontend: `supabase.auth.signInWithOAuth({ provider: 'kakao' })`
- Backend: 모든 API 요청의 `Authorization: Bearer <Supabase JWT>`를 검증해 `user_id`를 얻는다.

### 설정 (착수 전 체크리스트)
- [ ] Kakao Developers에 앱 등록, 카카오 로그인 활성화
- [ ] Redirect URI에 `https://<project-ref>.supabase.co/auth/v1/callback` 등록
- [ ] Supabase 대시보드 → Authentication → Providers → Kakao에 REST API 키와 Client Secret 입력
- [ ] 동의항목 확인: 닉네임·프로필 사진. **이메일(account_email)은 카카오 정책상 추가 심사나 비즈 앱 전환이 필요할 수 있으므로**, 이메일 없이도 가입이 되도록 Supabase 설정과 코드를 맞춘다
- [ ] 로그인 버튼은 카카오 디자인 가이드(노란색 `#FEE500`, 말풍선 심볼, "카카오 로그인" 문구)를 따른다

### 사용자 정보
- `auth.users`를 그대로 사용하고 별도 users 테이블은 만들지 않는다.
- 화면에 표시할 이름은 카카오 닉네임(`user_metadata`)을 사용한다.

### 접근 제어
- 모든 Episode 조회·수정 쿼리에 `user_id` 조건을 넣는다.
- 다른 사용자의 `episode_id`로 요청하면 **404**를 반환한다 (존재 여부를 노출하지 않음).

---

## 4. 프로젝트 폴더 구조

```text
modu-sofa/
├── frontend/
│   └── src/
│       ├── api/          client.ts, episodeApi.ts, uploadApi.ts, transcriptApi.ts, speakerApi.ts, aiApi.ts
│       ├── lib/          supabase.ts
│       ├── components/
│       │   ├── audio/       AudioPlayer.tsx, Waveform.tsx, PlaybackControls.tsx
│       │   ├── transcript/  TranscriptEditor.tsx, TranscriptLine.tsx, SegmentEditForm.tsx, SpeakerBadge.tsx
│       │   ├── speaker/     SpeakerManager.tsx, SpeakerMergeDialog.tsx
│       │   ├── episode/     EpisodeSidebar.tsx, EpisodeCard.tsx
│       │   ├── upload/      FileDropzone.tsx, FileValidationList.tsx
│       │   ├── status/      ProcessingSteps.tsx
│       │   └── ai/          AiAssistant.tsx, SummaryCard.tsx, TitleSuggestions.tsx, ChapterList.tsx, HighlightCard.tsx
│       ├── pages/        LoginPage.tsx, DashboardPage.tsx, UploadPage.tsx, ProcessingPage.tsx, EditorPage.tsx
│       ├── hooks/        useAuth.ts, useAudioPlayer.ts, useTranscriptSync.ts, useEpisodePolling.ts
│       ├── store/        episodeStore.ts, playerStore.ts
│       ├── types/        episode.ts, transcript.ts, speaker.ts, ai.ts
│       └── App.tsx
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/       episodes.py, uploads.py, transcripts.py, speakers.py, ai.py
│   │   ├── services/      audio_service.py, transcription_service.py, speaker_merge_service.py,
│   │   │                  summary_service.py, chapter_service.py, highlight_service.py,
│   │   │                  storage_service.py, job_recovery_service.py
│   │   ├── repositories/  episode_repo.py, segment_repo.py, speaker_repo.py, ai_repo.py
│   │   ├── models/        episode.py, speaker.py, transcript.py, ai_result.py, chapter.py, highlight.py
│   │   ├── schemas/       episode.py, transcript.py, speaker.py, ai.py
│   │   ├── db/            session.py
│   │   ├── core/          config.py, auth.py
│   │   └── utils/         ffmpeg_utils.py
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
│
├── .env.example
├── docker-compose.yml
└── README.md
```

- v3의 `worker/` 폴더, `audio_edit_service.py`, `routers/audio.py`는 MVP 범위가 아니므로 만들지 않는다.

---

## 5. DB 구조

### episodes

```text
id                uuid PK
user_id           uuid        -- auth.users.id
title             text
description       text
original_path     text        -- Storage: 원본
playback_path     text        -- Storage: 재생용 CBR
peaks_path        text        -- Storage: waveform peaks JSON
duration          float       -- 초 (재생용 파일 기준)
file_size         bigint
status            text        -- 아래
ai_status         text        -- 아래
error_stage       text        -- upload | processing | transcription | ai
error_message     text
progress_current  int         -- 처리한 청크 수
progress_total    int         -- 전체 청크 수
status_updated_at timestamptz
created_at        timestamptz
updated_at        timestamptz
```

#### status (오디오 + STT)

```text
created → uploading → uploaded → processing → transcribing → transcribed
                                                   ↘ failed
```

#### ai_status (STT와 독립)

```text
none → running → completed
            ↘ failed
```

- AI가 실패해도 `status = transcribed`가 유지되어 Transcript는 정상 사용된다.
- 서버 재시작으로 중단되면 `status = failed`, `error_stage`는 중단된 단계, `error_message = "서버 재시작으로 작업이 중단되었습니다"`.

### episode_speakers

```text
id            uuid PK
episode_id    uuid FK
speaker_code  text      -- SPEAKER_01 (통합 후 라벨)
display_name  text      -- 혜영 (NULL이면 speaker_code 표시)
color         text
created_at
updated_at
UNIQUE(episode_id, speaker_code)
```

### transcript_segments

```text
id             uuid PK
episode_id     uuid FK
speaker_id     uuid FK → episode_speakers.id
seq            int       -- 정렬 기준
start_time     float     -- 초, 전체 오디오 기준 (offset 보정 완료)
end_time       float
original_text  text      -- STT 결과, 절대 수정하지 않음
edited_text    text NULL -- 사용자 수정본
is_deleted     boolean default false
created_at
updated_at
INDEX(episode_id, seq)
INDEX(episode_id, start_time)
```

- 화면 표시와 AI 입력 모두 **`edited_text ?? original_text`** 를 사용한다.
- "원문으로 되돌리기"는 `edited_text = NULL`로 처리한다.

### ai_results

```text
id               uuid PK
episode_id       uuid FK UNIQUE
summary          text
keywords         jsonb    -- ["재물운", "재성", "대운"]
title_candidates jsonb    -- ["...", "...", "..."]
model            text
created_at
updated_at
```

### chapters

```text
id                uuid PK
episode_id        uuid FK
start_segment_id  uuid FK → transcript_segments.id
start_time        float    -- Backend가 Segment에서 복사
title             text
description       text
seq               int
```

### highlights

```text
id                uuid PK
episode_id        uuid FK
start_segment_id  uuid FK
end_segment_id    uuid FK
start_time        float    -- start_segment.start_time
end_time          float    -- end_segment.end_time
title             text
text              text     -- Backend가 구간 Segment 텍스트를 이어 붙여 생성
seq               int
```

---

## 6. Backend API

모든 API는 Supabase JWT가 필요하다.

### Episode

```text
POST   /api/episodes
GET    /api/episodes                       -- 목록 (status, ai_status 포함)
GET    /api/episodes/{id}                  -- 상세 + 진행률 + 재생용 Signed URL
PATCH  /api/episodes/{id}
DELETE /api/episodes/{id}                  -- DB + Storage 파일 함께 삭제
```

### Upload

```text
POST /api/episodes/{id}/upload-url        -- 확장자·용량 검증 후 Signed Upload URL 발급, status = uploading
POST /api/episodes/{id}/upload-complete   -- ffprobe 검증 → status = uploaded → 전처리+STT 시작
```

### Transcript

```text
POST   /api/episodes/{id}/transcribe      -- 재분석 (사용자 수정 내용 초기화 경고 후)
GET    /api/episodes/{id}/transcript      -- segments + speakers
PATCH  /api/transcripts/{segment_id}      -- { "edited_text": "...", "speaker_id": "..." }
POST   /api/transcripts/{segment_id}/revert   -- edited_text = NULL
DELETE /api/transcripts/{segment_id}      -- is_deleted = true
POST   /api/transcripts/{segment_id}/restore  -- is_deleted = false
```

### Speaker

```text
GET   /api/episodes/{id}/speakers         -- 화자별 문장 수, 대표 구간 시간 포함
PATCH /api/speakers/{speaker_id}          -- { "display_name": "혜영", "color": "#..." }
POST  /api/episodes/{id}/speakers/merge   -- { "from_id": "...", "into_id": "..." }
POST  /api/episodes/{id}/speakers/merge/undo   -- 직전 병합 되돌리기
```

- `merge`: `from` 화자의 Segment를 모두 `into`로 옮기고 `from` 화자를 삭제한다. 되돌리기를 위해 옮긴 Segment ID 목록을 보관한다.
- 대표 구간: 해당 화자의 가장 긴 Segment의 start/end.

### AI

```text
POST /api/episodes/{id}/ai/analyze        -- 요약+제목+챕터+하이라이트 일괄, 즉시 응답 후 Background
GET  /api/episodes/{id}/ai                -- ai_results + chapters + highlights
POST /api/episodes/{id}/ai/title          -- { "title": "선택한 제목" } → episodes.title
```

- 긴 작업 API는 모두 **즉시 `{ "episode_id", "status" }`를 응답**하고 Background에서 처리한다.

---

## 7. 오디오 전처리와 STT 파이프라인

**MVP에서 가장 어려운 부분이다. 1순위로 구현하고, 40분 이상 실제 파일로 먼저 검증한다.**

### 7-1. 전처리 (FFmpeg)

| 산출물 | 목적 | 권장 설정 |
|---|---|---|
| 재생용 파일 | 정확한 seek | MP3 CBR 128kbps, 44.1kHz |
| STT용 청크 | 25MB·길이 제한 회피 | 모노, 16kHz, 64kbps 이하, 20분 단위 |
| peaks JSON | 파형 표시 | 초당 20~50 포인트 |

- **재생은 항상 재생용 파일로 한다.** 원본 VBR MP3를 브라우저에서 seek하면 수 초 어긋날 수 있다.
- 변환 후 ffprobe로 재생용 파일의 duration을 다시 재서 `episodes.duration`에 저장한다.

### 7-2. 분할

- 청크 20분, 겹침 15초
- 청크 i의 `offset` = 원본 기준 시작 시각(초)

```text
청크 0: 00:00 ~ 20:00   offset = 0
청크 1: 19:45 ~ 39:45   offset = 1185
청크 2: 39:30 ~ 끝      offset = 2370
```

### 7-3. STT 호출

```python
client.audio.transcriptions.create(
    model=settings.OPENAI_STT_MODEL,      # gpt-4o-transcribe-diarize
    file=chunk_file,
    response_format="diarized_json",
    chunking_strategy="auto",
)
```

- 순차 또는 동시 2개 이하 (Rate limit)
- 청크 단위 최대 3회 재시도 (지수 백오프)
- 청크마다 `progress_current` 갱신 → 화면에 "구간 2 / 3" 표시
- 청크 원본 응답 JSON은 디버깅용으로 Storage에 보관

### 7-4. Offset 보정

```text
start_time = segment.start + chunk.offset
end_time   = segment.end   + chunk.offset
```

### 7-5. 겹침 제거와 화자 통합

1. 겹침 구간의 중간 시각을 경계로, 이전 청크는 경계 이전, 다음 청크는 경계 이후 Segment만 채택한다.
2. 겹침 구간에서 시간이 가장 많이 겹치는 화자끼리 같은 화자로 본다. (예: 청크 0의 `B` = 청크 1의 `A` → `SPEAKER_02`)
3. 매칭되지 않은 화자는 새 `SPEAKER_NN`으로 등록한다.
4. 자동 매칭은 완벽하지 않으므로 **화자 병합 화면**으로 보정한다.

> 2차 개선: 첫 청크에서 화자별 대표 음성을 잘라 known speaker reference로 다음 청크에 전달.

### 7-6. 저장

- 전체 Segment를 `start_time`으로 정렬해 `seq` 부여
- speakers + segments를 한 트랜잭션으로 저장
- 재분석 시 기존 segments / speakers / AI 결과를 삭제 후 재생성한다. **화면에서 반드시 경고한다** (14장 ⑦).

---

## 8. Transcript ↔ Audio 동기화

### 규칙
1. **재생 소스는 `<audio>` 하나.** Wavesurfer는 `media` 옵션으로 이 요소에 연결한다. 모든 seek/play는 이 요소로만 한다.
2. Waveform은 서버 peaks를 사용한다. 브라우저에서 전체 오디오를 디코딩하지 않는다.
3. 재생 URL은 `playback_path`의 Signed URL. 만료되면 재발급한다.
4. Storage가 HTTP Range 요청을 지원하는지 확인한다.

### Seek

```tsx
const handleSeek = (startTime: number) => {
  const audio = audioRef.current;
  if (!audio) return;
  audio.currentTime = startTime;
  void audio.play();
};
```

### 현재 문장 강조
- `timeupdate`마다 **"현재 시각 이전에 시작한 마지막 Segment"** 를 이진 탐색으로 찾는다.
  - v3의 `start ≤ t < end` 조건은 문장 사이 무음 구간에서 아무 줄도 강조되지 않으므로 사용하지 않는다.
  - 다음 Segment 시작 전까지는 직전 Segment를 계속 강조한다.
- 강조된 줄이 화면 밖이면 자동 스크롤한다. 사용자가 직접 스크롤 중이면 잠시 멈춘다.

### Soft Delete된 문장
- MVP에서는 오디오를 자르지 않으므로 재생은 그대로 진행한다.
- 화면: 취소선 + "삭제됨 · 오디오에는 그대로 남아 있어요" + [복원]
- AI 입력에서는 제외한다.

---

## 9. AI Assistant

### 공통 원칙
- LLM 입력 형식:

```text
[seg=3f2a…][00:12.4][혜영] 재물운이 좋다고 해서 반드시 돈이 많은 것은 아닙니다.
```

- 텍스트는 `edited_text ?? original_text`, 화자는 `display_name ?? speaker_code`
- `is_deleted = true` 문장 제외
- **LLM은 시간을 반환하지 않는다. Segment ID만 반환한다.**
- 출력은 JSON Schema(Structured Outputs)로 강제한다.
- Backend는 반환된 ID가 해당 Episode에 실제 존재하는지 검증한다. 없는 ID가 섞이면 그 항목만 버리고, 유효 항목이 최소 개수에 못 미치면 1회 재요청 후 실패 처리한다.
- 컨텍스트 한도를 넘으면 구간별 요약 후 합친다(map-reduce).

### 요약 · 키워드 · 제목 후보

```json
{
  "summary": "...",
  "keywords": ["재물운", "재성", "대운"],
  "title_candidates": ["재물운은 어떻게 판단할까?", "재성이 많으면 정말 부자가 될까?", "돈복을 보는 세 가지 기준"]
}
```

선택한 제목만 `episodes.title`에 저장한다.

### 챕터

```json
{ "chapters": [ { "start_segment_id": "…", "title": "재성의 의미", "description": "…" } ] }
```

- 첫 챕터는 첫 Segment에서 시작
- 시간 오름차순
- 10분당 1~2개, 최소 3개 최대 12개

### 하이라이트

```json
{ "highlights": [ { "start_segment_id": "…", "end_segment_id": "…", "title": "재물운의 핵심" } ] }
```

- start가 end보다 앞이거나 같음
- 구간 길이 15~90초, 3~6개
- **인용문 텍스트는 Backend가 실제 Segment 텍스트로 만든다** (LLM이 문장을 지어내지 못하게)
- MVP는 클릭 시 해당 구간 재생까지. Clip 생성은 2차.

---

## 10. 비동기 작업과 상태 관리

### 구조
- FastAPI `BackgroundTasks` 사용, uvicorn worker 1개
- Frontend는 처리 중일 때 `GET /api/episodes/{id}`를 3~5초 간격으로 polling

### 멈춘 작업 정리 (필수)
- 서버 시작 시 `status ∈ {processing, transcribing}` 또는 `ai_status = running`인 Episode를 `failed`로 바꾸고 `error_stage`, `error_message` 기록
- 상태 변경 시 `status_updated_at` 갱신

### 중복 실행 방지
- 작업 시작 시 조건부 UPDATE로 상태를 선점한다.

```sql
UPDATE episodes SET status = 'processing', status_updated_at = now()
WHERE id = :id AND status IN ('uploaded', 'failed')
RETURNING id;
```

- 반환 행이 없으면 이미 다른 작업이 진행 중이므로 시작하지 않는다.

### 2차에서 Worker Queue로 전환하는 기준
- 동시 처리 에피소드가 자주 3개 이상
- 서버 재시작 중단이 운영상 문제
- 90분 초과 오디오 지원 필요

---

## 11. 오류 처리

### 업로드 (화면 ③)

| 상황 | 검사 위치 | 문구 |
|---|---|---|
| 형식이 MP3/WAV/M4A 아님 | 브라우저 + 서버 | 지원하지 않는 형식이에요. MP3, WAV, M4A 파일만 올릴 수 있어요. |
| 90분 초과 | 서버(ffprobe) | 90분까지 올릴 수 있어요. 파일을 나눠서 올려 주세요. |
| 500MB 초과 | 브라우저 + 서버 | 500MB까지 올릴 수 있어요. |
| 확장자는 맞지만 재생 불가 | 서버(ffprobe) | 파일을 재생할 수 없어요. 내용이 손상되었을 수 있어요. |
| 음성 없음 (Segment 0개) | STT 후 | 음성을 찾지 못했어요. |

### STT 실패 (화면 ④)

```text
status = failed, error_stage = transcription
```

```text
음성 분석 중 오류가 발생했습니다.
구간 2를 처리하지 못했어요. 업로드한 파일은 그대로 있으니 다시 시도할 수 있어요.
[다시 분석하기]
```

### 서버 재시작 중단 (화면 ④)

```text
서버 점검으로 분석이 중단됐어요.
파일은 그대로 있으니 다시 분석하면 처음부터 다시 진행해요.
[다시 분석하기]
```

### AI 실패 (화면 ⑦)

```text
ai_status = failed (status = transcribed 유지)
```

```text
AI 분석에 실패했어요
대본과 재생은 그대로 쓸 수 있어요. 요약 · 제목 추천 · 챕터 · 하이라이트만 다시 만들면 돼요.
[AI 분석 다시 실행]
```

---

## 12. 환경변수, Storage

### 환경변수

```text
# Backend
DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=      # Backend 전용, Frontend 노출 금지
SUPABASE_JWT_SECRET=
STORAGE_BUCKET=
OPENAI_API_KEY=
OPENAI_STT_MODEL=gpt-4o-transcribe-diarize
OPENAI_LLM_MODEL=
MAX_UPLOAD_MB=500
MAX_DURATION_SEC=5400
STT_CHUNK_SEC=1200
STT_OVERLAP_SEC=15

# Frontend (VITE_ 접두사)
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_API_BASE_URL=
```

- 카카오 REST API 키와 Client Secret은 **Supabase 대시보드에만** 입력하고 코드·`.env`에 넣지 않는다.
- `.env`는 Git에 올리지 않고 `.env.example`만 커밋한다.

### Storage
- 버킷은 private
- 경로: `{user_id}/{episode_id}/original.ext`, `playback.mp3`, `peaks.json`, `chunks/…`, `stt_raw/…`
- 재생 URL은 Signed URL(예: 1시간)
- 착수 전 Supabase 플랜의 파일 크기 제한 확인 (90분 WAV는 900MB 이상일 수 있음)
- CORS를 Frontend 도메인으로 허용

---

## 13. 개발 우선순위

### 1순위 — 기반과 파이프라인
```text
카카오 로그인 (Supabase Auth) + JWT 검증
Episode CRUD
Signed Upload + 서버 검증
FFmpeg 전처리 (재생용 파일, peaks, 청크)
STT + offset 보정 + 화자 통합
Segment / Speaker 저장
멈춘 작업 정리 / 중복 실행 방지
```
> 1순위가 끝나면 **40분 이상 실제 팟캐스트 파일로 검증**한다. 청크 경계(20분, 40분)에서 문장 누락·중복·화자 불일치를 확인한다.

### 2순위 — 에디터
```text
Audio Player (단일 소스) + Waveform (peaks)
문장 클릭 Seek + 현재 문장 강조 + 자동 스크롤
```

### 3순위 — 편집
```text
문장 수정 (edited_text) / 원문 보기 / 되돌리기
Soft Delete / 복원
화자 이름 변경 / 병합 / 병합 되돌리기
```

### 4순위 — AI
```text
요약 · 키워드 · 제목 추천 · 챕터 · 하이라이트
```

### 5순위 — 마무리
```text
UI 정리, Docker, 배포
```

---

## 14. 화면 설계

Claude Design 캔버스 **"모두의 소파 MVP 화면"** 에 7개 화면이 있다. 각 화면은 Play로 실행해 동작을 확인할 수 있다.

| # | 화면 | 핵심 요소 | 관련 장 |
|---|---|---|---|
| ① | 로그인 | 카카오 로그인 버튼 하나, 자동 가입 안내 | 3 |
| ② | 대시보드 | 업로드 영역, 에피소드 카드 (분석 중 진행률 / 분석 실패 / AI만 실패 / 완료) | 5, 10 |
| ③ | 업로드 · 파일 검증 | 제목(선택), 드롭존, 형식·길이·용량·재생 가능 체크, 업로드 진행률, 오류 3종 | 6, 11 |
| ④ | 분석 진행 상태 | 5단계 (업로드 → 오디오 준비 → 음성 분석(구간 n/3) → Transcript 생성 → AI 분석), 실패 / 서버 중단 상태 | 7, 10, 11 |
| ⑤ | 에디터 | 3단 레이아웃 + 하단 플레이어, 문장 클릭 이동, 현재 문장 강조, 챕터 마커 파형, 하이라이트 재생, 제목 선택 반영, 삭제 문장 표시 | 8, 9 |
| ⑥ | 화자 이름 · 병합 | 화자별 문장 수·비율, 대표 구간 듣기, 의심 화자 강조, 병합 대화상자, 되돌리기 | 6, 7-5 |
| ⑦ | 문장 수정 · 재분석 · AI 실패 | 수정 중 STT 원문 표시, "수정됨" + 원문 보기·되돌리기, 재분석 경고 대화상자, AI 실패 안내 | 5, 7-6, 11 |

### 에디터 레이아웃

```text
┌──────────────┬──────────────────────────┬────────────────┐
│ 사이드바      │ [트랜스크립트][챕터][화자] │ AI Assistant   │
│ 홈           │ 검색 · 화자 필터           │ [요약][제목]   │
│ 프로젝트      │ 시간 | 화자 | 문장         │ [챕터][하이라이트]│
│ 파일 업로드   │                          │                │
│ 최근 프로젝트 │                          │                │
├──────────────┴──────────────────────────┴────────────────┤
│ 00:14 / 42:13  ⟲10 ▶ 10⟳ 1x | 챕터 마커 + 파형 | 볼륨        │
└──────────────────────────────────────────────────────────┘
```

### MVP에서 화면에 넣지 않는 것
녹음하기, 미디어 라이브러리, 편집 탭, 노이즈 개선 탭, Clip 만들기, 전체 하이라이트 클립 만들기, 공유, 내보내기, 저장공간/업그레이드, 자막·영상·전체화면 아이콘, 화자 사진 아바타(이니셜 배지로 대체), 댓글, 좋아요, 공개 에피소드 페이지

---

## 15. MVP 제외 기능

- 실시간 공동 편집, 실시간 녹음 협업
- 녹음 기능
- 영상 팟캐스트
- AI 음성 복제, 음성 직접 수정
- 자동 번역
- Shorts / Clip 생성
- 텍스트 삭제 → 실제 Audio Cut, 완성 오디오 Export
- 공유, 공개 에피소드, 댓글, 좋아요, Social 업로드
- Spotify / Apple Podcast 배포
- 구독, 결제, 광고, 저장공간 요금제
- 노이즈 제거

MVP 완료 전에는 기능 추가 요청이 있어도 구현하지 않는다.

---

## 16. 개발 완료 검증

| # | 테스트 | PASS 조건 |
|---|---|---|
| 1 | 카카오 로그인 | 첫 로그인 시 자동 가입, 재로그인 시 같은 계정, 로그아웃 후 API 401 |
| 2 | 접근 제어 | 다른 사용자의 episode_id로 호출 시 404 |
| 3 | 긴 파일 업로드 | 40분 이상·30MB 이상 MP3 업로드 → `status = uploaded`, duration 정상 |
| 4 | 포맷별 처리 | MP3(VBR 포함) / WAV / M4A 각각 재생용 파일과 peaks 생성 |
| 5 | 잘못된 파일 | mp4, 90분 초과, 손상 파일 각각 11장 문구로 차단 |
| 6 | STT | 모든 Segment에 speaker·start·end 존재, 마지막 end ≤ duration, 청크 경계 ±30초 내 누락·중복 없음 |
| 7 | 진행률 | 처리 중 "구간 n / 전체" 갱신 |
| 8 | Seek 정확도 | 무작위 20개 문장 클릭, 실제 발화 시작과 오차 0.5초 이내 (30분 이후 문장 포함) |
| 9 | 현재 문장 강조 | 파형 클릭·±10초 이동·무음 구간에서도 올바른 줄 강조 + 자동 스크롤 |
| 10 | 문장 수정 | `original_text` 불변, `edited_text`만 변경, 되돌리기 시 NULL |
| 11 | Soft Delete | Row 유지, `is_deleted = true`, 복원 가능, AI 입력에서 제외 |
| 12 | 화자 | 이름 변경 즉시 전체 반영, 병합 후 화자 수 감소, 되돌리기 시 원상복구 |
| 13 | AI 요약·제목 | 요약·키워드·제목 후보 3개, 선택 제목 저장 |
| 14 | 챕터 | 모든 start_time이 실제 Segment start_time과 일치, 오름차순 |
| 15 | 하이라이트 | 클릭 시 구간 재생, 인용문이 실제 Segment 텍스트와 일치 |
| 16 | STT 실패 | `status = failed`, `error_stage = transcription`, [다시 분석하기]로 완료 |
| 17 | 서버 재시작 | 처리 중 재시작 → `failed` 표시 → 재분석 성공, 중복 실행 없음 |
| 18 | AI 실패 | Transcript 유지, [AI 분석 다시 실행]으로 완료 |
| 19 | 재분석 경고 | 수정 내용이 있을 때 경고 대화상자 표시 후에만 실행 |

---

## 17. 구현 원칙

1. 기존 코드가 있으면 구조를 먼저 확인하고, 파일 전체를 덮어쓰지 않는다. 필요한 파일만 수정한다.
2. 기존 Router 연결, DB Schema, 환경변수를 먼저 확인하고 변경 영향 범위를 파악한다.
3. Schema 변경은 Alembic 마이그레이션으로만 한다.
4. Router → Service → Repository / External API 구조를 지킨다. Router에 비즈니스 로직을 쓰지 않는다.
5. API Key, Service Role Key, 카카오 키를 코드나 Frontend에 넣지 않는다.
6. Timestamp는 초 단위 Float, 전체 오디오 기준(offset 보정 완료)으로 저장한다.
7. Transcript는 Segment 단위로만 저장하고, `original_text`는 수정하지 않는다.
8. 재생은 재생용 변환 파일로, `<audio>` 하나로만 한다.
9. LLM에게 시간을 만들게 하지 않는다. Segment ID로 받고 Backend가 시간을 확정한다.
10. 하이라이트 인용문은 실제 Segment 텍스트로 만든다.
11. 긴 작업은 요청-응답 안에서 처리하지 않는다.
12. 서버 재시작 시 멈춘 작업을 정리하고, 작업 시작은 조건부 UPDATE로 선점한다.
13. STT 모델 제한은 착수 시점 공식 문서로 재확인하고, 다르면 `STT_CHUNK_SEC`만 조정한다.
14. 개발 완료 후 40분 이상 실제 팟캐스트 파일로 전체 흐름을 테스트한다.
15. 기존 정상 기능이 유지되는지 확인한 뒤 Commit한다.

---

## 18. 2차 개발 후보 (MVP 안정화 이후)

```text
텍스트 삭제 → Audio Cut (새 Audio Version 생성)
삭제 구간 건너뛰며 미리듣기
Highlight → Short Clip
화자 known reference로 청크 간 화자 일치 개선
Worker Queue 전환
공유 / 공개 에피소드 / 내보내기
Spotify / Apple Podcast 배포
```
