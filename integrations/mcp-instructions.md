# HY ARCHIVE 직접 MCP 연결

서버 URL: `https://web-production-7226d.up.railway.app/mcp`
인증: OAuth (자동 검색 및 동적 클라이언트 등록). 기존 Sites 주소나 Actions API 키를 사용하지 않습니다.

ChatGPT의 새 MCP 연결에 서버 URL을 입력하고 OAuth를 선택합니다. HY ARCHIVE 관리자 계정으로 로그인한 뒤 독서 조회 및 비공개 초안 저장 권한을 승인합니다. 비밀번호나 발급된 토큰을 대화에 붙여 넣지 않습니다.

관리자의 `/admin/chatgpt` 화면에서 활성 연결을 확인하고 모두 해제할 수 있습니다. Railway의 기존 SECRET_KEY, 관리자 계정, DATABASE_URL 설정을 사용합니다. SITE_URL을 설정한다면 위 서버의 HTTPS 원점으로 지정합니다. 추가 패키지나 DB 스키마 변경은 없습니다.

## 도구 사용 순서

1. `listReadingBooks`로 『총, 균, 쇠』를 검색합니다. 결과의 실제 ID를 사용합니다.
2. `listReadingPages`, `getReadingSource`로 원문과 기존 이미지 목록을 확인합니다.
3. `getReadingDraft`로 기존 초안을 확인합니다. 기존 내용과 수정 번호를 존중합니다.
4. 원문에 근거하여 글을 정리합니다. 사용자 자신의 감상을 지어내지 않습니다. 사진은 원문 asset ID만 선택합니다.
5. `saveReadingDraft`에 source_token과 기존 수정 번호를 전달해 비공개로 저장합니다. 공개·삭제 권한은 제공하지 않습니다.
6. 실제 도구의 성공 응답을 확인한 뒤 저장된 초안 링크를 안내합니다. 연결이나 저장이 실패하면 완료됐다고 말하지 않습니다.

로컬 검증: `python -m unittest discover -s tests -q`.
HTTPS 브라우저/공식 MCP SDK 검증: 별도 검증 환경에 playwright, mcp, cryptography를 설치하고 `python tests/verify_mcp_https.py` 실행. 임시 SQLite와 명시적 가상 독서 메모만 사용하며 실제 독서 데이터에는 접근하지 않습니다.
