"""Copy a reviewed SQLite backup into an EMPTY PostgreSQL database.

Credentials are read from TARGET_DATABASE_URL and are never printed.
The source is read only; unknown tables/columns abort instead of discarding data.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings


def run(source_path, target_url):
    if make_url(target_url).get_backend_name() != "postgresql":
        raise RuntimeError("Target must be PostgreSQL")
    target = create_engine(target_url)
    if inspect(target).get_table_names():
        raise RuntimeError("Target database must be empty; no existing data will be overwritten")
    source = create_engine(f"sqlite:///file:{Path(source_path).resolve().as_posix()}?mode=ro&uri=true")
    with source.connect() as conn:
        if conn.execute(text("PRAGMA integrity_check")).scalar_one() != "ok":
            raise RuntimeError("Source integrity check failed")
    spec = importlib.util.spec_from_file_location("initial", "app/db/migrations/versions/0001_initial_schema.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = module.initial_metadata()
    old = MetaData()
    old.reflect(bind=source)
    unknown = set(old.tables) - set(schema.tables) - {"alembic_version"}
    if unknown:
        raise RuntimeError(f"Unrecognized source tables: {sorted(unknown)}")
    for name, table in old.tables.items():
        if name in schema.tables and set(table.c.keys()) - set(schema.tables[name].c.keys()):
            raise RuntimeError(f"Unrecognized columns in {name}")
    previous = settings.database_url
    settings.database_url = target_url
    try:
        command.upgrade(Config("alembic.ini"), "0001_initial_schema")
        counts = {}
        with source.connect() as reader, target.begin() as writer:
            for table in schema.sorted_tables:
                rows = list(reader.execute(select(old.tables[table.name])).mappings()) if table.name in old.tables else []
                for original in rows:
                    row = dict(original)
                    if table.name == "meetings":
                        row.setdefault("speaker_names", {})
                    for column in table.c:
                        if column.name not in row:
                            if column.nullable:
                                row[column.name] = None
                            else:
                                raise RuntimeError(f"Missing required column: {table.name}.{column.name}")
                    writer.execute(table.insert().values(**row))
                counts[table.name] = len(rows)
                if "id" in table.c:
                    writer.execute(text("SELECT setval(pg_get_serial_sequence(:table, 'id'), COALESCE((SELECT MAX(id) FROM " + table.name + "), 1), EXISTS(SELECT 1 FROM " + table.name + "))"), {"table": table.name})
            for name, count in counts.items():
                if writer.execute(text("SELECT count(*) FROM " + name)).scalar_one() != count:
                    raise RuntimeError(f"Row count mismatch: {name}")
        command.upgrade(Config("alembic.ini"), "head")
        print(json.dumps({"imported_rows": counts, "migration": "head", "source_unchanged": True}))
    finally:
        settings.database_url = previous
        source.dispose()
        target.dispose()


if __name__ == "__main__":
    run(sys.argv[1], os.environ["TARGET_DATABASE_URL"])
