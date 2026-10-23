"""로그인 도입: users · sessions 표와 tasks.owner_id (R-009, D-018)

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# D-018: 기존 Task 의 주인. password_hash 가 NULL 이라 처음에는 로그인할 수 없고,
# 이 이메일로 처음 가입하는 사람이 비밀번호를 정해 계정과 기존 Task 를 받는다.
MIGRATED_EMAIL = "migrated@test.com"


def upgrade() -> None:
    conn = op.get_bind()

    op.execute(
        """
        CREATE TABLE users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            created_at    TEXT NOT NULL
        )
        """
    )
    # token_hash: 쿠키 값의 HMAC. 쿠키 값 원문은 저장하지 않는다.
    op.execute(
        """
        CREATE TABLE sessions (
            token_hash TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_sessions_user_id ON sessions (user_id)")

    conn.exec_driver_sql(
        "INSERT INTO users (email, password_hash, created_at)"
        " VALUES (?, NULL, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now'))",
        (MIGRATED_EMAIL,),
    )
    migrated_id = conn.exec_driver_sql(
        "SELECT id FROM users WHERE email = ?", (MIGRATED_EMAIL,)
    ).scalar_one()

    # SQLite 는 기존 표에 NOT NULL + FK 열을 더할 수 없어 표를 새로 만들어 옮긴다.
    # 기존 값(id · 제목 · 설명 · 상태 · 시각)은 그대로 복사하고 owner_id 만 채운다.
    old_seq = conn.exec_driver_sql(
        "SELECT seq FROM sqlite_sequence WHERE name = 'tasks'"
    ).scalar()
    op.execute(
        """
        CREATE TABLE tasks_new (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status      TEXT NOT NULL DEFAULT 'TODO'
                        CHECK (status IN ('TODO', 'IN_PROGRESS', 'DONE')),
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            owner_id    INTEGER NOT NULL REFERENCES users(id)
        )
        """
    )
    conn.exec_driver_sql(
        "INSERT INTO tasks_new"
        " (id, title, description, status, created_at, updated_at, owner_id)"
        " SELECT id, title, description, status, created_at, updated_at, ?"
        " FROM tasks",
        (migrated_id,),
    )
    op.execute("DROP TABLE tasks")
    op.execute("ALTER TABLE tasks_new RENAME TO tasks")
    _restore_sequence(conn, old_seq)
    op.execute("CREATE INDEX ix_tasks_owner_id ON tasks (owner_id)")


def downgrade() -> None:
    # users · sessions 의 내용(가입한 계정 포함)은 사라진다. tasks 는 owner_id 만 빠진다.
    conn = op.get_bind()
    old_seq = conn.exec_driver_sql(
        "SELECT seq FROM sqlite_sequence WHERE name = 'tasks'"
    ).scalar()
    op.execute(
        """
        CREATE TABLE tasks_old (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status      TEXT NOT NULL DEFAULT 'TODO'
                        CHECK (status IN ('TODO', 'IN_PROGRESS', 'DONE')),
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )
    op.execute(
        "INSERT INTO tasks_old (id, title, description, status, created_at, updated_at)"
        " SELECT id, title, description, status, created_at, updated_at FROM tasks"
    )
    op.execute("DROP TABLE tasks")
    op.execute("ALTER TABLE tasks_old RENAME TO tasks")
    _restore_sequence(conn, old_seq)
    op.execute("DROP TABLE sessions")
    op.execute("DROP TABLE users")


def _restore_sequence(conn, old_seq) -> None:
    # 표를 새로 만들면 AUTOINCREMENT 카운터가 현재 최대 id 로 줄어든다.
    # 삭제된 id 가 다시 쓰이지 않도록 원래 값으로 되돌린다.
    if old_seq is None:
        return
    updated = conn.exec_driver_sql(
        "UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = 'tasks'", (old_seq,)
    ).rowcount
    if not updated:
        conn.exec_driver_sql(
            "INSERT INTO sqlite_sequence (name, seq) VALUES ('tasks', ?)", (old_seq,)
        )
