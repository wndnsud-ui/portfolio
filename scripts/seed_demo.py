from datetime import UTC, date, datetime, timedelta

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.action_item import ActionItem
from app.models.decision import Decision
from app.models.enums import ActionStatus, AnalysisStatus, DecisionStatus, Priority
from app.models.meeting import Meeting
from app.models.project import Project
from app.models.transcript import Transcript
from app.services.risk_service import risk_service


DEMO_PROJECT = "DecisionFlow MVP"


def make_meeting(
    project: Project,
    title: str,
    days_ago: int,
    participants: list[str],
    summary: str,
    discussion: str,
    transcript: str,
    undecided_topics: list[str] | None = None,
) -> Meeting:
    meeting = Meeting(
        project=project,
        title=title,
        meeting_date=date.today() - timedelta(days=days_ago),
        participants=participants,
        summary=summary,
        discussion=discussion,
        undecided_topics=undecided_topics or [],
        analysis_status=AnalysisStatus.confirmed,
    )
    meeting.transcript = Transcript(content=transcript)
    return meeting


def make_action(
    project: Project,
    meeting: Meeting,
    task: str,
    assignee: str,
    due_in_days: int,
    priority: Priority,
    status: ActionStatus = ActionStatus.todo,
    stale_days: int = 0,
) -> ActionItem:
    now = datetime.now(UTC).replace(tzinfo=None)
    item = ActionItem(
        project=project,
        meeting=meeting,
        task=task,
        assignee=assignee,
        due_date=date.today() + timedelta(days=due_in_days),
        priority=priority,
        status=status,
        status_changed_at=now - timedelta(days=stale_days),
        completed_at=now if status == ActionStatus.done else None,
    )
    item.risk_score, item.risk_level = risk_service.score(item)
    return item


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Project).filter(Project.name == DEMO_PROJECT).first():
            print("Demo data already exists.")
            return

        decisionflow = Project(
            name=DEMO_PROJECT,
            description="회의 기록부터 결정사항과 실행 업무까지 연결하는 협업 서비스 MVP",
        )
        website = Project(
            name="2026 브랜드 웹사이트",
            description="신규 브랜드 메시지와 제품 소개 페이지 개편 프로젝트",
        )
        operations = Project(
            name="고객 운영 개선",
            description="반복 문의를 줄이고 고객 대응 시간을 단축하기 위한 운영 개선",
        )
        db.add_all([decisionflow, website, operations])

        kickoff = make_meeting(
            decisionflow,
            "MVP 킥오프 및 범위 확정",
            6,
            ["혜영", "민수", "지우"],
            "DecisionFlow의 1차 출시 범위를 프로젝트, 회의, 결정사항, Action Item 관리로 확정했다.",
            "음성 전사는 파일 업로드 방식으로 시작하고 실시간 녹음은 후속 단계에서 검토한다. 로컬 개발은 SQLite를 사용하되 운영 환경은 PostgreSQL을 유지한다.",
            "혜영: 오늘은 MVP 범위를 확정하겠습니다. 핵심은 회의록을 저장하는 데서 끝나지 않고 실행 업무까지 연결하는 것입니다.\n민수: 프로젝트별 회의 이력과 결정사항 변경 기록이 필요합니다.\n지우: 음성 파일은 업로드 후 전사하는 방식으로 먼저 제공하면 좋겠습니다.\n혜영: 좋습니다. 대시보드, 프로젝트, 회의, Action Item, 결정사항을 1차 범위로 확정하겠습니다.",
            ["실시간 녹음 지원 시점", "다중 사용자 권한 모델"],
        )
        api_review = make_meeting(
            decisionflow,
            "API 및 데이터 모델 리뷰",
            3,
            ["혜영", "민수"],
            "핵심 엔터티 관계와 API 응답 구조를 검토하고 DecisionHistory 저장 방식을 확정했다.",
            "Meeting과 Transcript는 1:1, Project와 Meeting은 1:N으로 구성한다. 결정 내용이 변경되면 이전 값과 새 값을 별도 이력으로 저장한다.",
            "민수: Decision은 Meeting 본문에 묻히지 않도록 독립 엔터티로 두겠습니다.\n혜영: 변경 이력에는 이전 값, 새 값, 변경 회의를 남겨 주세요.\n민수: Action Item 위험도는 서비스 계층에서 계산하고 나중에 ML 구현으로 교체할 수 있게 하겠습니다.",
        )
        sprint = make_meeting(
            decisionflow,
            "1차 스프린트 진행 점검",
            1,
            ["혜영", "민수", "지우"],
            "CRUD 화면과 음성 전사 연결 상태를 점검하고 데모 준비 항목을 정리했다.",
            "회의 생성 오류를 수정하고 전체 CRUD 왕복 테스트를 추가한다. 데모에서는 위험도가 다른 Action Item을 함께 보여준다.",
            "혜영: 생성뿐 아니라 수정과 삭제가 화면에서 모두 가능해야 합니다.\n민수: 백엔드 CRUD 테스트를 자동화하고 회의 상세 응답 오류를 수정하겠습니다.\n지우: 음성 회의 버튼은 어느 화면에서도 찾기 쉽게 상단에 노출하겠습니다.",
        )
        website_review = make_meeting(
            website,
            "메인 화면 콘텐츠 리뷰",
            4,
            ["서연", "지우", "현우"],
            "메인 화면의 핵심 메시지를 간결하게 줄이고 실제 제품 화면을 우선 노출하기로 했다.",
            "첫 화면에서는 제품명과 핵심 효용을 명확히 보여주고 장식적 요소는 줄인다. 고객 사례는 다음 섹션에서 구체적인 수치와 함께 제시한다.",
            "서연: 첫 문장이 너무 추상적이라 제품이 무엇인지 바로 알기 어렵습니다.\n지우: 제품 화면을 크게 보여주고 설명은 두 문장으로 줄이겠습니다.\n현우: 고객 사례에는 도입 전후 시간을 비교하는 숫자를 넣겠습니다.",
        )
        support_review = make_meeting(
            operations,
            "주간 고객 문의 분석",
            2,
            ["유진", "태호"],
            "최근 문의의 42%가 계정 설정과 결제 내역 확인에 집중되어 있음을 확인했다.",
            "반복 문의 두 유형을 도움말 상단으로 이동하고 상담원이 사용하는 답변 템플릿을 통일한다.",
            "유진: 이번 주 문의 126건 중 계정 설정이 31건, 결제 확인이 22건입니다.\n태호: 도움말 탐색 경로가 길어서 상담으로 넘어오는 것 같습니다.\n유진: 상위 두 문서를 첫 화면으로 올리고 답변 템플릿도 이번 주에 정리하겠습니다.",
        )
        db.add_all([kickoff, api_review, sprint, website_review, support_review])

        db.add_all([
            Decision(project=decisionflow, meeting=kickoff, topic="백엔드 프레임워크", value="FastAPI와 SQLAlchemy 2를 사용한다.", status=DecisionStatus.confirmed),
            Decision(project=decisionflow, meeting=kickoff, topic="음성 전사 방식", value="완료된 음성 파일을 gpt-transcribe로 변환한다.", status=DecisionStatus.confirmed),
            Decision(project=decisionflow, meeting=api_review, topic="데이터 저장 원칙", value="운영 데이터의 Source of Truth는 PostgreSQL로 유지한다.", status=DecisionStatus.confirmed),
            Decision(project=website, meeting=website_review, topic="메인 화면 구성", value="제품 화면을 첫 화면의 핵심 시각 요소로 사용한다.", status=DecisionStatus.confirmed),
            Decision(project=operations, meeting=support_review, topic="도움말 우선순위", value="계정 설정과 결제 확인 문서를 도움말 상단에 배치한다.", status=DecisionStatus.draft),
        ])

        db.add_all([
            make_action(decisionflow, kickoff, "회의 생성 화면 CRUD 마무리", "민수", -2, Priority.high, stale_days=5),
            make_action(decisionflow, api_review, "DecisionHistory API 테스트 작성", "민수", 2, Priority.high, ActionStatus.in_progress, 1),
            make_action(decisionflow, sprint, "음성 전사 오류 메시지 문구 검토", "지우", 4, Priority.medium),
            make_action(decisionflow, kickoff, "Notion 연동 범위 문서화", "혜영", 8, Priority.low),
            make_action(decisionflow, api_review, "ERD 1차 검토 완료", "혜영", -1, Priority.medium, ActionStatus.done),
            make_action(website, website_review, "메인 카피 두 가지 안 작성", "서연", -1, Priority.high, stale_days=4),
            make_action(website, website_review, "제품 화면 캡처 최신화", "지우", 3, Priority.medium, ActionStatus.in_progress),
            make_action(operations, support_review, "계정 설정 도움말 개편", "태호", 1, Priority.high, ActionStatus.in_progress),
            make_action(operations, support_review, "상담 답변 템플릿 통합", "유진", 5, Priority.medium),
        ])

        db.commit()
        print("Demo data created: 3 projects, 5 meetings, 5 decisions, 9 action items.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
