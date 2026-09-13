"""Intent classifier — chunks token streams and classifies into intent nodes.

Runs as a background processor. Takes token entries from the token store,
groups them by tool-call boundaries, and calls Haiku to classify each chunk
into a structured intent node.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider

from nightowl.config import bedrock_provider, settings
from nightowl.models.observability import IntentEdge, IntentNode
from nightowl.observability.token_store import TokenEntry, TokenType

log = logging.getLogger(__name__)

_HAIKU_MODEL = "au.anthropic.claude-haiku-4-5-20251001-v1:0"

_CLASSIFIER_PROMPT = """\
You are an intent classifier for an AI agent's activity stream.
Given a sequence of agent actions (thinking, tool calls, responses),
classify the overall intent into a structured node.

Respond with:
- service: the external service or system involved (e.g. "gmail", "calendar", "web-search", "internal")
- intent: what the agent is trying to accomplish (e.g. "fetch-emails", "check-availability", "search-restaurants")
- status: "in_progress", "completed", "failed", or "waiting"
- summary: one-sentence description of what happened"""


class ClassifiedIntent(BaseModel):
    service: str
    intent: str
    status: str
    summary: str


def chunk_tokens(entries: list[TokenEntry]) -> list[list[TokenEntry]]:
    """Split token entries into chunks at tool-call boundaries.

    Each chunk represents one logical unit of work:
    thinking → tool_call → tool_result → response.
    """
    if not entries:
        return []

    chunks: list[list[TokenEntry]] = []
    current: list[TokenEntry] = []

    for entry in entries:
        if entry.token_type == TokenType.THINKING and current:
            # New thinking starts a new chunk
            chunks.append(current)
            current = []
        current.append(entry)

    if current:
        chunks.append(current)
    return chunks


def _format_chunk(chunk: list[TokenEntry]) -> str:
    lines = []
    for e in chunk:
        if e.token_type == TokenType.THINKING:
            lines.append(f"[THINKING] {e.content[:500]}")
        elif e.token_type == TokenType.TOOL_CALL:
            args = e.metadata.get("args", "")[:400]
            lines.append(f"[TOOL CALL] {e.content}({args})")
        elif e.token_type == TokenType.TOOL_RESULT:
            lines.append(f"[TOOL RESULT] {e.content[:500]}")
        elif e.token_type == TokenType.RESPONSE:
            lines.append(f"[RESPONSE] {e.content[:600]}")
        elif e.token_type == TokenType.SPAWN:
            lines.append(f"[SPAWN] {e.content}")
        elif e.token_type == TokenType.COMPLETION:
            lines.append(f"[COMPLETION] {e.content[:400]}")
    return "\n".join(lines)


async def classify_chunk(chunk: list[TokenEntry]) -> ClassifiedIntent:
    """Classify a chunk of token entries into a structured intent."""
    text = _format_chunk(chunk)

    try:
        model = BedrockConverseModel(model_name=_HAIKU_MODEL, provider=bedrock_provider())
        agent: Agent[None, ClassifiedIntent] = Agent(
            model=model,
            system_prompt=_CLASSIFIER_PROMPT,
            output_type=ClassifiedIntent,
        )
        result = await agent.run(text)
        return result.output
    except Exception:
        log.exception("Intent classification failed, using fallback")
        # Fallback: derive intent from tool names in the chunk
        tools = [e.content for e in chunk if e.token_type == TokenType.TOOL_CALL]
        service = tools[0].split("_")[0].lower() if tools else "internal"
        intent = tools[0] if tools else "processing"
        return ClassifiedIntent(
            service=service,
            intent=intent,
            status="completed",
            summary=f"Agent executed {', '.join(tools) or 'internal processing'}",
        )


def intent_to_node(
    session_id: str,
    chunk_index: int,
    classified: ClassifiedIntent,
    token_start: int,
    token_end: int,
    started_at: float,
    ended_at: float,
) -> IntentNode:
    """Convert a classified intent into an IntentNode."""
    return IntentNode(
        id=f"{session_id}:intent:{chunk_index}",
        label=f"{classified.service}/{classified.intent}",
        type=classified.status,
        service=classified.service,
        intent=classified.intent,
        summary=classified.summary,
        token_start=token_start,
        token_end=token_end,
        started_at=started_at,
        ended_at=ended_at,
    )


def build_edges(
    session_id: str, nodes: list[IntentNode],
) -> list[IntentEdge]:
    """Build sequential edges between intent nodes."""
    edges = []
    for i in range(len(nodes) - 1):
        edges.append(IntentEdge(
            source=nodes[i].id,
            target=nodes[i + 1].id,
            label="then",
        ))
    return edges
