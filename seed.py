from models import db, Profile, Project, Experience, Skill, Archive, Book

def seed_books():
    """Optional local sample books. Kept separate so real Notion exports can replace it."""
    if Book.query.first():
        return 0
    db.session.add_all([
        Book(title="기획의 정석", author="박신영", genre="Product", record_type="book", status="completed", summary="문제를 정의하고 구조화하는 기획의 기본을 정리한 책."),
        Book(title="인스파이어드", author="Marty Cagan", genre="Product", record_type="book", status="reading", summary="제품팀이 고객 문제를 발견하고 검증하는 방법을 기록한다."),
    ])
    db.session.commit()
    return 2

def seed_database():
    if Profile.query.first():
        return
    db.session.add(Profile(name="최혜영", headline="I turn problems into structure.", intro="문제를 발견하고, 구조를 만들고, 결과까지 연결합니다.", email="hello@example.com"))
    db.session.add_all([
        Project(title="Mood Code", subtitle="공간과 무드 기반 인테리어 상품 추천 서비스", description="상품 코드와 공간 이미지를 연결해 더 나은 선택을 돕는 서비스입니다.", problem="사용자가 여러 상품을 개별적으로 검색하지 않고도 자신의 공간과 분위기에 맞는 조합을 발견하기 어려웠습니다.", role="서비스 기획, 데이터 구조 설계, 프로젝트 구조, 발표와 문서화", process="Problem 정의 → 데이터 구조 → 매핑 검증 → 서비스 구현 → 문서화", action="공간·무드·상품 간 관계를 데이터 모델로 정리하고 추천 흐름을 설계했습니다.", trouble="카테고리 코드가 중복되고 장면과 상품 매핑이 어긋나는 문제가 있었습니다.", solution="Unique Key와 Scene-Product Mapping 검증 규칙을 도입했습니다.", result="추천 로직의 기준을 명확히 하고 재사용 가능한 데이터 구조를 만들었습니다.", insight="좋은 추천은 단순한 데이터 나열이 아니라 관계의 정확성에서 시작됩니다.", tech_stack="Python / Flask / SQLite / Data / UX"),
        Project(title="CaloDetect", subtitle="음식 이미지 기반 객체 탐지와 칼로리 영양 분석 서비스", description="음식 사진에서 객체를 탐지하고 영양 정보로 연결하는 AI 서비스입니다.", problem="식단을 기록하는 과정이 번거롭고 음식별 영양 정보를 직접 입력해야 했습니다.", role="프로젝트 구조, 데이터셋 실험 정리, 결과 검증, 발표 구조 설계", process="Dataset Analysis → Model Training → Validation → Service Integration → Documentation", action="탐지 결과와 영양 데이터의 연결 규칙을 정리하고 검증 화면을 구성했습니다.", trouble="모델 성능만으로는 실제 사용 가능한 결과를 보장하기 어려웠습니다.", solution="실험 기록, 검증 기준, 데이터 연결 상태를 함께 관리했습니다.", result="AI 모델 결과를 사용자가 이해할 수 있는 서비스 흐름으로 연결했습니다.", insight="AI 프로젝트에서는 모델 성능과 함께 데이터 구조·검증·작업 과정의 관리가 중요합니다.", tech_stack="Python / YOLO / Computer Vision / Data / AI")
    ])
    db.session.add_all([
        Experience(company="AI / SW Training", position="Data & AI Project Trainee", start_date="2024", end_date="2025", description="데이터와 AI 프로젝트를 수행하며 문제 정의부터 검증까지 경험했습니다.", achievement="실험과 결과를 문서화하고 팀 작업의 기준을 정리했습니다.", sort_order=1),
        Experience(company="Projects", position="Product & Data Builder", start_date="2024", end_date="현재", description="작은 문제를 실제로 작동하는 서비스 구조로 전환하고 있습니다.", achievement="Mood Code, CaloDetect 프로젝트를 기획·구현했습니다.", sort_order=2),
        Experience(company="Current Learning", position="Continuous Learner", start_date="현재", end_date="", description="Flask, SQLAlchemy, 데이터 검증과 AI 서비스화를 학습합니다.", achievement="배운 내용을 archive로 남기고 다시 사용할 수 있는 지식으로 구조화합니다.", sort_order=3),
    ])
    for category, names in {"DATA": ["Python", "Pandas", "SQL"], "AI": ["Machine Learning", "YOLO", "Computer Vision"], "DEVELOPMENT": ["Flask", "HTML / CSS", "Git / GitHub"], "WORK": ["Planning", "Documentation", "Process Design", "Data Validation"]}.items():
        for index, name in enumerate(names):
            db.session.add(Skill(category=category, name=name, level=88 - index * 5, sort_order=index))
    db.session.add_all([
        Archive(title="데이터 구조를 먼저 설계해야 하는 이유", category="DATA", summary="결과가 흔들릴 때 데이터 관계부터 점검한 기록입니다.", content="데이터를 잘 모으는 것만큼 어떤 기준으로 연결하고 검증할지 정하는 일이 중요합니다."),
        Archive(title="AI 프로젝트 검증 체크리스트", category="AI / ML", summary="모델 결과를 서비스 결과로 바꾸기 위한 질문들입니다.", content="정확도뿐 아니라 입력, 예외, 사용자에게 전달되는 결과까지 확인합니다."),
    ])
    db.session.commit()
