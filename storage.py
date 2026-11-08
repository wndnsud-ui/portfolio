"""이미지·파일 저장.

SUPABASE_URL과 SUPABASE_SERVICE_KEY가 있으면 Supabase Storage 퍼블릭 버킷에 올리고 공개 URL을 돌려준다.
없으면(로컬 개발) static/uploads/에 저장한다. DB에는 항상 URL만 저장한다.
"""
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import current_app

IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}
FILE_TYPES = {**IMAGE_TYPES, "pdf": "application/pdf"}
_client = None


class UploadError(ValueError):
    pass


def _supabase():
    global _client
    cfg = current_app.config
    if not (cfg.get("SUPABASE_URL") and cfg.get("SUPABASE_SERVICE_KEY")):
        return None
    if _client is None:
        from supabase import create_client

        _client = create_client(cfg["SUPABASE_URL"], cfg["SUPABASE_SERVICE_KEY"])
    return _client


def _bucket():
    return current_app.config.get("SUPABASE_BUCKET", "media")


def _extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""


def put_bytes(data, extension, folder="posts"):
    """바이트를 저장하고 공개 URL을 돌려준다."""
    content_type = FILE_TYPES.get(extension, "application/octet-stream")
    key = f"{folder}/{datetime.utcnow():%Y/%m}/{uuid4().hex}.{extension}"
    client = _supabase()
    if client is not None:
        client.storage.from_(_bucket()).upload(key, data, {"content-type": content_type, "upsert": "false"})
        return client.storage.from_(_bucket()).get_public_url(key).rstrip("?")
    target = Path(current_app.static_folder) / "uploads" / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"/static/uploads/{key}"


def save_upload(file, allowed=IMAGE_TYPES, folder="posts"):
    if not file or not file.filename:
        return None
    extension = _extension(file.filename)
    if extension not in allowed:
        raise UploadError("PNG, JPG, GIF, WEBP 이미지" + (" 또는 PDF" if "pdf" in allowed else "") + "만 올릴 수 있습니다.")
    data = file.read()
    if not data:
        raise UploadError("빈 파일입니다.")
    return put_bytes(data, extension, folder)


def delete_url(url):
    """이 사이트가 올린 파일이면 지운다. 다른 주소는 건드리지 않는다."""
    if not url:
        return
    client = _supabase()
    marker = f"/storage/v1/object/public/{_bucket()}/"
    if client is not None and marker in url:
        client.storage.from_(_bucket()).remove([url.split(marker, 1)[1]])
        return
    prefix = "/static/uploads/"
    if url.startswith(prefix):
        root = (Path(current_app.static_folder) / "uploads").resolve()
        path = (root / url[len(prefix):]).resolve()
        if root in path.parents and path.exists():
            path.unlink()
