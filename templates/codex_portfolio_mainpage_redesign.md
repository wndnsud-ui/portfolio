# Codex 업무지시서 — Portfolio Main Page UI Redesign

## 작업 목적

현재 Flask 기반 개인 포트폴리오의 **메인페이지(`/`) 디자인만 개선한다.**

현재 디자인은 카드와 색상 블록이 많고 대형 영문 타이포그래피 비중이 높아 다소 복잡하고 포스터처럼 보이는 문제가 있다.

이번 개편의 목표는 다음과 같다.

> **화려한 포트폴리오가 아니라, 차분하고 정돈된 에디토리얼 포트폴리오**

사용자가 첫 화면에서 자연스럽게 다음 세 가지를 이해할 수 있어야 한다.

**최혜영은 누구인가 → 어떻게 문제를 다루는가 → 어떤 프로젝트를 했는가**

---

## 1. 작업 범위

현재 프로젝트 구조를 먼저 확인한 후 작업한다.

중요하게 확인할 파일은 다음과 같다.

```text
templates/home-reference.html
templates/base.html
static/css/style.css
static/js/main.js
app.py
```

현재 `/` 라우트는 `home.html`이 아니라 **`home-reference.html`을 렌더링하고 있으므로 반드시 `home-reference.html`을 기준으로 수정한다.**

`home.html`은 이번 작업에서 수정하지 않아도 된다.

백엔드 구조, 데이터베이스 모델, 관리자 페이지, Archive CRUD, Project CRUD 등은 수정하지 않는다.

---

## 2. 디자인 방향

이번 메인페이지의 디자인 키워드는 다음과 같다.

```text
QUIET EDITORIAL
MINIMAL
CLEAR
STRUCTURED
PROFESSIONAL
WARM
```

현재의 Bento/Card UI 느낌은 줄인다.

페이지 전체가 여러 개의 색상 카드로 나뉘는 디자인을 지양하고, 다음 요소를 중심으로 구성한다.

- 충분한 여백
- 얇은 divider line
- 명확한 grid
- 프로필 이미지
- 프로젝트 이미지
- 작은 section numbering
- 중간 크기의 타이포그래피
- 절제된 accent color

---

## 3. 가장 중요한 디자인 원칙

### 대형 영문 타이포그래피를 사용하지 않는다.

현재 또는 이전 시안처럼 다음 문장이 화면 절반 이상을 차지하면 안 된다.

```text
I TURN
PROBLEMS
INTO
STRUCTURES
```

또는

```text
Problems into
Structures,
Ideas into
Results
```

와 같은 초대형 타이포 디자인은 사용하지 않는다.

Hero에서 가장 큰 글씨도 데스크톱 기준 약 `42~52px` 정도를 권장한다.

텍스트 크기가 아니라 **여백, 정렬, 사진, 정보구조**를 통해 시선을 유도한다.

---

## 4. 전체 페이지 구조

메인페이지는 다음 순서로 구성한다.

```text
HEADER

01 INTRO / HERO

02 HOW I WORK

03 SELECTED WORK

04 ARCHIVE / THINKING

CONTACT / FOOTER
```

섹션을 필요 이상으로 추가하지 않는다.

---

## 5. HEADER

현재 메뉴 구조는 유지한다.

```text
HY / PORTFOLIO

ABOUT
PROJECTS
ARCHIVE
EXPERIENCE
CONTACT
```

Header 디자인은 최대한 단순하게 한다.

배경색 카드 형태는 사용하지 않는다.

추천 구조:

```text
HY / PORTFOLIO                     ABOUT PROJECTS ARCHIVE EXPERIENCE CONTACT
────────────────────────────────────────────────────────────────────────────
```

Sticky header는 선택사항이다.

과한 blur, glassmorphism은 사용하지 않는다.

---

## 6. HERO / INTRO

Hero는 **텍스트 55~60% + 프로필 이미지 40~45%** 정도의 2-column layout으로 구성한다.

왼쪽 영역 예시:

```text
01 / INTRO

HYEYOUNG CHOI

문제를 발견하고,
복잡한 정보를 구조화해
실행 가능한 결과로 연결합니다.

기술보다 먼저 문제를 보고,
필요한 정보와 데이터를 정리하며
결과까지 연결하는 과정을 중요하게 생각합니다.

PLANNING · DATA · AI · DOCUMENTATION

VIEW PROJECTS ↗
```

