import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from app.core.config import settings


class MigrationTests(unittest.TestCase):
    def test_existing_data_and_fresh_database_upgrade(self):
        previous = settings.database_url
        try:
            with TemporaryDirectory(dir=".") as directory:
                for legacy in [False, True]:
                    settings.database_url = f"sqlite:///{Path(directory).as_posix()}/{legacy}.db"
                    config = Config("alembic.ini")
                    if legacy:
                        command.upgrade(config, "0001_initial_schema")
                        engine = create_engine(settings.database_url)
                        with engine.begin() as connection:
                            connection.execute(text("INSERT INTO users (id,email,created_at,updated_at) VALUES (1,'existing@example.com',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
                            connection.execute(text("INSERT INTO projects (id,user_id,name,created_at,updated_at) VALUES (1,1,'Preserved',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
                        engine.dispose()
                    command.upgrade(config, "head")
                    engine = create_engine(settings.database_url)
                    self.assertIn("task_reviews", inspect(engine).get_table_names())
                    self.assertIn("workspace_invites", inspect(engine).get_table_names())
                    columns = {column["name"] for column in inspect(engine).get_columns("action_items")}
                    self.assertTrue({"progress_percent", "progress_updated_at", "progress_content"} <= columns)
                    with engine.connect() as connection:
                        self.assertEqual(connection.execute(text("SELECT version_num FROM alembic_version")).scalar(), "0006_example_projects")
                        self.assertIn("password_resets", inspect(engine).get_table_names())
                        if legacy:
                            self.assertEqual(connection.execute(text("SELECT name FROM projects WHERE id=1")).scalar(), "Preserved")
                            self.assertIsNotNone(connection.execute(text("SELECT workspace_id FROM projects WHERE id=1")).scalar())
                            self.assertEqual(connection.execute(text("SELECT role FROM workspace_members WHERE user_id=1")).scalar(), "OWNER")
                    engine.dispose()
        finally:
            settings.database_url = previous
