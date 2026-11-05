import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))                     # backend/ 를 import 경로에

from fastapi.staticfiles import StaticFiles
from app.main import app as taskflow                         # 어제까지의 FastAPI 앱 그대로

app = taskflow                                               # 안쪽 앱을 그대로 쓴다 (/api/… 와 /health 는 이미 있음)
app.mount("/", StaticFiles(directory=ROOT / "frontend" / "dist", html=True))   # 그 밖 → 화면