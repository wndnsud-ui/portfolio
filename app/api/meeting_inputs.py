import unicodedata
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_user
from app.api.workflow import editable_meeting, record
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.user import User
from app.models.workflow import TranscriptionJob, TranscriptChunk
from app.services.integration_context import credentials
from app.services.transcription_service import transcription_service
from app.services.workflow_service import activity

router = APIRouter(tags=["Meeting inputs"])


class TextInput(BaseModel):
    text: str = Field(min_length=1, max_length=2000000)


def normalize(text):
    result = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not result or "\x00" in result:
        raise AppError("INVALID_TEXT", "A nonempty text transcript is required.", 400)
    return result


def store_text(db, meeting, text, input_type, user):
    if meeting.report_status == "TRANSCRIBING":
        raise AppError("INPUT_BUSY", "Transcription is already running.", 409)
    if meeting.transcript:
        meeting.transcript.content = text
    else:
        meeting.transcript = Transcript(content=text)
    meeting.input_type = input_type
    meeting.report_status = "DRAFT"
    meeting.summary = None
    meeting.discussion = None
    meeting.candidates = {}
    meeting.undecided_topics = []
    job = TranscriptionJob(meeting_id=meeting.id, user_id=user.id, status="TRANSCRIBED", progress=100)
    db.add(job)
    activity(db, meeting.project_id, user.id, "transcription_completed", "meeting", meeting.id)
    db.commit()
    return record(job)


@router.post("/meetings/{meeting_id}/input/text")
def paste_text(meeting_id: int, payload: TextInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return store_text(db, editable_meeting(db, meeting_id, user), normalize(payload.text), "text_paste", user)


async def transcribe_job(bind, job_id, filename, data, content_type, personal):
    token = credentials.set(personal)
    factory = sessionmaker(bind=bind)
    try:
        with factory() as db:
            job = db.get(TranscriptionJob, job_id)
            job.status = "TRANSCRIBING"
            db.commit()
        def on_chunk(index, count, text):
            with factory() as db:
                job = db.get(TranscriptionJob, job_id)
                db.add(TranscriptChunk(job_id=job_id, sequence=index, content=text))
                db.flush()
                chunks = db.query(TranscriptChunk).filter_by(job_id=job_id).order_by(TranscriptChunk.sequence).all()
                meeting = db.get(Meeting, job.meeting_id)
                if meeting.transcript:
                    meeting.transcript.content = "\n\n".join(c.content for c in chunks)
                else:
                    meeting.transcript = Transcript(content="\n\n".join(c.content for c in chunks))
                job.progress = round(len(chunks) / count * 100)
                db.commit()
        text = await transcription_service.transcribe(filename, data, content_type, on_chunk=on_chunk)
        with factory() as db:
            job = db.get(TranscriptionJob, job_id)
            meeting = db.get(Meeting, job.meeting_id)
            if meeting.transcript:
                meeting.transcript.content = text
            else:
                meeting.transcript = Transcript(content=text)
            job.status, job.progress = "TRANSCRIBED", 100
            meeting.report_status = "DRAFT"
            activity(db, meeting.project_id, job.user_id, "transcription_completed", "meeting", meeting.id)
            db.commit()
    except Exception:
        with factory() as db:
            job = db.get(TranscriptionJob, job_id)
            if job:
                job.status, job.error = "FAILED", "전사에 실패했습니다. 설정과 파일을 확인한 뒤 다시 업로드해 주세요."
                meeting = db.get(Meeting, job.meeting_id)
                if meeting:
                    meeting.report_status = "DRAFT"
                db.commit()
    finally:
        credentials.reset(token)


@router.post("/meetings/{meeting_id}/input/file", status_code=202)
async def upload_input(meeting_id: int, background: BackgroundTasks, file: UploadFile = File(...), recording: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = editable_meeting(db, meeting_id, user)
    if meeting.report_status == "TRANSCRIBING":
        raise AppError("INPUT_BUSY", "Transcription is already running.", 409)
    extension = Path(file.filename or "").suffix.lower()
    if extension in {".txt", ".md"}:
        data = await file.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise AppError("FILE_SIZE", "Text files are limited to 2 MB.", 413)
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = data.decode("cp949")
            except UnicodeDecodeError:
                raise AppError("TEXT_ENCODING", "Use UTF-8 or Korean CP949 text.", 400)
        return store_text(db, meeting, normalize(text), "text_file", user)
    if extension not in transcription_service.supported_extensions:
        raise AppError("UNSUPPORTED_FILE", "Upload audio, TXT or MD.", 415)
    data = await file.read(transcription_service.max_file_size + 1)
    if not data or len(data) > transcription_service.max_file_size:
        raise AppError("FILE_SIZE", "Audio must be between 1 byte and 250 MB.", 413)
    if not (credentials.get() or {}).get("openai_api_key"):
        raise AppError("OPENAI_API_KEY_MISSING", "Configure your OpenAI API key first.", 503)
    meeting.input_type = "recording" if recording else "audio"
    meeting.report_status = "TRANSCRIBING"
    meeting.candidates = {}
    meeting.summary = None
    meeting.discussion = None
    meeting.undecided_topics = []
    if meeting.transcript:
        meeting.transcript.content = ""
    job = TranscriptionJob(meeting_id=meeting_id, user_id=user.id)
    db.add(job)
    db.commit()
    background.add_task(transcribe_job, db.get_bind(), job.id, file.filename, data, file.content_type, credentials.get())
    return record(job)


@router.get("/meetings/{meeting_id}/input/jobs")
def jobs(meeting_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.api.meetings import get_meeting_or_404
    get_meeting_or_404(db, meeting_id, user)
    return [record(j) for j in db.query(TranscriptionJob).filter_by(meeting_id=meeting_id).order_by(TranscriptionJob.id.desc()).all()]
