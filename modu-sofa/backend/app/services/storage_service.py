"""Storage 추상화.

- SupabaseStorage: private 버킷, Signed Upload URL / Signed URL 사용 (운영)
- LocalStorage: 로컬 디스크 + HMAC 서명 URL (Supabase 키가 없을 때 개발용)

경로 규칙: {user_id}/{episode_id}/original.ext, playback.mp3, peaks.json, chunks/…, stt_raw/…
"""

import hashlib
import hmac
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx

from app.core.config import settings


@dataclass
class SignedUpload:
    url: str
    method: str
    headers: dict[str, str]


class StorageBackend:
    def create_signed_upload(self, path: str, content_type: str) -> SignedUpload: ...
    def signed_url(self, path: str, expires_in: int | None = None) -> str: ...
    def download_url(self, path: str, filename: str, expires_in: int | None = None) -> str:
        """브라우저가 파일로 저장하도록 하는 서명 URL."""
        ...
    def exists(self, path: str) -> bool: ...
    def size(self, path: str) -> int | None: ...
    def download(self, path: str, dest: Path) -> None: ...
    def upload_file(self, path: str, src: Path, content_type: str) -> None: ...
    def upload_bytes(self, path: str, data: bytes, content_type: str) -> None: ...
    def read_bytes(self, path: str) -> bytes: ...
    def delete_prefix(self, prefix: str) -> None: ...
    def probe_source(self, path: str) -> str:
        """ffprobe/ffmpeg에 넘길 수 있는 소스 (로컬 경로 또는 URL)."""
        ...


