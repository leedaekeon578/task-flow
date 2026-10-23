from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import load_env_file, load_session_secret
from .db import check_schema
from .routers import auth, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_env_file()
    app.state.session_secret = load_session_secret()
    check_schema()
    yield


app = FastAPI(title="Task Flow API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
