"""Prompts API — get and update agent prompts."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


class PromptUpdate(BaseModel):
    main: str | None = None
    orchestrator: str | None = None
    leaf: str | None = None


_prompts: dict[str, str] = {
    "main": "",
    "orchestrator": "",
    "leaf": "",
}


def get_prompt(role: str) -> str:
    return _prompts.get(role, "")


def set_prompt(role: str, value: str) -> None:
    _prompts[role] = value


@router.get("/")
async def get_prompts() -> dict[str, str]:
    return {
        "main": _prompts.get("main", ""),
        "orchestrator": _prompts.get("orchestrator", ""),
        "leaf": _prompts.get("leaf", ""),
    }


@router.post("/")
async def update_prompts(update: PromptUpdate) -> dict[str, str]:
    if update.main is not None:
        _prompts["main"] = update.main
    if update.orchestrator is not None:
        _prompts["orchestrator"] = update.orchestrator
    if update.leaf is not None:
        _prompts["leaf"] = update.leaf
    return {
        "main": _prompts.get("main", ""),
        "orchestrator": _prompts.get("orchestrator", ""),
        "leaf": _prompts.get("leaf", ""),
    }
