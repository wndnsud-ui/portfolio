"""Create private, clearly labelled examples once during account creation."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.models.project import Project
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.decision import Decision
from app.models.action_item import ActionItem
from app.models.workflow import FinalResult, TaskProgress

def create_examples(db, user):
    db.flush()
    if db.query(Project).filter_by(user_id=user.id, is_example=True).first():
        return
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    project = Project(user_id=user.id, workspace_id=None, is_example=True,
        name="[예시] 처음 시작하기", description="가상 데이터로 사용 흐름을 살펴보세요. 개인 업무를 기록하고, 팀 관리에서 팀을 만든 뒤 팀원을 초대하고 업무를 배정할 수 있습니다.")
    db.add(project)
    db.flush()
    meeting = Meeting(project_id=project.id, user_id=user.id, recorder_id=user.id,
        title="[예시] 첫 회의와 결정 정리", meeting_date=today, participants=[user.nickname or "나"],
        report_status="PUBLISHED", analysis_status="confirmed", summary="회의 내용을 기록하고 결정사항과 실행 업무로 연결하는 사용 예시입니다.",
        discussion="개인 업무는 개인 공간에서 관리합니다. 협업은 팀 만들기 → 팀원 초대 → 프로젝트 참여 → 업무 배정 순서로 진행합니다.",
        undecided_topics=["[예시] 다음 회의 일정"])
    meeting.transcript = Transcript(content="# 첫 회의 (예시)\n\n실제 회의가 아닌 사용 안내용 데이터입니다.\n\n## 사용 순서\n1. 프로젝트를 열어 회의와 결정사항을 확인합니다.\n2. 업무를 열어 수락·시작·진행 기록·결과 제출을 살펴봅니다.\n3. 상단에서 팀을 만들고 팀 관리 메뉴에서 팀원을 초대합니다.\n4. 팀원을 프로젝트에 추가한 뒤 업무를 배정합니다.\n\n## 결정\n이번 주에는 첫 프로젝트와 업무를 등록해 봅니다.")
    db.add(meeting)
    db.flush()
    db.add(Decision(project_id=project.id, meeting_id=meeting.id, user_id=user.id,
        topic="[예시] 첫 프로젝트 시작", value="개인 업무를 먼저 등록하고 필요할 때 팀을 만들어 협업합니다.", status="confirmed"))
    for i, (title, state, status, percent) in enumerate([
        ("업무를 수락하고 시작해 보기", "ASSIGNED", "todo", 0),
        ("진행 단계를 선택하고 내용 기록하기", "IN_PROGRESS", "in_progress", 50),
        ("완료 결과 확인하기", "APPROVED", "done", 100),
    ]):
        task = ActionItem(project_id=project.id, meeting_id=meeting.id, user_id=user.id,
            assigned_by=user.id, assignee_id=user.id, assignee=user.nickname or user.email,
            task=f"[예시] {title}", description="사용 안내용 가상 업무입니다. 실제 업무는 새로 등록하세요.\n\n진행 상황은 시작 0% · 중간 50% · 마무리 100%를 선택하고 내용을 저장합니다. 결과를 제출한 뒤 완료를 승인할 수 있습니다.",
            workflow_status=state, status=status, priority="medium", due_date=today+timedelta(days=i+1),
            progress_percent=percent, progress_updated_at=datetime.utcnow() if percent else None,
            progress_content="[예시] 진행 기록을 남겼습니다." if percent else None,
            completed_at=datetime.utcnow() if status=="done" else None)
        db.add(task)
        db.flush()
        if percent:
            db.add(TaskProgress(task_id=task.id, user_id=user.id, content="[예시] 화면을 확인하고 진행 내용을 정리했습니다."))
        if status == "done":
            db.add(FinalResult(task_id=task.id, project_id=project.id, approved_by=user.id, assignee_id=user.id,
                title=task.task, content="# 완료 결과 (예시)\n\n업무 결과는 설명과 파일을 제출한 뒤 승인하여 보관합니다."))
