"""baseline: 로그인 도입 전의 tasks 표

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 로그인 도입 전(기존 app/db.py 의 SCHEMA)과 같은 모양. 이미 만들어진 DB 는 `alembic stamp 0001` 로 표시만 한다.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
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


def downgrade() -> None:
    op.execute("DROP TABLE tasks")
