"""Intent graph builder — maintains live intent graph per session.

Processes token entries into classified intent nodes, builds the graph,
and broadcasts updates via the event bus for the dashboard.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nightowl.models.observability import IntentEdge, IntentGraph, IntentNode
from nightowl.observability.intent_classifier import (
    build_edges,
    chunk_tokens,
    classify_chunk,
    intent_to_node,
)
from nightowl.observability.token_store import TokenStore

log = logging.getLogger(__name__)


class IntentGraphManager:
    """Manages live intent graphs for all sessions."""

    def __init__(self, token_store: TokenStore, event_bus: Any = None) -> None:
        self._token_store = token_store
        self._event_bus = event_bus
        self._graphs: dict[str, IntentGraph] = {}
        self._processed_counts: dict[str, int] = {}  # how many tokens we've classified
        self._background_tasks: set[asyncio.Task] = set()

    def get_graph(self, session_id: str) -> IntentGraph:
        return self._graphs.get(session_id, IntentGraph())

    def get_all_graphs(self) -> dict[str, IntentGraph]:
        return dict(self._graphs)

    async def process_session(self, session_id: str) -> IntentGraph:
        """Process new tokens for a session and update its intent graph.

        Only classifies tokens added since last processing.
        """
        entries = self._token_store.get_session(session_id)
        processed = self._processed_counts.get(session_id, 0)

        if len(entries) <= processed:
            return self.get_graph(session_id)

        new_entries = entries[processed:]
        self._processed_counts[session_id] = len(entries)

        chunks = chunk_tokens(new_entries)
        if not chunks:
            return self.get_graph(session_id)

        graph = self._graphs.get(session_id, IntentGraph())
        existing_node_count = len(graph.nodes)

        for i, chunk in enumerate(chunks):
            classified = await classify_chunk(chunk)
            node = intent_to_node(session_id, existing_node_count + i, classified)
            graph.nodes.append(node)

        # Rebuild edges for the full graph
        graph.edges = build_edges(session_id, graph.nodes)
        self._graphs[session_id] = graph

        # Broadcast update
        await self._broadcast(session_id, graph)

        log.debug(
            "Intent graph for %s: %d nodes, %d edges",
            session_id, len(graph.nodes), len(graph.edges),
        )
        return graph

    async def _broadcast(self, session_id: str, graph: IntentGraph) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish({
            "type": "intent:update",
            "session_id": session_id,
            "graph": graph.model_dump(),
        })

    def schedule_processing(self, session_id: str) -> None:
        """Schedule background intent processing for a session.

        Called after each agent turn — debounces naturally since
        we only process new tokens.
        """
        task = asyncio.create_task(
            self._safe_process(session_id),
            name=f"intent:{session_id}",
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _safe_process(self, session_id: str) -> None:
        try:
            await self.process_session(session_id)
        except Exception:
            log.exception("Intent processing failed for %s", session_id)

    def clear_session(self, session_id: str) -> None:
        self._graphs.pop(session_id, None)
        self._processed_counts.pop(session_id, None)
