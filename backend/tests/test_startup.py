import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from app.main import app
from support import migrate


class StartupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "t.db"
        # 실제 backend/.env 와 실제 DB 를 건드리지 않는다.
        for p in (
            mock.patch("app.config.ENV_PATH", Path(self.tmp.name) / "no.env"),
            mock.patch("app.db.DB_PATH", self.db),
            mock.patch.dict(os.environ, {"SESSION_SECRET": "test-secret"}),
        ):
            p.start()
            self.addCleanup(p.stop)

    def start(self):
        with TestClient(app) as c:
            return c.get("/health")

    def test_starts_when_migrated_and_secret_set(self):
        migrate(self.db)
        self.assertEqual(self.start().status_code, 200)

    def test_refuses_without_session_secret(self):
        migrate(self.db)
        for value in ("", "  "):
            with self.subTest(value=value), mock.patch.dict(os.environ, {"SESSION_SECRET": value}):
                with self.assertRaisesRegex(RuntimeError, "SESSION_SECRET"):
                    self.start()

    def test_refuses_when_db_missing(self):
        with self.assertRaisesRegex(RuntimeError, "alembic upgrade head"):
            self.start()
        self.assertFalse(self.db.exists())  # 빈 파일을 만들지 않는다

    def test_refuses_unmigrated_db(self):
        sqlite3.connect(self.db).close()  # alembic_version 없음
        with self.assertRaisesRegex(RuntimeError, "최신 버전이 아닙니다"):
            self.start()

    def test_refuses_old_revision(self):
        migrate(self.db, "0001")
        with self.assertRaisesRegex(RuntimeError, "최신 버전이 아닙니다"):
            self.start()
