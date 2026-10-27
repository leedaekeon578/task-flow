# 변경 제안 — 우선순위와 마감일

- 상태: 제안 (사람의 결정 전)
- 출처: PRODUCT-DIRECTION.md, PRD.md, 현재 코드(backend/app, backend/tests, frontend/src/components)

## 사용자 문제

- 현재 문제: 중요도와 기한을 Task에 적을 수 없다.
- 원하는 결과: 먼저 볼 일과 마감 위험을 카드에서 바로 확인한다.

## 새 Must

규칙은 아직 정하지 않았다. 아래 "미정"은 모두 사람이 정하며, Agent가 정하지 않는다.

| 항목 | 내용 | PRD 반영 | 미정 (사람이 정함) |
|------|------|----------|--------------------|
| 마감일 입력 | 카드에 마감일을 적는다. | PRD.md R-010 (Later의 "마감일"을 옮김) | 마감일 형식, 비워 둘 수 있는지, 기존 Task의 기본값 |
| 우선순위 선택 | 카드에 우선순위를 골라 적는다. | 아직 반영하지 않음 | 우선순위 단계, 기존 Task의 기본값 |
| 기한 초과 표시 | 마감일이 지난 카드를 카드에서 바로 알아볼 수 있게 표시한다. | 아직 반영하지 않음 | 기한 초과 기준 |
| 정렬 | 먼저 볼 일이 앞에 오도록 카드를 정렬한다. | 아직 반영하지 않음 | 정렬 순서 (PRD Q-06 "같은 상태 안의 카드 순서"와 관련) |

## 이번에 안 할 것

아래 세 가지는 Must로 올리지 않는다.

- 알림 (PRD에는 "결제 · 외부 알림"으로 이미 만들지 않는 것에 있음)
- 반복 일정
- 시간 단위 마감

## 유지해야 할 것

지난 시간까지 동작하던 기능 중, 이번 변경 뒤에도 깨지면 안 되는 것이다. PRD.md와 코드에서 읽고 확인한 것만 적었다.

| 영역 | 유지할 동작 | 근거 |
|------|-------------|------|
| 등록 | 제목은 공백만으로 등록할 수 없고(422), 100자 이하여야 한다. 설명은 선택이며 기본값은 빈 문자열이다. 새 카드는 TODO 상태로 시작한다. | backend/app/schemas.py, backend/app/routers/tasks.py, backend/tests/test_tasks.py |
| 상태 변경 | 세 상태 중 어느 곳으로든 바꿀 수 있고, 자동으로 바뀌지 않는다. 같은 상태로 바꾸면 updated_at 이 그대로다. | backend/app/routers/tasks.py, frontend/src/components/TaskCard.tsx, PRD R-004 |
| 수정 | 제목과 설명만 바뀌고 상태는 그대로다. 값이 같으면 updated_at 도 그대로다. | backend/app/routers/tasks.py, backend/tests/test_tasks.py |
| 삭제 | 삭제 전 확인창이 뜬다. 이미 지운 카드를 다시 지우면 404 다. | frontend/src/components/TaskCard.tsx, backend/tests/test_tasks.py |
| 보드 | 칸반 보드 하나에 할 일 · 진행 중 · 완료 3열이 있다. 같은 열 안의 순서는 현재 id 오름차순이다. 이 순서는 "정렬" 결정 전까지의 현재 동작이며, 지켜야 할 규칙으로 정하지 않는다. | PRD R-005, backend/app/routers/tasks.py |
| 로그인과 소유 | 로그인하지 않으면 Task API 5개가 모두 401 이다. 남의 카드는 없는 카드와 똑같이 404 다. owner_id 는 요청 본문에서 받지 않고 응답에도 나가지 않는다. 한 사용자는 자기 카드만 본다. | backend/tests/test_tasks.py, PRD R-009 |
| 세션과 비밀번호 | 세션은 30분이다. 쿠키는 httponly 이고, 비밀번호는 Argon2 해시로만 저장한다. | backend/tests/test_auth.py |
| 기존 데이터 | 변경 전 기준선(tasks 3건, 모두 owner_id=1)이 변경 뒤에도 같은 id · 제목 · 상태 · owner_id 로 남는다. 새 값이 비어 있는 기존 카드에서도 화면과 API가 깨지지 않는다. | 변경 전 기준선 조회 결과 |
| API 요청 | 새 필드를 모르는 기존 요청이 그대로 동작한다. | 제안 |
