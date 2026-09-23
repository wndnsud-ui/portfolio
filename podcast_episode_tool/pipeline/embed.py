from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import INDEX_PATH, ensure_data_dirs
from .models import Candidate


def init_db(path: Path = INDEX_PATH) -> None:
    ensure_data_dirs()
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS approved_clips (
                id TEXT PRIMARY KEY,
                recording_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                title TEXT NOT NULL,
                question TEXT,
                transcript TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                audio_path TEXT,
                start REAL NOT NULL,
                end REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_clip_version ON approved_clips(recording_id, candidate_id, start, end)")


def embed_text(text: str, api_key: str | None, model: str) -> list[float]:
    if not api_key:
        return [0.0]
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    result = client.embeddings.create(model=model, input=text)
    return result.data[0].embedding


def upsert_approved_clip(
    recording_id: str,
    candidate: Candidate,
    audio_path: Path | None,
    api_key: str | None,
    model: str,
    db_path: Path = INDEX_PATH,
) -> bool:
    init_db(db_path)
    text = f"{candidate.title}\n{candidate.summary}\n{candidate.listener_question}\n{candidate.transcript}"
    embedding = embed_text(text, api_key, model)
    row_id = f"{recording_id}:{candidate.id}:{int(candidate.start * 1000)}:{int(candidate.end * 1000)}"
    with sqlite3.connect(db_path) as conn:
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO approved_clips
            (id, recording_id, candidate_id, title, question, transcript, embedding_json, audio_path, start, end, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                recording_id,
                candidate.id,
                candidate.title,
                candidate.listener_question,
                candidate.transcript,
                json.dumps(embedding),
                str(audio_path) if audio_path else None,
                candidate.start,
                candidate.end,
                "approved",
            ),
        )
        return conn.total_changes > before
