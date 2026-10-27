"""우선순위 · 마감일: tasks.priority, tasks.due_date (#17)

Revision ID: 0003
Revises: 0002

downgrade 는 만들지 않는다. 되돌리기는 upgrade 전에 만든 DB 백업 파일로 한다.
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 표를 다시 만들지 않고 열만 더한다. 기존 행은 priority 'NORMAL', due_date NULL 이 된다.
    # 허용 값 검사(LOW · NORMAL · HIGH)는 CHECK 없이 앱(app/rules.py)이 한다.
    op.execute("ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'NORMAL'")
    op.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
