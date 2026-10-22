import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from app.main import app

BACKEND = Path(__file__).resolve().parent.parent
SECRET = "test-secret"

_template_dir: tempfile.TemporaryDirectory | None = None


def migrate(db: Path, revision: str = "head") -> None:
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "-x", f"db={db}", "upgrade", revision],
        cwd=BACKEND, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 0, r.stderr


def _template() -> Path:
    # alembic 으로 한 번만 만들고 테스트마다 복사해서 쓴다.
    global _template_dir
    if _template_dir is None:
        _template_dir = tempfile.TemporaryDirectory()
        migrate(Path(_template_dir.name) / "template.db")
    return Path(_template_dir.name) / "template.db"


class ApiTestCase(unittest.TestCase):
    """임시 DB(alembic 으로 이전된 모양)와 테스트용 SESSION_SECRET 으로 앱을 띄운다.
    실제 backend/.env 와 backend/data/taskflow.db 는 쓰지 않는다."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db_path = Path(tmp.name) / "t.db"
        shutil.copy(_template(), self.db_path)
        for p in (
            mock.patch("app.config.ENV_PATH", Path(tmp.name) / "no.env"),
            mock.patch("app.db.DB_PATH", self.db_path),
            mock.patch.dict(os.environ, {"SESSION_SECRET": SECRET}),
        ):
            p.start()
            self.addCleanup(p.stop)

    def new_client(self) -> TestClient:
        # 클라이언트마다 쿠키 보관함이 따로라 서로 다른 사용자처럼 쓸 수 있다.
        c = TestClient(app)
        c.__enter__()
        self.addCleanup(c.__exit__, None, None, None)
        return c

    def sql(self, query: str, args=()):
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(query, args).fetchall()
            conn.commit()
            return rows
        finally:
            conn.close()
