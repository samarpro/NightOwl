"""Session-related data models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SessionRole(StrEnum):
    MAIN = "main"
    ORCHESTRATOR = "orchestrator"
    LEAF = "leaf"


class SessionState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class SandboxMode(StrEnum):
    NONE = "none"
    CLI = "cli"
    BROWSER = "browser"
    COMPUTER = "computer"


class SpawnRequest(BaseModel):
    task: str
    label: str | None = None
    sandbox: SandboxMode = SandboxMode.NONE
    model: str | None = None


class Session(BaseModel):
    id: str
    parent_id: str | None = None
    role: SessionRole = SessionRole.MAIN
    state: SessionState = SessionState.PENDING
    depth: int = 0
    task: str = ""
    label: str | None = None
    sandbox_mode: SandboxMode | None = None
    model_override: str | None = None
    children: list[str] = Field(default_factory=list)
    expected_completions: set[str] = Field(default_factory=set)
    result: str | None = None


class TaskCompletionEvent(BaseModel):
    child_session_id: str
    parent_session_id: str
    result: str
    success: bool = True
