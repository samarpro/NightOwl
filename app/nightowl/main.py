"""FastAPI application shell with routers and runtime services."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nightowl.api.routers.approvals import router as approvals_router
from nightowl.api.routers.health import router as health_router
from nightowl.api.routers.ingest import router as ingest_router
from nightowl.api.routers.observability import router as observability_router
from nightowl.api.routers.skills import router as skills_router
from nightowl.api.routers.webhooks import router as webhooks_router
from nightowl.api.routers.websocket import router as websocket_router
from nightowl.channels.base import ChannelRegistry
from nightowl.channels.telegram import TelegramBridge
from nightowl.channels.whatsapp import WhatsAppBridge
from nightowl.config import settings
from nightowl.db import close_db, init_db
from nightowl.events import RuntimeBroadcaster
from nightowl.hitl.gate import HITLGate
from nightowl.ingest.service import IngressService
from nightowl.observability.intent_graph import IntentGraphManager
from nightowl.observability.token_store import TokenStore
from nightowl.sandbox.manager import DockerSandboxManager
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.runner import run_child_session
from nightowl.sessions.store import SessionStore
from nightowl.skills.loader import load_builtin_skills
from nightowl.skills.store import SkillStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s [%(levelname)s] %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)

    session_factory = await init_db()
    store = SessionStore(session_factory)
    broadcaster = RuntimeBroadcaster()
    manager = SessionManager()
    manager.set_event_bus(broadcaster)
    manager.set_child_runner(run_child_session)
    manager.store = store

    registry = ChannelRegistry()
    if settings.telegram_bot_token:
        registry.register(TelegramBridge())
    if settings.twilio_account_sid and settings.twilio_auth_token:
        registry.register(WhatsAppBridge())

    gate = HITLGate(manager=manager, event_bus=broadcaster, registry=registry)
    manager.hitl_gate = gate
    manager.channel_registry = registry
    manager.sandbox_manager = DockerSandboxManager()
    manager.skill_store = SkillStore(session_factory)

    token_store = TokenStore()
    intent_graph = IntentGraphManager(token_store, event_bus=broadcaster)
    manager.token_store = token_store
    manager.intent_graph = intent_graph

    await load_builtin_skills(manager.skill_store)
    ingress_service = IngressService(manager=manager, registry=registry)

    # Resume active session from DB if one exists
    result = await manager.load_and_resume()
    if result:
        session, messages = result
        ingress_service.set_resumed_session(session.id, messages)

    app.state.session_factory = session_factory
    app.state.broadcaster = broadcaster
    app.state.manager = manager
    app.state.hitl_gate = gate
    app.state.channel_registry = registry
    app.state.skill_store = manager.skill_store
    app.state.token_store = token_store
    app.state.intent_graph = intent_graph
    app.state.ingress_service = ingress_service

    yield

    await manager.sandbox_manager.cleanup_all()
    await ingress_service.shutdown()
    await close_db()


def create_app() -> FastAPI:
    application = FastAPI(title="NightOwl", version="0.1.0", lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(ingest_router)
    application.include_router(approvals_router)
    application.include_router(observability_router)
    application.include_router(skills_router)
    application.include_router(webhooks_router)
    application.include_router(websocket_router)
    return application


app = create_app()
