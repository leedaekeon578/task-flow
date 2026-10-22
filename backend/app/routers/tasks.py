import sqlite3
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_db
from ..deps import CurrentUser
from ..schemas import INITIAL_STATUS, StatusUpdate, Task, TaskCreate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

Db = Annotated[sqlite3.Connection, Depends(get_db)]

STORAGE_ERROR = "저장하지 못했습니다."
NOT_FOUND = "카드를 찾을 수 없습니다."


def _now() -> str:
    return datetime.now(UTC).isoformat()


@router.get("", response_model=list[Task])
def list_tasks(user: CurrentUser, db: Db) -> list[Task]:
    try:
        rows = db.execute(
            "SELECT * FROM tasks WHERE owner_id = ? ORDER BY id ASC", (user.id,)
        ).fetchall()
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="카드를 읽지 못했습니다.")
    return [Task(**dict(r)) for r in rows]


@router.post("", response_model=Task, status_code=201)
def create_task(body: TaskCreate, user: CurrentUser, db: Db) -> Task:
    now = _now()
    try:
        cur = db.execute(
            "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (body.title, body.description, INITIAL_STATUS, now, now, user.id),
        )
        db.commit()
        row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail=STORAGE_ERROR)
    return Task(**dict(row))


@router.patch("/{task_id}/status", response_model=Task)
def change_status(
    task_id: int, body: StatusUpdate, user: CurrentUser, db: Db
) -> Task:
    try:
        row = db.execute(
            "SELECT * FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=NOT_FOUND)
        # 같은 상태면 그대로 돌려주고 updated_at 도 바꾸지 않는다.
        if row["status"] != body.status:
            db.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ? AND owner_id = ?",
                (body.status, _now(), task_id, user.id),
            )
            db.commit()
            row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail=STORAGE_ERROR)
    return Task(**dict(row))


@router.patch("/{task_id}", response_model=Task)
def update_task(task_id: int, body: TaskCreate, user: CurrentUser, db: Db) -> Task:
    try:
        row = db.execute(
            "SELECT * FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=NOT_FOUND)
        # 제목 · 설명만 바꾼다. 상태는 건드리지 않고, 값이 같으면 updated_at 도 그대로 둔다.
        if row["title"] != body.title or row["description"] != body.description:
            db.execute(
                "UPDATE tasks SET title = ?, description = ?, updated_at = ?"
                " WHERE id = ? AND owner_id = ?",
                (body.title, body.description, _now(), task_id, user.id),
            )
            db.commit()
            row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail=STORAGE_ERROR)
    return Task(**dict(row))


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, user: CurrentUser, db: Db) -> None:
    try:
        cur = db.execute(
            "DELETE FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id)
        )
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail=STORAGE_ERROR)
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
