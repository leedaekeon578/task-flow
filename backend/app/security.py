import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# 비밀번호는 Argon2 로만 저장한다. 원문은 저장하지도, 응답이나 로그에 넣지도 않는다.
_hasher = PasswordHasher()
# 계정이 없거나 이전용 계정(해시 없음)일 때도 같은 검증 비용을 쓰기 위한 값
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if password_hash is None:
        try:
            _hasher.verify(_DUMMY_HASH, password)
        except (VerificationError, InvalidHashError):
            pass
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def new_session_token() -> str:
    # 쿠키에 담기는 값. 서버는 이 값 대신 hash_session_token 결과만 저장한다.
    return secrets.token_urlsafe(32)


def hash_session_token(token: str, secret: str) -> str:
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()
