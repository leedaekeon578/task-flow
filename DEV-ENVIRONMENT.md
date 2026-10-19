# DEV-ENVIRONMENT — Task Flow

확인일: 2026-10-19. 아래 결과는 이 컴퓨터에서 명령을 실행해 얻은 출력이다.

## 운영체제 · 셸

| 항목 | 값 |
|------|----|
| 운영체제 | Microsoft Windows 11 Pro |
| 버전 | 10.0.22631 |
| 아키텍처 | 64비트 |
| 셸 | PowerShell 7.6.6 |

## 도구별 버전

각 명령의 `--version` 결과를 그대로 적었다.

| 도구 | 명령 | 결과 |
|------|------|------|
| git | `git --version` | `git version 2.56.0.windows.2` |
| node | `node --version` | 처음에는 실행 안 됨. M0 에서 설치 후 `v24.22.0` |
| npm | `npm --version` | 처음에는 실행 안 됨. M0 에서 설치 후 `11.19.1` |
| uv | `uv --version` | `uv 0.13.1 (62faed335 2026-10-13 x86_64-pc-windows-msvc)` |
| python | `python --version` | 버전이 나오지 않고 `Python` 한 단어만 출력됨 |

### python 참고

- `python` 명령은 WindowsApps 의 Microsoft Store 연결용 실행 파일(C:\Users\EZ\AppData\Local\Microsoft\WindowsApps\python.exe)을 가리키는 것으로 보인다. 이 프로젝트는 시스템 python 을 쓰지 않는다.
- 프로젝트가 쓰는 Python 은 uv 가 관리한다. `uv python list --only-installed` 결과:

```
cpython-3.15.0-windows-x86_64-none     C:\Users\EZ\AppData\Roaming\uv\python\cpython-3.15.0-windows-x86_64-none\python.exe
cpython-3.15.0-windows-x86_64-none     C:\Users\EZ\.local\bin\python3.15.exe
cpython-3.15.0-windows-x86_64-none     C:\Users\EZ\AppData\Roaming\uv\python\cpython-3.15-windows-x86_64-none\python.exe
cpython-3.12.15-windows-x86_64-none    C:\Users\EZ\AppData\Roaming\uv\python\cpython-3.12.15-windows-x86_64-none\python.exe
cpython-3.12.15-windows-x86_64-none    C:\Users\EZ\.local\bin\python3.12.exe
cpython-3.12.15-windows-x86_64-none    C:\Users\EZ\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe
```

- 사용자가 직접 확인한 결과: task-flow 폴더에서 `uv run python --version` 은 Python 3.15.0 이 나왔다. 버전을 고정하지 않아 uv 가 가장 새 버전을 골랐다.
- 쓰는 버전은 Python 3.12 이다. M0 에서 backend 폴더에 고정했다.

## 새로 설치한 것 (M0, 2026-10-19)

- Node.js v24.22.0 (LTS), npm 11.19.1. 설치 위치: `%LOCALAPPDATA%\Programs\nodejs`, 사용자 PATH 에 추가. 새 터미널부터 `node` 가 잡힌다.
  - winget 은 이 컴퓨터에서 비정상 종료(0xC0000005)했고, MSI 는 관리자 권한이 없어 실패(1603)했다. nodejs.org 의 공식 zip 을 SHA256 확인 후 풀었다.
- backend: `uv python pin 3.12` 로 `backend/.python-version` 고정 (`uv run python --version` → 3.12.15). fastapi 0.146.0, uvicorn 0.54.0 (`backend/pyproject.toml`).
- frontend: Vite + React + TypeScript (`frontend/package.json`).

## 아직 없는 것

없음. (M0 범위의 환경은 모두 갖췄다.)
