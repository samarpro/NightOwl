"""Sessions query API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("/")
async def list_sessions(
    request: Request, parent_id: str | None = Query(default=None, alias="parentId"),
) -> list[dict[str, Any]]:
    store = request.app.state.manager.store
    if parent_id is None:
        return await store.list_root_sessions()
    return await store.list_child_sessions(parent_id)
