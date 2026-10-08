"""Add repeatable local collaboration examples to the shared test workspace."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.action_item import ActionItem
from app.models.decision import Decision
from app.models.meeting import Meeting
from app.models.project import Project
from app.models.transcript import Transcript
from app.models.user import User, UserSettings
from app.models.workspace import Workspace, WorkspaceMember, ProjectMember
from app.models.workflow import TaskProgress, TaskComment, TaskAttachment, FinalResult, TaskReview, Notification
from app.services.auth_service import hash_password
from app.services.risk_service import risk_service
from scripts.seed_test_accounts import seed as seed_accounts


def seed():
    if settings.app_env == "production":
        raise RuntimeError("This demo seed is for local development only.")
    seed_accounts()
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal() as db:
        leader = db.query(User).filter_by(email="leader@decisionflow.test").one()
        member = db.query(User).filter_by(email="member@decisionflow.test").one()
        workspace = db.query(Workspace).filter_by(name="권한 테스트 Workspace", created_by=leader.id).one()
        people = [member]
        for email, name in [("designer@decisionflow.test", "김디자인"), ("developer@decisionflow.test", "이개발")]:
            person = db.query(User).filter_by(email=email).first()
            if not person:
                person = User(email=email, nickname=name, password_hash=hash_password("MemberTest123!"))
                person.settings = UserSettings()
                db.add(person)
                db.flush()
            if not db.query(WorkspaceMember).filter_by(workspace_id=workspace.id, user_id=person.id).first():
                db.add(WorkspaceMember(workspace_id=workspace.id, user_id=person.id, role="MEMBER"))
            people.append(person)
        created = 0
        states = ["ASSIGNED", "ACCEPTED", "IN_PROGRESS", "BLOCKED", "READY_FOR_REVIEW", "CHANGES_REQUESTED", "APPROVED", "CANCELLED"]
        titles = ["요구사항 정리", "화면 구성안 작성", "핵심 기능 구현", "외부 연동 확인", "검수 체크리스트 제출", "피드백 반영", "최종 가이드 배포", "이전 시안 정리"]
        for index, name in enumerate(["[더미] 서비스 출시", "[더미] 브랜드 사이트 개편", "[더미] 고객 운영 개선"]):
            if db.query(Project).filter_by(workspace_id=workspace.id, name=name).first():
                continue
            project = Project(name=name, description="화면 확인용 가상 프로젝트입니다. 회의 검토, 업무 수행, 결과 승인 흐름을 체험하세요.", workspace_id=workspace.id, user_id=leader.id)
            db.add(project)
            db.flush()
            for person in [leader, *people]:
                db.add(ProjectMember(project_id=project.id, user_id=person.id))
            meetings = []
            for offset, report_status in enumerate(["MANAGER_REVIEW", "PUBLISHED"]):
                meeting = Meeting(project_id=project.id, user_id=leader.id, recorder_id=member.id,
                    title=f"{name} · {'주간 진행 점검' if offset == 0 else '킥오프 회의'}",
                    meeting_date=today-timedelta(days=offset*3), participants=[leader.nickname, *[p.nickname for p in people]],
                    report_status=report_status, analysis_status="confirmed",
                    summary="출시 범위와 담당 업무를 정리하고 결과물 제출 일정을 합의했습니다.",
                    discussion="팀원은 진행 상황을 기록하고 팀장은 제출된 결과물을 검토합니다.",
                    undecided_topics=["차기 릴리스 일정"])
                meeting.transcript = Transcript(content="## 회의록 (더미)\n\n팀장: 이번 주에는 핵심 화면을 완성합니다.\n\n팀원: 검수 체크리스트와 결과물을 제출하겠습니다.\n\n### 합의 사항\n- 업무별 담당자 지정\n- 제출 후 팀장 승인\n- 다음 주 사용자 피드백 검토")
                db.add(meeting)
                db.flush()
                meetings.append(meeting)
                db.add(Decision(project_id=project.id, meeting_id=meeting.id, user_id=leader.id,
                    topic=f"{name} · {'검수 기준' if offset == 0 else '출시 범위'}", value="핵심 화면과 사용 가이드를 우선 완성하고 팀장 승인 후 게시합니다.", status="draft" if offset == 0 else "confirmed"))
            for task_index, state in enumerate(states):
                # The primary test member gets every state; other members add workload variety.
                assignee = member if task_index < 6 else people[(index+task_index)%len(people)]
                status = "done" if state == "APPROVED" else "cancelled" if state == "CANCELLED" else "todo" if state in {"ASSIGNED", "ACCEPTED"} else "in_progress"
                percent = 100 if state in {"READY_FOR_REVIEW", "APPROVED"} else 60 if status == "in_progress" else 0
                task = ActionItem(project_id=project.id, meeting_id=meetings[1].id, user_id=leader.id,
                    task=f"{name} · {titles[task_index]}", description="화면 확인용 테스트 업무입니다. 진행 내용과 결과물을 기록하고 검토를 요청하세요.",
                    assignee_id=assignee.id, assignee=assignee.nickname, assigned_by=leader.id,
                    workflow_status=state, status=status, priority="high" if task_index%3 == 0 else "medium",
                    due_date=today+timedelta(days=task_index-3), progress_percent=percent,
                    progress_content="핵심 항목을 작성하고 체크리스트로 검증했습니다." if percent else None,
                    progress_updated_at=now if percent else None,
                    status_changed_at=now-timedelta(days=2), completed_at=now if state == "APPROVED" else None)
                task.risk_score, task.risk_level = risk_service.score(task)
                db.add(task)
                db.flush()
                if percent:
                    db.add(TaskProgress(task_id=task.id, user_id=assignee.id, content=f"진행률 {percent}%. 핵심 항목을 정리했습니다. 다음 단계는 최종 검수입니다."))
                    db.add(TaskComment(task_id=task.id, user_id=leader.id, content="수고하셨습니다. 체크리스트와 결과물을 함께 확인하겠습니다. (더미 댓글)"))
                if state in {"READY_FOR_REVIEW", "APPROVED"}:
                    content = f"# {task.task}\n\n화면 확인용 더미 결과물입니다.\n\n## 완료 내용\n- 핵심 화면 검수\n- 사용자 안내 작성\n- 모바일 표시 확인\n\n## 검수 결과\n모든 항목을 확인했습니다.\n"
                    key = f"demo-workflow-{task.id}.md"
                    root = Path(settings.attachment_dir)
                    root.mkdir(parents=True, exist_ok=True)
                    data = content.encode("utf-8")
                    (root/key).write_bytes(data)
                    db.add(TaskAttachment(task_id=task.id, uploaded_by=assignee.id, file_name="검수결과.md", storage_key=key, file_type="md", size=len(data)))
                    db.add(TaskReview(task_id=task.id, actor_id=assignee.id, action="submit-review", previous_status="IN_PROGRESS", new_status="READY_FOR_REVIEW", content=content))
                    if state == "APPROVED":
                        db.add(TaskReview(task_id=task.id, actor_id=leader.id, action="approve", previous_status="READY_FOR_REVIEW", new_status="APPROVED", content="검수 완료. 최종 결과로 게시합니다."))
                        db.add(FinalResult(task_id=task.id, project_id=project.id, approved_by=leader.id, assignee_id=assignee.id, title=task.task, content=content))
                if state in {"ASSIGNED", "READY_FOR_REVIEW"}:
                    db.add(Notification(user_id=assignee.id if state == "ASSIGNED" else leader.id,
                        type="task_assigned" if state == "ASSIGNED" else "task_review_requested",
                        title=task.task, message="화면 확인용 더미 알림입니다.", target_type="task", target_id=task.id))
            created += 1
        db.commit()
        print(f"Created {created} demo projects; {created*2} meetings; {created*8} tasks; {created*2} decisions; {created} final results; {created*2} attachments. workspace_id={workspace.id}")


if __name__ == "__main__":
    seed()
