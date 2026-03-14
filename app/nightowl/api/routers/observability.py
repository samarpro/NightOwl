"""Observability API — intent graphs and token streams."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/observability", tags=["observability"])


@router.get("/intent-graph/{session_id}")
async def get_intent_graph(session_id: str, request: Request) -> dict[str, Any]:
    intent_graph = request.app.state.intent_graph
    graph = intent_graph.get_graph(session_id)
    return graph.model_dump()


@router.get("/intent-graphs")
async def get_all_intent_graphs(request: Request) -> dict[str, Any]:
    intent_graph = request.app.state.intent_graph
    return {sid: g.model_dump() for sid, g in intent_graph.get_all_graphs().items()}


@router.get("/tokens/{session_id}")
async def get_tokens(session_id: str, request: Request, last: int = 20) -> list[dict[str, Any]]:
    token_store = request.app.state.token_store
    entries = token_store.get_latest(session_id, n=last)
    return [
        {
            "type": e.token_type.value,
            "content": e.content,
            "metadata": e.metadata,
            "timestamp": e.timestamp,
        }
        for e in entries
    ]


@router.post("/intent-graph/{session_id}/process")
async def process_intent_graph(session_id: str, request: Request) -> dict[str, Any]:
    """Manually trigger intent processing for a session."""
    intent_graph = request.app.state.intent_graph
    graph = await intent_graph.process_session(session_id)
    return graph.model_dump()
