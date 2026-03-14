"""FastAPI application shell with routers and runtime services."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nightowl.api.routers.approvals import router as approvals_router
from nightowl.api.routers.health import router as health_router
from nightowl.api.routers.ingest import router as ingest_router
from nightowl.api.routers.websocket import router as websocket_router
from nightowl.channels.outbound import ChannelDeliveryService
from nightowl.channels.registry import ChannelRegistry
from nightowl.channels.session_routing import ChannelSessionRouter
from nightowl.channels.telegram.outbound import TelegramOutbound
from nightowl.channels.telegram.router import router as telegram_router
from nightowl.config import settings
from nightowl.db import close_db, init_db
from nightowl.events import RuntimeBroadcaster
from nightowl.hitl.gate import HITLGate
from nightowl.ingest.service import IngressService
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.runner import run_child_session


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    session_factory = await init_db()
    broadcaster = RuntimeBroadcaster()
    manager = SessionManager()
    manager.set_event_bus(broadcaster)
    manager.set_child_runner(run_child_session)

    routing = ChannelSessionRouter()
    registry = ChannelRegistry()
    registry.register_outbound("telegram", TelegramOutbound())
    delivery = ChannelDeliveryService(routing, registry, manager._emit)
    gate = HITLGate(manager=manager, event_bus=broadcaster, outbound_service=delivery)
    manager.hitl_gate = gate
    ingress_service = IngressService(manager=manager, routing=routing, delivery=delivery)

    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.broadcaster = broadcaster
    app.state.manager = manager
    app.state.hitl_gate = gate
    app.state.routing = routing
    app.state.channel_registry = registry
    app.state.delivery_service = delivery
    app.state.ingress_service = ingress_service

    yield

    await ingress_service.shutdown()
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(title="NightOwl", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(ingest_router)
    app.include_router(approvals_router)
    app.include_router(websocket_router)
    app.include_router(telegram_router)
    return app


app = create_app()
