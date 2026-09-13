"""Context compaction — proactive summarization when history approaches the context window.

Uses a history_processor hook that PydanticAI calls before every model request.
When estimated tokens exceed 75% of the context window, old messages are
summarized by a dedicated agent and replaced with a compact summary.

Also provides tool result truncation to prevent single responses from blowing
up the context (e.g. a full Gmail inbox dump).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Sequence

from pydantic_ai import Agent, ModelHTTPError, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from nightowl.config import settings

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONTEXT_WINDOW = 200_000  # Haiku / Sonnet default
COMPACTION_TRIGGER_RATIO = 0.75
COMPACTION_TARGET_RATIO = 0.35
CHARS_PER_TOKEN = 4
MIN_MESSAGES_TO_COMPACT = 8
MAX_TOOL_RESULT_CHARS = 20_000  # truncate individual tool results beyond this

# ---------------------------------------------------------------------------
# Summarizer prompt
# ---------------------------------------------------------------------------

SUMMARIZER_SYSTEM_PROMPT = """\
You are a context compaction agent. Produce a faithful, dense summary of a conversation between a user and an AI agent.

RULES:
1. Preserve ALL factual information: data values, query results, API responses, error messages.
2. Preserve the user's original intent, instructions, and constraints verbatim where possible.
3. Preserve every decision the agent made and why.
4. Preserve tool names called and their key results. Omit raw payloads but keep essential data.
5. Preserve any pending tasks or next steps.
6. Use structured format:
   - USER INTENT: What the user asked for
   - COMPLETED WORK: What was accomplished (with key data)
   - KEY FINDINGS: Important data points, results, patterns
   - PENDING: What still needs to be done
   - CONTEXT: Any other critical context
