import sqlite3
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response

from ..config import SESSION_COOKIE, SESSION_MAX_AGE
from ..deps import CurrentUser, Db, Session
from ..schemas import LoginRequest, SignupRequest, User
from ..security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

STORAGE_ERROR = "저장하지 못했습니다."
EMAIL_TAKEN = "이미 가입된 이메일입니다."
LOGIN_FAILED = "이메일 또는 비밀번호가 맞지 않습니다."


def _start_session(db: Db, request: Request, response: Response, user_id: int) -> None:
    # 쿠키에는 무작위 값, DB 에는 그 값의 HMAC 만 둔다. 연장하지 않는다. (D-019)
    token = new_session_token()
    now = datetime.now(UTC)
    db.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (
            hash_session_token(token, request.app.state.session_secret),
            user_id,
            now.isoformat(),
            (now + timedelta(seconds=SESSION_MAX_AGE)).isoformat(),
        ),
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/signup", response_model=User, status_code=201)
def signup(body: SignupRequest, request: Request, response: Response, db: Db) -> User:
    password_hash = hash_password(body.password)
    try:
        row = db.execute(
            "SELECT id, password_hash FROM users WHERE email = ?", (body.email,)
        ).fetchone()
        if row is None:
            cur = db.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (body.email, password_hash, datetime.now(UTC).isoformat()),
            )
            user_id = cur.lastrowid
        elif row["password_hash"] is None:
            # 이전용 계정(D-018): 처음 가입하는 사람이 비밀번호를 정하고 계정과 기존 Task 를 받는다.
            cur = db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ? AND password_hash IS NULL",
                (password_hash, row["id"]),
            )
            if cur.rowcount == 0:
                db.rollback()
                raise HTTPException(status_code=409, detail=EMAIL_TAKEN)
            user_id = row["id"]
        else:
            raise HTTPException(status_code=409, detail=EMAIL_TAKEN)
        _start_session(db, request, response, user_id)
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=EMAIL_TAKEN)
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail=STORAGE_ERROR)
    return User(id=user_id, email=body.email)


@router.post("/login", response_model=User)
def login(body: LoginRequest, request: Request, response: Response, db: Db) -> User:
    try:
        row = db.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?", (body.email,)
        ).fetchone()
        # 없는 계정 · 틀린 비밀번호 · 이전용 계정(해시 없음)을 구분하지 않는다.
        if not verify_password(row["password_hash"] if row else None, body.password) or row is None:
            raise HTTPException(status_code=401, detail=LOGIN_FAILED)
        _start_session(db, request, response, row["id"])
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail=STORAGE_ERROR)
    return User(id=row["id"], email=row["email"])


@router.post("/logout", status_code=204)
def logout(session: Session, response: Response, db: Db) -> None:
    try:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (session.token_hash,))
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail=STORAGE_ERROR)
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")


@router.get("/me", response_model=User)
def me(user: CurrentUser) -> User:
    return user
