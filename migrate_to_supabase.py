"""SQLite → Supabase(PostgreSQL) 일회성 이관.

순서
  1. .env(~/Desktop/프로젝트/포트폴리오/env.txt)에 DATABASE_URL(Supabase Session pooler 주소)을 넣고 `flask db upgrade`로 빈 테이블을 만든다.
  2. 배포 사이트에서 받은 SQLite 파일을 원본으로 지정해 실행한다.
       python migrate_to_supabase.py --source path/to/portfolio.db            # 미리보기(쓰지 않음)
       python migrate_to_supabase.py --source path/to/portfolio.db --apply    # 실제 복사
       python migrate_to_supabase.py --source path/to/portfolio.db --apply --images   # 이미지도 Storage로

하는 일
  - 원본 파일을 임시 복사본으로 만들어 마이그레이션(0002 데이터 변환 포함)을 적용한다. 원본은 건드리지 않는다.
  - 테이블을 id까지 그대로 대상 DB에 복사하고, id 시퀀스를 최댓값에 맞춘다.
  - 테이블별 건수를 원본과 비교해 출력한다.
  - --images: /static/... 경로의 이미지를 Supabase Storage(media 버킷)에 올리고 DB의 주소를 공개 URL로 바꾼다.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import sqlalchemy as sa

BASE_DIR = Path(__file__).resolve().parent
TABLES = ["profile", "project", "experience", "skill", "books", "archive", "reading_notes", "record_comments", "sync_logs", "pages"]
IMAGE_COLUMNS = {
    "profile": ["photo"],
    "project": ["thumbnail", "cover_image"],
    "archive": ["thumbnail", "cover_image"],
    "books": ["cover_image"],
    "pages": ["cover_image"],
}
JSON_BLOCK_TABLES = ["profile", "project", "archive", "pages"]


def run_migrations(sqlite_path):
    """임시 복사본을 최신 스키마로 올린다. alembic_version이 없으면 baseline으로 표시한 뒤 올린다."""
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{sqlite_path}", "FLASK_APP": "app.py", "PYTHONDONTWRITEBYTECODE": "1"}
    engine = sa.create_engine(f"sqlite:///{sqlite_path}")
    if "alembic_version" not in sa.inspect(engine).get_table_names():
        subprocess.run([sys.executable, "-m", "flask", "db", "stamp", "0001_baseline"], cwd=BASE_DIR, env=env, check=True)
    subprocess.run([sys.executable, "-m", "flask", "db", "upgrade"], cwd=BASE_DIR, env=env, check=True)
    engine.dispose()


def target_url():
    sys.path.insert(0, str(BASE_DIR))
    from config import database_url  # import 시 .env를 읽는다 (config.env_file 참고)

    url = database_url()
    if not url.startswith("postgresql"):
        sys.exit("DATABASE_URL이 PostgreSQL(Supabase) 주소가 아닙니다. .env(~/Desktop/프로젝트/포트폴리오/env.txt)를 확인하세요.")
    return url


def copy_tables(source, target, apply):
    src_meta, dst_meta = sa.MetaData(), sa.MetaData()
    src_meta.reflect(source)
    dst_meta.reflect(target)
    with target.connect() as dst:
        for name in TABLES:
            if name not in dst_meta.tables:
                sys.exit(f"대상 DB에 {name} 테이블이 없습니다. 먼저 `flask db upgrade`를 실행하세요.")
            existing = dst.execute(sa.select(sa.func.count()).select_from(dst_meta.tables[name])).scalar()
            if existing:
                sys.exit(f"대상 DB의 {name} 테이블이 비어 있지 않습니다({existing}건). 이관은 빈 DB에만 합니다.")
    counts = {}
    with source.connect() as src, target.begin() as dst:
        for name in TABLES:
            if name not in src_meta.tables:
                counts[name] = (0, 0)
                continue
            dst_table = dst_meta.tables[name]
            columns = [c.name for c in dst_table.columns if c.name in src_meta.tables[name].columns]
            rows = [dict(row._mapping) for row in src.execute(sa.select(*[src_meta.tables[name].c[c] for c in columns]))]
            if apply and rows:
                dst.execute(dst_table.insert(), rows)
                # id를 그대로 넣었으므로 다음 id가 겹치지 않게 시퀀스를 최댓값으로 맞춘다
                dst.execute(sa.text(
                    f"SELECT setval(pg_get_serial_sequence('\"{name}\"', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM \"{name}\"), 1), (SELECT MAX(id) FROM \"{name}\") IS NOT NULL)"))
            counts[name] = (len(rows), None)
        if not apply:
            dst.rollback()
    if apply:
        with target.connect() as dst:
            for name in TABLES:
                counts[name] = (counts[name][0], dst.execute(sa.select(sa.func.count()).select_from(dst_meta.tables[name])).scalar())
    return counts


def move_images(target):
    """/static/... 이미지를 Storage로 올리고 DB 주소를 바꾼다."""
    from supabase import create_client

    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    bucket = os.environ.get("SUPABASE_BUCKET", "media")
    uploaded = {}

    def to_storage(url):
        if not url or not url.startswith("/static/"):
            return url
        if url in uploaded:
            return uploaded[url]
        path = BASE_DIR / url.lstrip("/")
        if not path.exists():
            print(f"  ! 파일 없음, 그대로 둠: {url}")
            return url
        key = "migrated/" + url[len("/static/"):]
        content_type = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp",
                        "svg": "image/svg+xml", "pdf": "application/pdf"}.get(path.suffix.lower().lstrip("."), "application/octet-stream")
        client.storage.from_(bucket).upload(key, path.read_bytes(), {"content-type": content_type, "upsert": "true"})
        uploaded[url] = client.storage.from_(bucket).get_public_url(key).rstrip("?")
        print(f"  ↑ {url} → {uploaded[url]}")
        return uploaded[url]

    meta = sa.MetaData()
    meta.reflect(target)
    with target.begin() as conn:
        for name in set(IMAGE_COLUMNS) | set(JSON_BLOCK_TABLES):
            table = meta.tables[name]
            cols = [c for c in IMAGE_COLUMNS.get(name, [])] + (["blocks"] if name in JSON_BLOCK_TABLES else [])
            for row in conn.execute(sa.select(table.c.id, *[table.c[c] for c in cols])):
                values = {}
                for col in IMAGE_COLUMNS.get(name, []):
                    new = to_storage(row._mapping[col])
                    if new != row._mapping[col]:
                        values[col] = new
                blocks = row._mapping.get("blocks")
                if isinstance(blocks, list):
                    changed = False
                    for block in blocks:
                        for key in ("url", "url2"):
                            if isinstance(block, dict) and block.get(key):
                                new = to_storage(block[key])
                                changed |= new != block[key]
                                block[key] = new
                    if changed:
                        values["blocks"] = blocks
                if values:
                    conn.execute(table.update().where(table.c.id == row.id).values(**values))
    print(f"이미지 {len(uploaded)}개를 Storage로 옮겼습니다.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="원본 SQLite 파일 (배포 사이트의 portfolio.db)")
    parser.add_argument("--apply", action="store_true", help="실제로 복사한다 (없으면 건수만 확인)")
    parser.add_argument("--images", action="store_true", help="이미지를 Supabase Storage로 옮긴다 (--apply와 함께)")
    args = parser.parse_args()

    source_file = Path(args.source).resolve()
    if not source_file.exists():
        sys.exit(f"원본 파일이 없습니다: {source_file}")
    url = target_url()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "source.db"
        shutil.copy(source_file, work)
        print("1) 원본 복사본에 마이그레이션 적용")
        run_migrations(work)
        print("2) 테이블 복사" + ("" if args.apply else " (미리보기 — 쓰지 않음)"))
        counts = copy_tables(sa.create_engine(f"sqlite:///{work}"), sa.create_engine(url), args.apply)
    print(f"\n{'테이블':<18}{'원본':>6}{'대상':>6}")
    ok = True
    for name, (src_count, dst_count) in counts.items():
        mark = "" if dst_count is None else (" ✓" if src_count == dst_count else " ✗")
        ok &= dst_count is None or src_count == dst_count
        print(f"{name:<18}{src_count:>6}{'' if dst_count is None else dst_count:>6}{mark}")
    if args.apply and args.images:
        print("\n3) 이미지 이전")
        move_images(sa.create_engine(url))
    if not ok:
        sys.exit("건수가 다른 테이블이 있습니다.")


if __name__ == "__main__":
    main()
