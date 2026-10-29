from datetime import date, datetime, timedelta, timezone
from enum import StrEnum


class Priority(StrEnum):
    # 우선순위의 허용 값은 여기 한 곳에서만 정한다. (BUSINESS-RULES 규칙 1, 2)
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


# 정렬에서 앞에 오는 순서: HIGH → NORMAL → LOW (규칙 5)
PRIORITY_RANK = {Priority.HIGH: 0, Priority.NORMAL: 1, Priority.LOW: 2}

# 「오늘」의 기준 시간대. 지금은 한국 시간(UTC+9, 서머타임 없음).
# UTC 로 바꾸려면 이 값만 timezone.utc 로 바꾼다. (Q-5, 사람이 확정하기 전)
TODAY_TZ = timezone(timedelta(hours=9))


def today() -> date:
    # 오늘 날짜를 계산하는 유일한 곳. 기한 초과 판단과 정렬이 모두 여기서 받는다.
    return datetime.now(TODAY_TZ).date()


def safe_priority(value) -> str:
    # DB 에는 CHECK 가 없어 허용 값 밖의 값이 있을 수 있다. 읽을 때는 NORMAL 로 본다.
    try:
        return Priority(value).value
    except ValueError:
        return Priority.NORMAL.value


def safe_due(value) -> str | None:
    # YYYY-MM-DD 가 아니거나 없는 날짜면 마감일 없음으로 본다. 읽기에서 500 을 내지 않는다.
    if not isinstance(value, str):
        return None
    try:
        return value if date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def is_overdue(due_date: str | None, status: str, today_: date) -> bool:
    # 규칙 4: 마감일이 오늘보다 이전(당일은 아님)이고 완료가 아닐 때. 저장하지 않고 계산한다.
    due = safe_due(due_date)
    if due is None or status == "DONE":
        return False
    return date.fromisoformat(due) < today_


def sort_key(row, today_: date) -> tuple:
    # 규칙 5: 기한 초과 → 우선순위 → 가까운 마감일(없으면 뒤) → id
    due = safe_due(row["due_date"])
    return (
        not is_overdue(due, row["status"], today_),
        PRIORITY_RANK[Priority(safe_priority(row["priority"]))],
        due is None,
        due or "",
        row["id"],
    )
