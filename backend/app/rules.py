from enum import StrEnum


class Priority(StrEnum):
    # 우선순위의 허용 값은 여기 한 곳에서만 정한다. (BUSINESS-RULES 규칙 1, 2)
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
