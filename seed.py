"""빈 DB에만 넣는 기본 데이터. 운영 DB에는 다시 돌리지 않는다 (`flask seed`가 데이터가 있으면 건너뜀)."""
from models import Archive, Experience, Profile, Project, Skill, db

PROJECTS = [
    dict(title="모모슬의 느린책방", slug="slow-bookshop", sort_order=1, subtitle="느린 독서 경험을 위한 온라인 책방",
         description="책방의 분위기에서 추천 이야기와 도서를 발견하고 검색 또는 ISBN으로 실제 책 정보를 확인하는 흐름을 설계했습니다.",
         problem="어떻게 천천히 책을 즐기게 할까?", role="독서 경험 기획, 콘텐츠 순서 설계, 도서 API 구현",
         process="둘러보기 → 추천 이야기·도서 발견 → 검색·ISBN 확인", result="도서 API 연결 구현",
         tech_stack="Web / Book API / UX", demo_url="https://wndnsud-ui.github.io/kakao_books/",
         github_url="https://github.com/wndnsud-ui/kakao_books"),
    dict(title="Mood Code", slug="mood-code", sort_order=2, subtitle="공간과 무드 기반 인테리어 상품 추천 서비스",
         description="상품 코드와 공간 이미지를 연결해 더 나은 선택을 돕는 서비스입니다.",
         problem="사용자가 여러 상품을 개별적으로 검색하지 않고도 자신의 공간과 분위기에 맞는 조합을 발견하기 어려웠습니다.",
         role="서비스 기획, 데이터 구조 설계, 프로젝트 구조, 발표와 문서화",
         process="Problem 정의 → 데이터 구조 → 매핑 검증 → 서비스 구현 → 문서화",
         result="추천 로직의 기준을 명확히 하고 재사용 가능한 데이터 구조를 만들었습니다.",
         tech_stack="Python / Flask / SQLite / Data / UX", cover_image="/static/images/moodcode.png",
         demo_url="https://mood-code-latest.onrender.com/"),
    dict(title="CaloDetect", slug="calodetect", sort_order=3, subtitle="음식 이미지 기반 객체 탐지와 칼로리 영양 분석 서비스",
         description="음식 사진에서 객체를 탐지하고 영양 정보로 연결하는 AI 서비스입니다.",
         problem="식단을 기록하는 과정이 번거롭고 음식별 영양 정보를 직접 입력해야 했습니다.",
         role="프로젝트 구조, 데이터셋 실험 정리, 결과 검증, 발표 구조 설계",
         process="Dataset Analysis → Model Training → Validation → Service Integration → Documentation",
         result="AI 모델 결과를 사용자가 이해할 수 있는 서비스 흐름으로 연결했습니다.",
         tech_stack="Python / YOLO / Computer Vision / Data / AI", demo_url="https://calo-detect.vercel.app/",
         github_url="https://github.com/wndnsud-ui/CaloDetect"),
]


def seed_database():
    """데이터가 하나라도 있으면 아무것도 하지 않고 False를 돌려준다."""
    if Profile.query.first() or Project.query.first() or Archive.query.first():
        return False
    db.session.add(Profile(name="최혜영", headline="I turn problems into structure.",
                           intro="문제를 발견하고, 구조를 만들고, 결과까지 연결합니다.", email=""))
    for data in PROJECTS:
        db.session.add(Project(status="published", design={"layout": "magazine"}, **data))
    db.session.add_all([
        Experience(company="AI / SW Training", position="기업맞춤형 AI+X 융복합 인재 양성 과정", start_date="2026.06.05",
                   end_date="2026.11.04", description="824시간 / 103일 · 수행 프로젝트 CaloDetect",
                   achievement="실험과 결과를 문서화하고 팀 작업의 기준을 정리했습니다.", sort_order=1),
        Experience(company="Projects", position="Product & Data Builder", start_date="2026", end_date="현재",
                   description="작은 문제를 실제로 작동하는 서비스 구조로 전환하고 있습니다.",
                   achievement="Mood Code, CaloDetect 프로젝트를 기획·구현했습니다.", sort_order=2),
    ])
    for category, names in {"DATA": ["Python", "Pandas", "SQL"], "AI": ["Machine Learning", "YOLO", "Computer Vision"],
                            "DEVELOPMENT": ["Flask", "HTML / CSS", "Git / GitHub"],
                            "WORK": ["Planning", "Documentation", "Process Design", "Data Validation"]}.items():
        for index, name in enumerate(names):
            db.session.add(Skill(category=category, name=name, level=88 - index * 5, sort_order=index))
    db.session.add_all([
        Archive(title="데이터 구조를 먼저 설계해야 하는 이유", slug="data-structure-first", category="DATA", content_type="notes",
                status="published", summary="결과가 흔들릴 때 데이터 관계부터 점검한 기록입니다.",
                blocks=[{"type": "paragraph", "text": "데이터를 잘 모으는 것만큼 어떤 기준으로 연결하고 검증할지 정하는 일이 중요합니다."}]),
        Archive(title="AI 프로젝트 검증 체크리스트", slug="ai-validation-checklist", category="AI / ML", content_type="notes",
                status="published", summary="모델 결과를 서비스 결과로 바꾸기 위한 질문들입니다.",
                blocks=[{"type": "paragraph", "text": "정확도뿐 아니라 입력, 예외, 사용자에게 전달되는 결과까지 확인합니다."}]),
    ])
    db.session.commit()
    return True
