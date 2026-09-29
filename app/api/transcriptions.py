from fastapi import APIRouter, File, UploadFile

from app.services.transcription_service import transcription_service

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


@router.post("")
async def create_transcription(file: UploadFile = File(...)) -> dict[str, str]:
    content = await file.read(transcription_service.max_file_size + 1)
    text = await transcription_service.transcribe(
        filename=file.filename or "audio",
        content=content,
        content_type=file.content_type,
    )
    return {"text": text}
