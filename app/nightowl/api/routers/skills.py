"""Skills CRUD API — upload, list, read, delete, toggle skills."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile
from pydantic import BaseModel

from nightowl.skills.parser import parse_skill_md

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


class SkillToggle(BaseModel):
    enabled: bool


@router.get("/")
async def list_skills(request: Request) -> list[dict[str, Any]]:
    store = request.app.state.skill_store
    return await store.list_skills(enabled_only=False)


@router.get("/{name}")
async def get_skill(name: str, request: Request) -> dict[str, Any]:
    store = request.app.state.skill_store
    skill = await store.load_skill(name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return skill


@router.post("/upload")
async def upload_skill(file: UploadFile, request: Request) -> dict[str, Any]:
    """Upload a SKILL.md file."""
    content = (await file.read()).decode("utf-8")
    try:
        parsed = parse_skill_md(content, source="upload")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    store = request.app.state.skill_store
    skill_id = await store.save_skill(parsed)
    return {"id": skill_id, "name": parsed.name, "status": "saved"}


@router.post("/")
async def create_skill(request: Request) -> dict[str, Any]:
    """Create or update a skill from raw SKILL.md content in the request body."""
    body = await request.json()
    content = body.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="Missing 'content' field")
    source = body.get("source", "api")

    try:
        parsed = parse_skill_md(content, source=source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    store = request.app.state.skill_store
    skill_id = await store.save_skill(parsed)
    return {"id": skill_id, "name": parsed.name, "status": "saved"}


@router.delete("/{name}")
async def delete_skill(name: str, request: Request) -> dict[str, str]:
    store = request.app.state.skill_store
    deleted = await store.delete_skill(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return {"status": "deleted", "name": name}


@router.patch("/{name}/toggle")
async def toggle_skill(name: str, body: SkillToggle, request: Request) -> dict[str, Any]:
    store = request.app.state.skill_store
    found = await store.toggle_skill(name, body.enabled)
    if not found:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return {"name": name, "enabled": body.enabled}
