import sqlite3
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_db
from ..schemas import INITIAL_STATUS, Task, TaskCreate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

Db = Annotated[sqlite3.Connection, Depends(get_db)]

STORAGE_ERROR = "저장하지 못했습니다."


def _now() -> str:
    return datetime.now(UTC).isoformat()


@router.get("", response_model=list[Task])
def list_tasks(db: Db) -> list[Task]:
    try:
        rows = db.execute("SELECT * FROM tasks ORDER BY id ASC").fetchall()
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="카드를 읽지 못했습니다.")
    return [Task(**dict(r)) for r in rows]


@router.post("", response_model=Task, status_code=201)
def create_task(body: TaskCreate, db: Db) -> Task:
    now = _now()
    try:
        cur = db.execute(
            "INSERT INTO tasks (title, description, status, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (body.title, body.description, INITIAL_STATUS, now, now),
        )
        db.commit()
        row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail=STORAGE_ERROR)
    return Task(**dict(row))
