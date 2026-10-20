from typing import Literal

from pydantic import BaseModel, field_validator

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
