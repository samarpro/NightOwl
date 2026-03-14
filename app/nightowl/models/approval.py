"""Approval and risk models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REDIRECT = "redirect"


class ToolCallWithRisk(BaseModel):
    tool_name: str
    tool_args: dict[str, Any] = {}
    risk_level: RiskLevel = RiskLevel.LOW


class ApprovalRequest(BaseModel):
    id: str
    session_id: str
    tool_name: str
    tool_args: dict[str, Any] = {}
    risk_level: RiskLevel
    status: str = "pending"


class ApprovalResponse(BaseModel):
    approval_id: str
    decision: ApprovalDecision
    reason: str | None = None
    redirect_message: str | None = None


class ApprovalResult(BaseModel):
    decision: ApprovalDecision
    reason: str | None = None
    redirect_message: str | None = None
