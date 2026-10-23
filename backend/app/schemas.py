from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, EmailStr, Field, field_validator

Status = Literal["TODO", "IN_PROGRESS", "DONE"]

TITLE_MAX_LENGTH = 100
INITIAL_STATUS: Status = "TODO"


class TaskCreate(BaseModel):
    title: str
    description: str = ""

    @field_validator("title")
    @classmethod
    def title_rules(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("제목을 입력하세요.")
        if len(v) > TITLE_MAX_LENGTH:
            raise ValueError(f"제목은 {TITLE_MAX_LENGTH}자 이하여야 합니다.")
        return v


class StatusUpdate(BaseModel):
    status: Status


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: Status
    created_at: str
    updated_at: str


PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128  # Argon2 계산 비용을 키우는 아주 긴 입력을 막는다.


def _normalize_email(v: object) -> object:
    # 같은 이메일이 대소문자만 달라 둘로 가입되지 않도록 소문자로 통일한다.
    return v.strip().lower() if isinstance(v, str) else v


NormalizedEmail = Annotated[EmailStr, BeforeValidator(_normalize_email)]


class SignupRequest(BaseModel):
    email: NormalizedEmail
    password: str

    @field_validator("password")
    @classmethod
    def password_rules(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"비밀번호는 {PASSWORD_MIN_LENGTH}자 이상이어야 합니다.")
        if len(v) > PASSWORD_MAX_LENGTH:
            raise ValueError(f"비밀번호는 {PASSWORD_MAX_LENGTH}자 이하여야 합니다.")
        return v


class LoginRequest(BaseModel):
    email: NormalizedEmail
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class User(BaseModel):
    # 비밀번호와 해시는 응답에 넣지 않는다.
    id: int
    email: str
