# BUG — 진행 중으로 옮긴 카드가 새로고침 뒤 할 일 열로 돌아감

발견 브랜치: practice/bug (연습용으로 화면 코드를 바꾼 브랜치. feature/m1-mvp와 main의 결함이 아님)

## 재현 순서
1. 할 일 열의 카드(예: 「테스트6」)에서 「진행 중」 버튼을 누른다. 카드가 진행 중 열로 옮겨진다.
2. F5로 새로고침한다.

## 기대 결과
SC-16: 새로고침 뒤에도 카드가 진행 중 열에 있고 할 일 열에는 없다. (USER-WORKFLOW S-03, R-008)

## 실제 결과
새로고침 뒤 카드가 할 일 열에 있고 진행 중 열은 「카드 없음」이다. F5 전에는 안내 문구 없이 카드가 진행 중 열에 있었다.

## 증거
캡처 두 장: F5 전(카드가 진행 중 열, 안내 문구 없음), F5 뒤(카드가 할 일 열).
Network 탭: PATCH /api/tasks/17 → 422 Unprocessable Entity
보낸 것: {"status": "IN_PROGRESS"}
돌아온 것: detail 항목 하나, type "missing", loc ["body", "title"], msg "Field required", input {"status": "IN_PROGRESS"}

## 영향 범위 (확인하지 않음)
같은 동작을 쓰는 SC-06, SC-17, SC-18도 같은 증상이 나올 가능성이 있다. 시험하지 않았다.
