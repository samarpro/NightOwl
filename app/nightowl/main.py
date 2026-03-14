"""FastAPI application shell with lifespan context manager."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nightowl.config import settings
from nightowl.db import close_db, init_db
from nightowl.sessions.manager import SessionManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[dict[str, Any]]:
    # Startup
    session_factory = await init_db()
    manager = SessionManager()
    broadcast: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    manager.set_broadcast_queue(broadcast)

    yield {
        "session_factory": session_factory,
        "manager": manager,
        "broadcast": broadcast,
    }

    # Shutdown
    await close_db()


app = FastAPI(title="NightOwl", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
