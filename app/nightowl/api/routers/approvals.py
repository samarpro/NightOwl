"""Approval resolution routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from nightowl.models.approval import ApprovalResponse

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


@router.post("/respond")
async def respond_to_approval(response: ApprovalResponse, request: Request) -> dict[str, object]:
    request.app.state.hitl_gate.resolve_approval(
        response.approval_id,
        approved=response.approved,
        reason=response.reason,
    )
    return {"status": "ok"}
