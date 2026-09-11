"""Import a Notion-exported JSON or CSV file into the local SQLite database.

Examples:
    python import_reading_data.py reading_books.json
    python import_reading_data.py reading_books.csv

JSON may be a list of books, or {"books": [...]} with optional "notes" per book.
CSV expects one book per row. Notes can be supplied as a JSON list in a `notes` column.
"""
import csv
import json
import sys
from pathlib import Path

from app import app
from models import db, Book, ReadingNote

BOOK_FIELDS = ["title", "author", "publisher", "genre", "record_type", "start_date", "finish_date", "status", "cover_image", "rating", "summary", "notion_url", "notion_page_id"]
NOTE_FIELDS = ["title", "chapter", "page", "quote", "summary", "my_thought", "question", "answer", "application", "keywords", "source_url"]

def read_export(path):
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload.get("books", payload) if isinstance(payload, dict) else payload
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))
    raise ValueError("지원 형식은 .json 또는 .csv입니다.")

def clean(value):
    return None if value in (None, "") else str(value).strip()

def source_key(data):
    return clean(data.get("notion_page_id")) or clean(data.get("notion_url"))

def existing_book(data):
    page_id = clean(data.get("notion_page_id"))
    notion_url = clean(data.get("notion_url"))
    if page_id:
        book = Book.query.filter_by(notion_page_id=page_id).first()
        if book: return book
    if notion_url:
        return Book.query.filter_by(notion_url=notion_url).first()
    return None

def import_books(records):
    created = updated = notes_created = skipped = 0
    for raw in records:
        data = dict(raw)
        book = existing_book(data)
        if book is None:
            if not clean(data.get("title")):
                skipped += 1
                continue
            book = Book(title=clean(data.get("title")))
            db.session.add(book)
            created += 1
        else:
            updated += 1
        for field in BOOK_FIELDS:
            if field in data and field != "title":
                value = clean(data[field])
                if field == "rating" and value is not None:
                    value = float(value)
                setattr(book, field, value)
        db.session.flush()
        notes = data.get("notes", [])
        if isinstance(notes, str) and notes:
            notes = json.loads(notes)
        for note_data in notes or []:
            note = ReadingNote(book_id=book.id)
            for field in NOTE_FIELDS:
                if field in note_data:
                    setattr(note, field, clean(note_data[field]))
            db.session.add(note)
            notes_created += 1
    db.session.commit()
    return created, updated, notes_created, skipped

def main():
    if len(sys.argv) != 2:
        print("사용법: python import_reading_data.py reading_books.json|csv")
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"파일을 찾을 수 없습니다: {path}")
        return 1
    with app.app_context():
        db.create_all()
        result = import_books(read_export(path))
    print(f"Import 완료 — 신규 도서 {result[0]}개, 갱신 {result[1]}개, 노트 {result[2]}개, 건너뜀 {result[3]}개")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
