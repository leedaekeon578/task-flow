import sqlite3
from collections.abc import Iterator
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "data" / "taskflow.db"
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class SchemaError(RuntimeError):
    pass


def check_schema() -> None:
    # 표는 Alembic 이 만든다. 서버는 만들지 않고, 이전이 안 된 DB 면 시작을 거부한다. (AQ-01)
    if not DB_PATH.exists():
        raise SchemaError(
            "DB 파일이 없습니다. backend 폴더에서 `uv run alembic upgrade head` 를 실행하세요."
        )
    head = ScriptDirectory.from_config(Config(str(ALEMBIC_INI))).get_current_head()
    conn = connect()
    try:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    except sqlite3.OperationalError:
        row = None
    finally:
        conn.close()
    if row is None or row["version_num"] != head:
        raise SchemaError(
            "DB 가 최신 버전이 아닙니다. 백업한 뒤 `uv run alembic upgrade head` 를 실행하세요."
        )


def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