`HYEYOUNG CHOI` 자체는 과도하게 크게 만들지 않는다.

핵심 한글 문장이 Hero의 주 메시지가 되어도 좋다.

영문 슬로건은 반드시 사용할 필요 없다.

사용한다면 작은 보조문장으로만 사용한다.

예:

```text
Problem → Structure → Result
```

---

## 7. PROFILE IMAGE

현재 `profile_image()` Flask route를 그대로 활용한다.

프로필 이미지를 새로운 카드 안에 지나치게 장식하지 않는다.

추천 형태:

```text
┌─────────────────────────┐
│                         │
│      PROFILE IMAGE      │
│                         │
│                         │
└─────────────────────────┘

HYEYOUNG CHOI
Planning / Data / AI
```

사진이 Hero의 중요한 visual anchor 역할을 하도록 한다.

Shadow는 없거나 매우 약하게 한다.

Border radius도 지나치게 둥글게 하지 않는다.

---

## 8. HOW I WORK

기존 `Problem → Structure → Result` 개념은 유지한다.

다만 카드 3개를 각각 다른 색으로 만들지 않는다.

한 줄 또는 3-column layout을 사용한다.

예:

```text
02 / HOW I WORK
────────────────────────────────────────────

01
PROBLEM

무엇을 해결해야 하는가?


02
STRUCTURE

복잡한 정보를 어떤 기준으로 정리할 것인가?


03
RESULT

어떤 실행 가능한 결과로 연결할 것인가?
```

Desktop에서는 3-column.

Mobile에서는 vertical stack.

필요하면 화살표를 매우 작게 사용할 수 있다.

아이콘은 없어도 된다.

---

## 9. SELECTED WORK

이 영역은 메인페이지에서 가장 중요한 섹션 중 하나다.

현재 Flask에서 전달하는 `projects` 데이터를 그대로 사용한다.

하드코딩보다 기존 Jinja loop를 유지한다.

메인에서는 최대 3개 프로젝트만 보여준다.

예:

```jinja
{% for project in projects[:3] %}
```

추천 UI는 카드형보다 **editorial list 또는 project showcase**다.

예:

```text
03 / SELECTED WORK
                                    VIEW ALL PROJECTS ↗

01
Mood Code

공간과 무드 기반 추천 서비스

Planning · Data · Flask                               ↗

────────────────────────────────────────────────────────


02
CaloDetect

음식 이미지 기반 AI 분석 서비스

AI · Computer Vision · Data                           ↗
```

Mood Code처럼 실제 thumbnail이 존재하는 프로젝트는 이미지를 적극적으로 활용할 수 있다.

단, 모든 프로젝트를 거대한 컬러 카드로 만들지 않는다.

Project title → description → stack → link의 정보 위계가 명확해야 한다.

---

## 10. ARCHIVE

현재 Archive는 포트폴리오의 보조 콘텐츠다.

프로젝트보다 더 시각적으로 강하게 만들지 않는다.

추천:

```text
04 / THE THINKING BEHIND THE WORK

배우고 기록하고,
실제 문제에 적용한 생각들.


AI 프로젝트 검증 체크리스트                    ↗
─────────────────────────────────────────────

데이터 구조를 먼저 설계해야 하는 이유           ↗
─────────────────────────────────────────────

VIEW ARCHIVE ↗
```

현재 전달받는 `archives` 데이터를 활용한다.

메인에서는 2~3개만 보여준다.

---

## 11. CONTACT / FOOTER

현재의 거대한 검정 Footer는 축소한다.

페이지 전체 분위기를 깨지 않도록 Hero와 동일한 neutral background를 사용할 수 있다.

예:

```text
────────────────────────────────────────────

LET'S CONNECT

Make something meaningful together.

CONTACT ↗

© 2026 HYEYOUNG CHOI
```

검정 배경을 유지한다면 높이는 현재보다 상당히 줄인다.

큰 타원형 그래픽이나 의미 없는 장식 요소는 제거한다.

---

## 12. 컬러 시스템

컬러를 지나치게 많이 사용하지 않는다.

권장 팔레트:

```css
--background: #F6F3EE;
--surface: #FBF9F6;
--text: #171614;
--muted: #77736D;
--line: #D8D3CC;
--accent: #78856E;
```

현재 사용 중인 핑크 / 코랄 / 민트가 동시에 강하게 등장하지 않도록 한다.

Accent color는 **전체 페이지의 약 5~10% 수준**으로 제한한다.

