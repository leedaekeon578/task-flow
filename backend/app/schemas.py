import re
from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, EmailStr, Field, field_validator

from .rules import Priority

Status = Literal["TODO", "IN_PROGRESS", "DONE"]

TITLE_MAX_LENGTH = 100
INITIAL_STATUS: Status = "TODO"

_DATE_FORMAT = re.compile(r"\d{4}-\d{2}-\d{2}")


def _check_due_date(v: str) -> str:
    # 날짜만(YYYY-MM-DD). 형식이 다르거나 없는 날짜(2026-02-30)는 거부한다. 과거 날짜는 허용. (규칙 3)
    try:
        if not _DATE_FORMAT.fullmatch(v):
            raise ValueError
        date.fromisoformat(v)
    except ValueError:
        raise ValueError("마감일은 YYYY-MM-DD 형식의 실제 날짜여야 합니다.") from None
    return v


DueDate = Annotated[str, AfterValidator(_check_due_date)]


class _TaskInput(BaseModel):
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


class TaskCreate(_TaskInput):
    # 생략하면 NORMAL · null.
    priority: Priority = Priority.NORMAL
    due_date: DueDate | None = None


class TaskUpdate(_TaskInput):
    # 수정은 TaskCreate 를 쓰지 않는다. 기본값이 있으면 안 보낸 값이 덮어써지기 때문이다.
    # 안 보냄(model_fields_set 에 없음)이면 유지, due_date 의 null 은 비움, 값은 변경.
    priority: Priority | None = None
    due_date: DueDate | None = None

    @field_validator("priority")
    @classmethod
    def priority_not_null(cls, v: Priority | None) -> Priority | None:
        # 보냈는데 null 이면 거부한다. 우선순위는 지울 수 없다. (안 보냈을 때는 검증이 돌지 않는다)
        if v is None:
            raise ValueError("우선순위는 비울 수 없습니다.")
        return v


class SuggestRequest(_TaskInput):
    # 제목 · 설명 규칙은 Task 입력과 같다. 저장하지 않고 AI 제안만 받는다.
    pass


class SuggestResponse(BaseModel):
    priority: Priority
    due_date: DueDate | None
    reason: str


class GenerateRequest(BaseModel):
    # 주제 한 줄. 규칙은 Task 제목과 같다(필수, 공백만 안 됨, 100자 이하).
    topic: str

    @field_validator("topic")
    @classmethod
    def topic_rules(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("주제를 입력하세요.")
        if len(v) > TITLE_MAX_LENGTH:
            raise ValueError(f"주제는 {TITLE_MAX_LENGTH}자 이하여야 합니다.")
        return v


class GeneratedTask(BaseModel):
    # 세 값 모두 필수다. 빠지면 기본값을 채우지 않고 모양이 다른 답으로 본다.
    title: str
    priority: Priority
    due_date: DueDate | None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("제목이 비어 있습니다.")
        return v


class GenerateResponse(BaseModel):
    tasks: list[GeneratedTask] = Field(min_length=3, max_length=5)


class BriefingTop(BaseModel):
    id: int
    reason: str


class BriefingResponse(BaseModel):
    top3: list[BriefingTop] = Field(max_length=3)
    later: list[int]
    cheer: str


class StatusUpdate(BaseModel):
    status: Status


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: Status
    priority: Priority
    due_date: str | None
    overdue: bool  # 저장하지 않고 응답을 만들 때 서버가 계산한다.
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
