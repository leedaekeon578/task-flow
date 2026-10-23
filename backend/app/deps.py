import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from .config import SESSION_COOKIE
from .db import get_db
from .schemas import User
from .security import hash_session_token

Db = Annotated[sqlite3.Connection, Depends(get_db)]

NOT_LOGGED_IN = "로그인이 필요합니다."


@dataclass
class AuthSession:
    user: User
    token_hash: str


def get_session(request: Request, db: Db) -> AuthSession:
    # 세션이 없거나, 틀렸거나, 만료됐으면 모두 같은 401 이다.
    unauthorized = HTTPException(status_code=401, detail=NOT_LOGGED_IN)
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise unauthorized
    token_hash = hash_session_token(token, request.app.state.session_secret)
    try:
        row = db.execute(
            "SELECT u.id, u.email, s.expires_at FROM sessions s"
            " JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
            (token_hash,),
        ).fetchone()
        if row is None:
            raise unauthorized
        if datetime.fromisoformat(row["expires_at"]) <= datetime.now(UTC):
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            db.commit()
            raise unauthorized
    except sqlite3.Error:
        db.rollback()
        raise HTTPException(status_code=500, detail="로그인 상태를 확인하지 못했습니다.")
    return AuthSession(user=User(id=row["id"], email=row["email"]), token_hash=token_hash)


Session = Annotated[AuthSession, Depends(get_session)]


def current_user(session: Session) -> User:
    return session.user


CurrentUser = Annotated[User, Depends(current_user)]