7. Be dense but complete. Err on the side of including too much.
8. Do NOT add commentary beyond what was in the original conversation.
9. Do NOT fabricate information."""

# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------


def estimate_tokens(messages: Sequence[ModelMessage]) -> int:
    total_chars = 0
    for message in messages:
        for part in message.parts:
            if isinstance(part, UserPromptPart):
                if isinstance(part.content, str):
                    total_chars += len(part.content)
                else:
                    total_chars += sum(len(str(item)) for item in part.content)
            elif isinstance(part, TextPart):
                total_chars += len(part.content)
            elif isinstance(part, ToolCallPart):
                total_chars += len(part.tool_name) + len(part.args_as_json_str())
            elif isinstance(part, ToolReturnPart):
                total_chars += len(str(part.content))
            elif isinstance(part, RetryPromptPart):
                total_chars += len(str(part.content))
            else:
                total_chars += len(str(part))
    return total_chars // CHARS_PER_TOKEN


# ---------------------------------------------------------------------------
# Safe split point
# ---------------------------------------------------------------------------


def find_safe_split_point(messages: Sequence[ModelMessage], target_index: int) -> int:
    """Walk backwards from target_index to avoid orphaning tool-call/return pairs."""
    idx = target_index
    while idx > 0:
        msg = messages[idx]
        if isinstance(msg, ModelRequest) and any(
            isinstance(p, ToolReturnPart) for p in msg.parts
        ):
            idx -= 1
            continue
        return idx
    return 0


def split_messages(
    messages: Sequence[ModelMessage],
    context_window: int = CONTEXT_WINDOW,
    target_ratio: float = COMPACTION_TARGET_RATIO,
) -> tuple[list[ModelMessage], list[ModelMessage]]:
    """Split into (old_to_summarise, recent_to_keep)."""
    if len(messages) <= MIN_MESSAGES_TO_COMPACT:
        return [], list(messages)

    token_budget = int(target_ratio * context_window)
    accumulated = 0
    count_recent = 0

    for i in range(len(messages) - 1, -1, -1):
        msg_tokens = estimate_tokens([messages[i]])
        if accumulated + msg_tokens > token_budget:
            break
        accumulated += msg_tokens
        count_recent += 1

    raw_split = len(messages) - count_recent
    if raw_split <= 0:
        return [], list(messages)

    safe_split = find_safe_split_point(messages, raw_split)
    if safe_split == 0:
        return [], list(messages)

    return list(messages[:safe_split]), list(messages[safe_split:])


# ---------------------------------------------------------------------------
# Summarize
# ---------------------------------------------------------------------------


def _extract_text(messages: Sequence[ModelMessage]) -> str:
    snippets: list[str] = []
    for message in messages:
        for part in message.parts:
            if isinstance(part, UserPromptPart):
                content = part.content if isinstance(part.content, str) else str(part.content)
                snippets.append(f"[User]: {content[:500]}")
            elif isinstance(part, TextPart):
                snippets.append(f"[Assistant]: {part.content[:500]}")
            elif isinstance(part, ToolCallPart):
                snippets.append(f"[ToolCall]: {part.tool_name}({part.args_as_json_str()[:300]})")
            elif isinstance(part, ToolReturnPart):
                snippets.append(f"[ToolReturn:{part.tool_name}]: {str(part.content)[:300]}")
    return "\n".join(snippets[-50:])


async def summarise_messages(messages: Sequence[ModelMessage]) -> list[ModelMessage]:
    """Summarise old messages into a compact 2-message history pair."""
    from pydantic_ai.models.bedrock import BedrockConverseModel
    from nightowl.config import bedrock_provider

    text_repr = _extract_text(messages)

    model = BedrockConverseModel(model_name=settings.bedrock_model, provider=bedrock_provider())
    summarizer: Agent[None, str] = Agent(
        model=model,
        system_prompt=SUMMARIZER_SYSTEM_PROMPT,
    )
    result = await summarizer.run(text_repr)

    return [
        ModelRequest(parts=[UserPromptPart(content=f"[CONTEXT SUMMARY]\n\n{result.output}")]),
        ModelResponse(
            parts=[TextPart(content="Understood. I have the prior context and will continue.")],
            model_name="context-compactor",
        ),
    ]


# ---------------------------------------------------------------------------
# History processor (proactive compaction hook)
# ---------------------------------------------------------------------------


def create_compaction_processor(context_window: int = CONTEXT_WINDOW):
    """Factory returning a PydanticAI history_processor for proactive compaction."""
    trigger_threshold = int(context_window * COMPACTION_TRIGGER_RATIO)

    async def compact_history(
        ctx: RunContext[Any], messages: list[ModelMessage],
    ) -> list[ModelMessage]:
        # Always truncate oversized tool results
        truncate_tool_results(messages)

        if len(messages) < MIN_MESSAGES_TO_COMPACT:
            return messages

        estimated = estimate_tokens(messages)
        if estimated < trigger_threshold:
            return messages

        log.warning(
            "Context compaction triggered: ~%d tokens (threshold: %d)",
            estimated, trigger_threshold,
        )

        old, recent = split_messages(messages, context_window)
        if not old:
            return messages

        try:
            summary = await summarise_messages(old)
            compacted = summary + recent
            log.info(
                "Compaction: %d -> ~%d tokens (%d -> %d messages)",
                estimated, estimate_tokens(compacted), len(messages), len(compacted),
            )
            return compacted
        except Exception:
            log.exception("Compaction failed, returning original messages")
            return messages

    return compact_history


# ---------------------------------------------------------------------------
# Tool result truncation (applied to ToolReturnPart content)
# ---------------------------------------------------------------------------


def truncate_tool_results(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Truncate oversized tool return content in-place."""
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if not isinstance(part, ToolReturnPart):
                continue
            content_str = str(part.content)
            if len(content_str) > MAX_TOOL_RESULT_CHARS:
                truncated = content_str[:MAX_TOOL_RESULT_CHARS]
                part.content = f"{truncated}\n\n[TRUNCATED — original was {len(content_str)} chars]"
                log.debug("Truncated tool result for %s: %d -> %d chars",
                         part.tool_name, len(content_str), MAX_TOOL_RESULT_CHARS)
    return messages


# ---------------------------------------------------------------------------
# Context overflow error detection (reactive path)
# ---------------------------------------------------------------------------

_CONTEXT_ERROR_PATTERNS = [
    "context length", "too many tokens", "token limit", "prompt is too long",
    r"maximum.*length", r"exceeds.*maximum", "too many input tokens",
    "content_too_large", "request_too_large", "context window",
]


def is_context_overflow(exc: Exception) -> bool:
    if not isinstance(exc, ModelHTTPError):
        return False
    if exc.status_code not in (400, 413):
        return False
    text = f"{exc.body} {exc}".lower()
    return any(re.search(p, text) for p in _CONTEXT_ERROR_PATTERNS)
