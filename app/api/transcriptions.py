from fastapi import APIRouter, Depends, File, UploadFile
from app.api.deps import get_current_user
from app.models.user import User

from app.services.transcription_service import transcription_service

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


@router.post("")
async def create_transcription(file: UploadFile = File(...), user: User = Depends(get_current_user)) -> dict[str, str]:
    content = await file.read(transcription_service.max_file_size + 1)
    text = await transcription_service.transcribe(
        filename=file.filename or "audio",
        content=content,
        content_type=file.content_type,
    )
    return {"text": text}
