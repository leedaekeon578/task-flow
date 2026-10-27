import sqlite3
import tempfile
import unittest
from pathlib import Path

from support import migrate

BASELINE = [
    # (id, title, description, status, owner_id) — 가짜 값. 실제 DB 의 내용이 아니다.
    (15, "t15", "", "TODO", 1),
    (17, "t17", "", "IN_PROGRESS", 1),
    (19, "t19", "abcde", "DONE", 1),
]
OLD_COLUMNS = "id, title, description, status, created_at, updated_at, owner_id"


class Migration0003Test(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Path(tmp.name) / "t.db"
        migrate(self.db, "0002")
        conn = sqlite3.connect(self.db)
        for id_, title, desc, status, owner in BASELINE:
            conn.execute(
                "INSERT INTO tasks (id, title, description, status, created_at, updated_at, owner_id)"
                " VALUES (?, ?, ?, ?, 'c', 'u', ?)",
                (id_, title, desc, status, owner),
            )
        conn.commit()
        self.before = conn.execute(f"SELECT {OLD_COLUMNS} FROM tasks ORDER BY id").fetchall()
        self.seq_before = conn.execute(
            "SELECT seq FROM sqlite_sequence WHERE name='tasks'"
        ).fetchall()
        conn.close()

    def query(self, sql):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def test_existing_rows_get_defaults_and_keep_everything_else(self):
        migrate(self.db)
        self.assertEqual(self.query(f"SELECT {OLD_COLUMNS} FROM tasks ORDER BY id"), self.before)
        self.assertEqual(
            self.query("SELECT id, priority, due_date FROM tasks ORDER BY id"),
            [(15, "NORMAL", None), (17, "NORMAL", None), (19, "NORMAL", None)],
        )
        self.assertEqual(self.query("SELECT version_num FROM alembic_version"), [("0003",)])

    def test_column_shapes(self):
        migrate(self.db)
        # (name, type, notnull, default)
        cols = {r[1]: (r[2], r[3], r[4]) for r in self.query("PRAGMA table_info(tasks)")}
        self.assertEqual(cols["priority"], ("TEXT", 1, "'NORMAL'"))
        self.assertEqual(cols["due_date"], ("TEXT", 0, None))
        self.assertEqual(len(cols), 9)

    def test_nothing_else_changes(self):
        migrate(self.db)
        self.assertEqual(
            self.query("SELECT seq FROM sqlite_sequence WHERE name='tasks'"), self.seq_before
        )
        (ddl,) = self.query("SELECT sql FROM sqlite_master WHERE name='tasks'")[0]
        self.assertIn("CHECK (status IN ('TODO', 'IN_PROGRESS', 'DONE'))", ddl)
        self.assertEqual(
            self.query("SELECT name FROM sqlite_master WHERE name='ix_tasks_owner_id'"),
            [("ix_tasks_owner_id",)],
        )
        self.assertEqual(
            sorted(r[0] for r in self.query("SELECT name FROM sqlite_master WHERE type='table'")),
            ["alembic_version", "sessions", "sqlite_sequence", "tasks", "users"],
        )

    def test_old_style_insert_still_works(self):
        # 열을 나열해 직접 넣는 기존 방식이 DEFAULT 덕에 그대로 된다.
        migrate(self.db)
        conn = sqlite3.connect(self.db)
        conn.execute(
            "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id)"
            " VALUES ('n', '', 'TODO', 'x', 'y', 1)"
        )
        conn.commit()
        conn.close()
        self.assertEqual(self.query("SELECT priority, due_date FROM tasks WHERE title='n'"), [("NORMAL", None)])

    def test_has_no_downgrade(self):
        # 되돌리기는 백업 파일로 한다. 절차 파일에 downgrade 를 두지 않는다.
        src = (Path(__file__).resolve().parent.parent / "migrations" / "versions" / "0003_priority_due.py").read_text(encoding="utf-8")
        self.assertNotIn("def downgrade", src)
