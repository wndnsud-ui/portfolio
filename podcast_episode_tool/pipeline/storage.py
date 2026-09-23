from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import RECORDINGS_DIR, ensure_data_dirs
from .models import Candidate, Transcript


def slugify(value: str, fallback: str = "clip") -> str:
    cleaned = re.sub(r"[^\w가-힣.-]+", "_", value, flags=re.UNICODE).strip("_")
    return cleaned[:80] or fallback


def recording_id(name: str, content: bytes | None = None) -> str:
    h = hashlib.sha256()
    h.update(name.encode("utf-8"))
    if content:
        h.update(content[:1024 * 1024])
        h.update(str(len(content)).encode("ascii"))
    return h.hexdigest()[:16]


def recording_dir(rid: str) -> Path:
    ensure_data_dirs()
    path = RECORDINGS_DIR / rid
    path.mkdir(parents=True, exist_ok=True)
    (path / "clips").mkdir(exist_ok=True)
    return path


def save_upload(rid: str, filename: str, content: bytes) -> Path:
    suffix = Path(filename).suffix.lower()
    target = recording_dir(rid) / f"original{suffix}"
    if not target.exists():
        target.write_bytes(content)
    return target


def save_json(path: Path, data: dict | list) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def save_transcript(rid: str, transcript: Transcript) -> Path:
    path = recording_dir(rid) / "transcript.json"
    save_json(path, transcript.model_dump())
    return path


def load_transcript(rid: str) -> Transcript | None:
    path = recording_dir(rid) / "transcript.json"
    return Transcript.model_validate(load_json(path)) if path.exists() else None


def save_candidates(rid: str, candidates: list[Candidate]) -> Path:
    path = recording_dir(rid) / "candidates.json"
    save_json(path, [c.model_dump() for c in candidates])
    return path


def load_candidates(rid: str) -> list[Candidate] | None:
    path = recording_dir(rid) / "candidates.json"
    if not path.exists():
        return None
    return [Candidate.model_validate(row) for row in load_json(path)]


def clip_base_name(candidate: Candidate) -> str:
    start = int(candidate.start * 1000)
    end = int(candidate.end * 1000)
    return f"{candidate.id}_{start}_{end}_{slugify(candidate.title)}"


def write_clip_artifacts(rid: str, candidate: Candidate, audio_path: Path | None) -> dict[str, Path]:
    clips = recording_dir(rid) / "clips"
    base = clip_base_name(candidate)
    txt_path = clips / f"{base}.txt"
    json_path = clips / f"{base}.json"
    txt_path.write_text(candidate.transcript, encoding="utf-8")
    metadata = candidate.model_dump()
    metadata["approved_at"] = datetime.now(timezone.utc).isoformat()
    metadata["audio_path"] = str(audio_path) if audio_path else None
    save_json(json_path, metadata)
    return {"txt": txt_path, "json": json_path}


def copy_demo_audio_if_needed(source: Path, target: Path) -> None:
    if not target.exists():
        shutil.copyfile(source, target)
