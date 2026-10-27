import sqlite3
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from .. import rules
from ..db import get_db
from ..deps import CurrentUser
from ..schemas import INITIAL_STATUS, StatusUpdate, Task, TaskCreate, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

Db = Annotated[sqlite3.Connection, Depends(get_db)]

STORAGE_ERROR = "저장하지 못했습니다."
NOT_FOUND = "카드를 찾을 수 없습니다."


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_task(row: sqlite3.Row, today: date) -> Task:
    # overdue 는 저장하지 않고 여기서 계산한다. owner_id 는 Task 에 없어 응답에 나가지 않는다.
    return Task(**dict(row), overdue=rules.is_overdue(row["due_date"], row["status"], today))


@router.get("", response_model=list[Task])
def list_tasks(user: CurrentUser, db: Db) -> list[Task]:
    try:
        rows = db.execute(
            "SELECT * FROM tasks WHERE owner_id = ? ORDER BY id ASC", (user.id,)
        ).fetchall()
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="카드를 읽지 못했습니다.")
    # 정렬은 서버가 한다. 기한 초과 → 우선순위 → 마감일 → id. 화면은 열 단위로 나누기만 한다.
    today = rules.today()
    rows = sorted(rows, key=lambda r: rules.sort_key(r, today))
    return [_to_task(r, today) for r in rows]


@router.post("", response_model=Task, status_code=201)
def create_task(body: TaskCreate, user: CurrentUser, db: Db) -> Task:
    now = _now()
    try:
        cur = db.execute(
            "INSERT INTO tasks"
            " (title, description, status, priority, due_date, created_at, updated_at, owner_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                body.title,
                body.description,
                INITIAL_STATUS,
                body.priority.value,
                body.due_date,
                now,
                now,
                user.id,
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail=STORAGE_ERROR)
    return _to_task(row, rules.today())


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
    return _to_task(row, rules.today())


@router.patch("/{task_id}", response_model=Task)
def update_task(task_id: int, body: TaskUpdate, user: CurrentUser, db: Db) -> Task:
    try:
        row = db.execute(
            "SELECT * FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=NOT_FOUND)
        # 제목 · 설명 · 우선순위 · 마감일을 바꾼다. 상태는 건드리지 않는다.
        # 제목 · 설명은 지금처럼 항상 보낸 값이 기준이다(설명을 안 보내면 빈 설명).
        # 우선순위 · 마감일은 안 보내면 저장된 값을 유지하고, 마감일의 null 은 비운다.
        sent = body.model_fields_set
        new = (
            body.title,
            body.description,
            body.priority.value if "priority" in sent else row["priority"],
            body.due_date if "due_date" in sent else row["due_date"],
        )
        # 네 값 중 하나라도 실제로 바뀔 때만 저장하고 updated_at 을 갱신한다.
        if new != (row["title"], row["description"], row["priority"], row["due_date"]):
            db.execute(
                "UPDATE tasks SET title = ?, description = ?, priority = ?, due_date = ?,"
                " updated_at = ? WHERE id = ? AND owner_id = ?",
                (*new, _now(), task_id, user.id),
            )
            db.commit()
            row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail=STORAGE_ERROR)
    return _to_task(row, rules.today())


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
