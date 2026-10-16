"""개발용 로컬 Storage 엔드포인트. Supabase Storage를 쓰면 등록되지 않는다.

Signed URL처럼 HMAC 서명과 만료 시각을 검사한다. GET은 HTTP Range 요청을 지원한다(Starlette FileResponse).
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.core.config import settings
from app.services.storage_service import LocalStorage, get_storage

router = APIRouter(prefix="/api/local-storage", tags=["local-storage"])


def _storage() -> LocalStorage:
    s = get_storage()
    assert isinstance(s, LocalStorage)
    return s


@router.put("/upload")
async def upload(request: Request, path: str, exp: int, sig: str):
    if not LocalStorage.verify(path, exp, "upload", sig):
        raise HTTPException(403, "invalid signature")
    dest = _storage().local_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with dest.open("wb") as f:
        async for chunk in request.stream():
            written += len(chunk)
            if written > settings.max_upload_bytes + 1024 * 1024:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "too large")
            f.write(chunk)
    return {"ok": True, "size": written}


@router.get("/object")
def get_object(path: str, exp: int, sig: str, download: str | None = None):
    if not LocalStorage.verify(path, exp, "object", sig):
        raise HTTPException(403, "invalid signature")
    p = _storage().local_path(path)
    if not p.is_file():
        raise HTTPException(404)
    media = "audio/mpeg" if p.suffix == ".mp3" else "application/json" if p.suffix == ".json" else None
    if download:
        return FileResponse(p, media_type=media, filename=download)  # Content-Disposition: attachment
    return FileResponse(p, media_type=media)
