# Task Flow

할 일을 카드로 등록하고 칸반 보드에서 상태를 보는 개인용 Task 관리 웹 앱. 설계는 PRD.md · ARCHITECTURE.md · DECISIONS.md 참고.

현재는 M0(기본 구조)까지만 있다. 카드 기능 · 데이터베이스 · 로그인은 아직 없다.

## 필요한 도구

- uv (Python 3.12 는 `backend/.python-version` 으로 고정)
- Node.js + npm

## 실행 (잠정 절차)

터미널 두 개를 연다.

```
# 1) API — http://127.0.0.1:8000
cd backend
uv run uvicorn app.main:app --reload

# 2) 화면 — http://localhost:5173
cd frontend
npm install   # 처음 한 번
npm run dev
```

브라우저에서 http://localhost:5173 을 열면 "API 연결: 정상" 이 보인다.
