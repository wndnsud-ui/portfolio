# 사주 팟캐스트 에피소드 추출

긴 녹음 또는 시간 표시 녹취록을 넣고, 후보 구간을 검토한 뒤 승인된 구간만 오디오와 전사문으로 저장하는 Windows 데스크톱 앱입니다.

## 바로 실행

파일 탐색기에서 다음 파일을 더블클릭합니다.

```text
dist\PodcastEpisodeTool\PodcastEpisodeTool.exe
```

브라우저나 Python 설치 없이 독립된 프로그램 창으로 실행됩니다. 배포할 때는 `PodcastEpisodeTool` 폴더 전체를 전달해야 합니다.

다른 PC에 전달할 때는 `dist\PodcastEpisodeTool-Windows.zip`을 전달하고, 압축을 푼 뒤 EXE를 실행합니다.

## OpenAI API 키 설정

프로그램을 실행하고 화면 위쪽의 `API 키 설정` 버튼을 누릅니다. OpenAI API 키를 입력하고 확인하면 EXE 옆의 `.env` 파일에 저장되며, 화면 상태가 `API 연결됨`으로 바뀝니다.

키는 일반적으로 `sk-`로 시작합니다. 프로그램은 전사, AI 후보 분석, 임베딩 버튼을 실행할 때만 OpenAI API를 호출하며 사용량에 따라 비용이 발생할 수 있습니다. `.env`에는 비밀 키가 들어 있으므로 다른 사람에게 전달하거나 공개 저장소에 올리면 안 됩니다.

직접 설정하려면 `PodcastEpisodeTool.exe`가 있는 폴더에 `.env` 파일을 만들고 다음 한 줄을 입력합니다.

```dotenv
OPENAI_API_KEY=여기에_API_키_입력
```

구간 타임스탬프가 필요한 이 앱은 기본 전사 모델로 `whisper-1`을 사용합니다. 공식 가격은 분당 $0.006이며 1시간 전사는 약 $0.36입니다. `gpt-4o-mini-transcribe`는 더 저렴하지만 `verbose_json` 타임스탬프를 지원하지 않아 후보 구간 분할 정확도가 떨어집니다.

## 개발 환경 설치

Windows PowerShell 기준입니다. 이 프로젝트에는 이미 `.venv`가 준비되어 있으므로 현재 PC에서는 활성화만 하면 됩니다.

```powershell
cd C:\pot\podcast_episode_tool
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

PowerShell 실행 정책 때문에 활성화가 막히면 활성화 없이 가상환경의 Python을 직접 사용해도 됩니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

`.venv`가 없는 다른 PC에서는 Python 3.11 또는 3.12로 새로 만듭니다.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Conda를 사용하려면 먼저 PowerShell 초기화가 필요합니다. 이 PC의 Anaconda 경로는 `C:\Users\PC\anaconda3`입니다.

```powershell
& "C:\Users\PC\anaconda3\Scripts\conda.exe" init powershell
```

명령 실행 후 VS Code 터미널을 완전히 닫았다가 새로 열면 `conda` 명령을 사용할 수 있습니다. 이 프로젝트에서는 이미 `.venv`가 있으므로 Conda 환경을 추가로 만들 필요는 없습니다.

FFmpeg가 필요합니다. `ffmpeg -version`과 `ffprobe -version`이 실행되어야 음성 길이 확인과 분할이 됩니다.

## API 키 설정

개발 환경에서는 `.env.example`을 `.env`로 복사하고 값을 채울 수도 있습니다.

```powershell
copy .env.example .env
notepad .env
```

API 키가 없으면 `.txt` 입력과 모의 후보로 승인 흐름을 검증할 수 있습니다. 음성 전사, AI 후보 분석, 실제 임베딩은 API 키가 있어야 실행됩니다.

## 개발용 Streamlit 화면 실행

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

기존 브라우저형 개발 화면이 필요한 경우에만 사용합니다.

## Windows 데스크톱 실행파일 만들기

Python 3.11 또는 3.12가 설치된 PowerShell에서 다음 명령을 실행합니다.

```powershell
cd C:\pot\podcast_episode_tool
PowerShell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

완료되면 아래 실행파일을 더블클릭합니다.

```text
dist\PodcastEpisodeTool\PodcastEpisodeTool.exe
```

또는 프로젝트 폴더의 `run_app.cmd`를 더블클릭합니다. 실행 오류가 발생하면 창을 닫지 않고 오류 내용을 보여 주므로 문제 확인이 더 쉽습니다.

`PodcastEpisodeTool` 폴더 전체가 배포 단위입니다. EXE만 따로 옮기면 실행되지 않습니다. 브라우저나 서버 창 없이 독립된 Windows 창으로 실행되며, `.env`와 `data`는 EXE가 있는 폴더에서 읽고 저장합니다.

빌드 PC의 PATH에 FFmpeg와 FFprobe가 있으면 배포 폴더에 자동으로 포함됩니다. 빌드할 때 찾지 못하면 경고가 표시되며, 이 경우 실행하는 PC에 별도 설치해야 합니다. 없더라도 텍스트 기반 검토는 가능하지만 음성 길이 확인과 MP3 분할은 동작하지 않습니다.

## 구현 범위

- 음성 파일 또는 시간 표시 `.txt` 입력
- `.txt` 타임코드 파싱, 역순/누락 오류 표시
- OpenAI 전사 함수, 후보 분석 함수, 임베딩 함수 분리
- API 키가 없을 때 모의 후보 0~5개 생성
- 후보 제목, 질문, 시간, 전사문, 활용 유형, 공개 검토 메모 편집
- 보류/승인 상태 저장과 재실행 복원
- 승인 후보만 MP3 분할, TXT/JSON 저장, SQLite 기록
- 동일 후보와 동일 시간 재처리 중복 방지
- 결과 ZIP 다운로드

## 저장 위치

```text
data/
  recordings/<녹음ID>/
    original.<확장자>
    transcript.json
    candidates.json
    clips/
  index.sqlite3
```

`data/`, `.env`, DB, 원본과 결과물은 `.gitignore`에 포함되어 있습니다.

## 제약

- 긴 음성을 업로드 제한 이하 조각으로 자동 압축/분할 전사하는 고급 처리는 아직 단순화되어 있습니다.
- Streamlit 기본 오디오 플레이어는 지정 구간만 잘라 미리듣는 UI가 아니라 원본을 재생하고 사용자가 시간대로 이동하는 방식입니다.
- API 키가 없는 환경에서는 실제 OpenAI 전사/분석/임베딩 경로가 검증되지 않습니다.
