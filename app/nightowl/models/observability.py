"""Observability models for the intent graph and agent cards."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentCard(BaseModel):
    session_id: str
    role: str
    label: str | None = None
    task: str = ""
    state: str = "pending"
    depth: int = 0
    children: list[str] = Field(default_factory=list)


class IntentNode(BaseModel):
    id: str
    label: str
    type: str = "session"
    service: str = ""
    intent: str = ""
    summary: str = ""
    token_start: int = 0
    token_end: int = 0
    started_at: float = 0.0
    ended_at: float = 0.0


class IntentEdge(BaseModel):
    source: str
    target: str
    label: str = ""


class IntentGraph(BaseModel):
    nodes: list[IntentNode] = Field(default_factory=list)
    edges: list[IntentEdge] = Field(default_factory=list)