Project thumbnail과 Profile image 자체가 페이지의 주요 색상 역할을 하도록 한다.

---

## 13. Typography

한글과 영문의 가독성이 가장 중요하다.

현재 font를 반드시 변경할 필요는 없지만, 가능하면 다음 느낌을 유지한다.

```text
English:
DM Sans / Inter / Manrope

Korean:
Pretendard / Noto Sans KR
```

타이포그래피 위계:

```text
Section Label
11~13px

Body
15~17px

Project Title
24~32px

Hero Main Message
42~52px
```

**70~100px 이상의 대형 글씨는 사용하지 않는다.**

---

## 14. Layout

전체 콘텐츠의 최대 width는 대략 다음 범위에서 결정한다.

```css
max-width: 1200px ~ 1320px;
```

Desktop에서 좌우 여백을 충분히 준다.

Section 사이 vertical spacing도 충분히 확보한다.

권장:

```css
section {
    padding-top: 96px;
    padding-bottom: 96px;
}
```

Mobile에서는 적절하게 축소한다.

---

## 15. Responsive

반드시 반응형으로 구현한다.

최소 기준:

```text
Desktop
Tablet
Mobile
```

Mobile에서는 Hero가 다음 순서로 변경된다.

```text
INTRO TEXT
↓
PROFILE IMAGE
↓
HOW I WORK
↓
PROJECTS
↓
ARCHIVE
```

가로 overflow가 발생하지 않아야 한다.

메뉴도 기존 mobile menu가 있다면 유지한다.

---

## 16. 반드시 유지해야 하는 기능

디자인 변경 과정에서 다음 기능을 깨뜨리지 않는다.

```text
Flask routing

profile_image route

project detail links

projects Jinja rendering

archive / record links

navigation links

mobile menu

contact email link
```

백엔드 기능이나 DB 구조 변경은 필요하지 않다.

---

## 17. 이번 작업에서 하지 말 것

이번 작업에서는 다음을 구현하지 않는다.

```text
AI chatbot
Ask HY
RAG
감정평가 업무 상세 페이지
Experience 상세 개편
Project DB schema 변경
Archive DB schema 변경
Admin page redesign
새로운 프로젝트 추가
Three.js
3D animation
복잡한 scroll animation
과도한 hover animation
```

메인 UI 개선에만 집중한다.

---

## 18. 구현 방식

기존 Flask/Jinja 구조를 최대한 유지한다.

필요하면 다음 파일 위주로 수정한다.

```text
templates/home-reference.html
templates/base.html
static/css/style.css
static/js/main.js
```

JavaScript는 필요한 경우에만 사용한다.

CSS로 해결 가능한 디자인은 CSS로 구현한다.

새로운 frontend framework를 도입하지 않는다.

Tailwind, React, Vue 등을 추가하지 않는다.

---

## 19. 완료 기준

작업 완료 후 다음 항목을 점검한다.

```text
1. 첫 화면에서 대형 영문 타이포가 사라졌는가?

2. 프로필 사진과 핵심 소개가 가장 먼저 자연스럽게 보이는가?

3. 카드와 배경색 사용량이 기존보다 현저히 줄었는가?

4. Problem → Structure → Result가 명확하게 보이는가?

5. Selected Projects가 메인 콘텐츠로 충분히 강조되는가?

6. Archive는 프로젝트보다 낮은 시각적 위계를 가지는가?

7. Desktop / Tablet / Mobile에서 레이아웃이 정상인가?

8. 기존 Flask/Jinja 기능이 모두 유지되는가?

9. 불필요한 decorative element가 없는가?

10. 전체적으로 '깔끔하고 차분한 에디토리얼 포트폴리오'로 보이는가?
```

---

## Codex 실행 지시

먼저 현재 프로젝트 구조와 `home-reference.html`, `base.html`, `style.css`, `main.js`를 분석한 뒤 수정 계획을 짧게 제시하세요.

그 후 **메인페이지 UI만 수정하세요.**

기존 Flask 라우팅과 Jinja 데이터 바인딩은 유지하고, 백엔드와 DB 구조는 변경하지 마세요.

특히 초대형 영문 헤드라인을 사용하지 말고, **프로필 이미지·여백·grid·프로젝트 콘텐츠**를 중심으로 시각적 위계를 만드세요.

작업 완료 후 수정한 파일과 변경 내용을 요약하고, 반응형 및 기존 링크 동작 여부를 점검하세요.
