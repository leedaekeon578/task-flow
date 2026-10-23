import os
from collections.abc import Mapping
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# D-019: 로그인 유지 시간은 30분이다. 사용할 때마다 연장하지 않는다.
SESSION_MAX_AGE = 1800
SESSION_COOKIE = "session"


class ConfigError(RuntimeError):
    pass


def load_env_file() -> None:
    # 이미 설정된 환경변수는 덮어쓰지 않는다. 값은 backend/.env 에만 두고 Git 에 넣지 않는다.
    load_dotenv(ENV_PATH, override=False)


def load_session_secret(environ: Mapping[str, str] | None = None) -> str:
    # 없거나 비었으면 서버 시작을 거부한다.
    env = os.environ if environ is None else environ
    secret = env.get("SESSION_SECRET", "").strip()
    if not secret:
        raise ConfigError(
            "SESSION_SECRET 이 비어 있습니다. backend/.env 에 값을 채우세요. (.env.example 참고)"
        )
    return secret