class SupabaseStorage(StorageBackend):
    def __init__(self) -> None:
        self.base = settings.SUPABASE_URL.rstrip("/") + "/storage/v1"
        self.bucket = settings.STORAGE_BUCKET
        key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {"Authorization": f"Bearer {key}", "apikey": key}

    def _client(self, timeout: float = 60) -> httpx.Client:
        return httpx.Client(headers=self.headers, timeout=timeout)

    def _obj(self, path: str) -> str:
        return f"{self.bucket}/{quote(path)}"

    def create_signed_upload(self, path: str, content_type: str) -> SignedUpload:
        with self._client() as c:
            r = c.post(f"{self.base}/object/upload/sign/{self._obj(path)}", headers={"x-upsert": "true"})
            r.raise_for_status()
            rel = r.json()["url"]  # "/object/upload/sign/<bucket>/<path>?token=..."
        return SignedUpload(
            url=f"{self.base}{rel}",
            method="PUT",
            headers={"Content-Type": content_type or "application/octet-stream", "x-upsert": "true"},
        )

    def signed_url(self, path: str, expires_in: int | None = None) -> str:
        with self._client() as c:
            r = c.post(
                f"{self.base}/object/sign/{self._obj(path)}",
                json={"expiresIn": expires_in or settings.SIGNED_URL_EXPIRES_SEC},
            )
            r.raise_for_status()
            rel = r.json()["signedURL"]
        return f"{self.base}{rel}"

    def download_url(self, path: str, filename: str, expires_in: int | None = None) -> str:
        url = self.signed_url(path, expires_in)
        return f"{url}&download={quote(filename)}"

    def _info(self, path: str) -> dict | None:
        with self._client() as c:
            r = c.get(f"{self.base}/object/info/{self._obj(path)}")
            if r.status_code in (400, 404):
                return None
            r.raise_for_status()
            return r.json()

    def exists(self, path: str) -> bool:
        return self._info(path) is not None

    def size(self, path: str) -> int | None:
        info = self._info(path)
        if not info:
            return None
        return info.get("size") or (info.get("metadata") or {}).get("size")

    def download(self, path: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._client(timeout=None) as c, c.stream("GET", f"{self.base}/object/{self._obj(path)}") as r:
            r.raise_for_status()
            with dest.open("wb") as f:
                for part in r.iter_bytes(1024 * 1024):
                    f.write(part)

    def upload_file(self, path: str, src: Path, content_type: str) -> None:
        with self._client(timeout=None) as c, src.open("rb") as f:
            r = c.post(
                f"{self.base}/object/{self._obj(path)}",
                content=f,
                headers={"Content-Type": content_type, "x-upsert": "true"},
            )
            r.raise_for_status()

    def upload_bytes(self, path: str, data: bytes, content_type: str) -> None:
        with self._client() as c:
            r = c.post(
                f"{self.base}/object/{self._obj(path)}",
                content=data,
                headers={"Content-Type": content_type, "x-upsert": "true"},
            )
            r.raise_for_status()

    def read_bytes(self, path: str) -> bytes:
        with self._client() as c:
            r = c.get(f"{self.base}/object/{self._obj(path)}")
            r.raise_for_status()
            return r.content

    def _list_all(self, prefix: str) -> list[str]:
        files: list[str] = []
        with self._client() as c:
            stack = [prefix.rstrip("/")]
            while stack:
                p = stack.pop()
                r = c.post(f"{self.base}/object/list/{self.bucket}", json={"prefix": p, "limit": 1000})
                r.raise_for_status()
                for item in r.json():
                    full = f"{p}/{item['name']}"
                    if item.get("id") is None:  # 폴더
                        stack.append(full)
                    else:
                        files.append(full)
        return files

    def delete_prefix(self, prefix: str) -> None:
        files = self._list_all(prefix)
        with self._client() as c:
            for i in range(0, len(files), 100):
                r = c.request("DELETE", f"{self.base}/object/{self.bucket}", json={"prefixes": files[i : i + 100]})
                r.raise_for_status()

    def probe_source(self, path: str) -> str:
        return self.signed_url(path, 600)


class LocalStorage(StorageBackend):
    def __init__(self) -> None:
        self.root = Path(settings.LOCAL_STORAGE_DIR)
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, path: str) -> Path:
        p = (self.root / path).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError("invalid path")
        return p

    @staticmethod
    def sign(path: str, exp: int, op: str) -> str:
        msg = f"{op}:{path}:{exp}".encode()
        return hmac.new(settings.LOCAL_STORAGE_SECRET.encode(), msg, hashlib.sha256).hexdigest()

    @classmethod
    def verify(cls, path: str, exp: int, op: str, sig: str) -> bool:
        return exp >= int(time.time()) and hmac.compare_digest(cls.sign(path, exp, op), sig)

    def _url(self, path: str, op: str, expires_in: int) -> str:
        exp = int(time.time()) + expires_in
        qs = urlencode({"path": path, "exp": exp, "sig": self.sign(path, exp, op)})
        return f"{settings.PUBLIC_API_BASE_URL.rstrip('/')}/api/local-storage/{op}?{qs}"

    def create_signed_upload(self, path: str, content_type: str) -> SignedUpload:
        return SignedUpload(
            url=self._url(path, "upload", 7200),
            method="PUT",
            headers={"Content-Type": content_type or "application/octet-stream"},
        )

    def signed_url(self, path: str, expires_in: int | None = None) -> str:
        return self._url(path, "object", expires_in or settings.SIGNED_URL_EXPIRES_SEC)

    def download_url(self, path: str, filename: str, expires_in: int | None = None) -> str:
        return self.signed_url(path, expires_in) + "&" + urlencode({"download": filename})

    def exists(self, path: str) -> bool:
        return self._p(path).is_file()

    def size(self, path: str) -> int | None:
        p = self._p(path)
        return p.stat().st_size if p.is_file() else None

    def local_path(self, path: str) -> Path:
        return self._p(path)

    def download(self, path: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self._p(path), dest)

    def upload_file(self, path: str, src: Path, content_type: str) -> None:
        p = self._p(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, p)

    def upload_bytes(self, path: str, data: bytes, content_type: str) -> None:
        p = self._p(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def read_bytes(self, path: str) -> bytes:
        return self._p(path).read_bytes()

    def delete_prefix(self, prefix: str) -> None:
        p = self._p(prefix)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.is_file():
            p.unlink()

    def probe_source(self, path: str) -> str:
        return str(self._p(path))


_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _storage
    if _storage is None:
        _storage = SupabaseStorage() if settings.use_supabase_storage else LocalStorage()
    return _storage


def episode_prefix(user_id, episode_id) -> str:
    return f"{user_id}/{episode_id}"
