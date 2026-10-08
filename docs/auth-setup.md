# Google 로그인과 비밀번호 재설정 메일 설정

## Google 로그인

1. https://console.cloud.google.com/ 에서 프로젝트를 선택하거나 생성합니다.
2. Google Auth Platform에서 브랜딩(앱 이름, 지원 이메일)과 대상(외부, 테스트 사용자)을 설정합니다.
3. 클라이언트에서 **웹 애플리케이션** OAuth 클라이언트를 생성합니다.
4. 로컬 승인된 리디렉션 URI: `http://127.0.0.1:8001/api/auth/google/callback`
5. `.env`에 아래 값을 입력합니다. Secret은 공개하거나 Git에 올리지 않습니다.

```dotenv
GOOGLE_CLIENT_ID=발급받은-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=발급받은-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8001/api/auth/google/callback
FRONTEND_URL=http://127.0.0.1:8001
```

운영에서는 두 URL을 실제 HTTPS 사이트 주소로 바꾸고 Google에도 해당 콜백을 등록합니다. `localhost`와 `127.0.0.1`은 서로 다른 주소입니다. 로그인 시작 주소와 콜백 호스트를 일치시켜야 state 쿠키가 전달됩니다. Vite(5173)로 개발할 때는 FRONTEND_URL만 해당 프런트엔드 주소로 바꿉니다.

Google이 검증한 이메일로만 로그인하며, 기존 이메일 계정과 동일한 경우 해당 계정에 연결합니다. Google 전용 계정은 Google 로그인을 사용합니다.

## 비밀번호 재설정 메일

Gmail 사용 시 먼저 2단계 인증을 켜고 https://myaccount.google.com/apppasswords 에서 앱 비밀번호를 생성합니다.

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=발신주소@gmail.com
SMTP_PASSWORD=발급받은앱비밀번호
SMTP_FROM=발신주소@gmail.com
SMTP_SSL=false
```

다른 SMTP 제공자도 사용할 수 있습니다. 587 포트는 STARTTLS, 465 포트는 `SMTP_SSL=true`를 사용합니다.

서버를 재시작한 뒤 로그인 화면의 **비밀번호를 잊으셨나요?**에서 이메일을 입력합니다. 재설정 링크는 30분 유효하며 1회 사용 후 폐기됩니다. 비밀번호 변경 시 이전 로그인 세션과 다른 재설정 링크도 무효화됩니다. DB에는 링크 원문 대신 SHA-256 해시를 저장합니다. 계정당 1분에 1회, 시간당 5회까지 메일을 보냅니다.

설정 전에는 메일 서비스 미설정 안내를 표시하며, API 응답이나 서버 로그에 재설정 링크를 노출하지 않습니다.

공식 참고: https://developers.google.com/identity/protocols/oauth2/web-server · https://support.google.com/accounts/answer/185833
