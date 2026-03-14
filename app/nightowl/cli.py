"""Slim CLI chat — thin wrapper around the session runner."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nightowl.events import EventBus
from nightowl.hitl.gate import HITLGate
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.runner import run_child_session, run_interactive


async def _async_input(prompt: str) -> str | None:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, lambda: input(prompt))
    except (EOFError, KeyboardInterrupt):
        return None


async def _print_output(text: str) -> None:
    print(f"nightowl> {text}\n")


async def _print_event(event: dict[str, Any]) -> None:
    etype = event.get("type", "")
    if etype == "node:tool_call":
        tools = ", ".join(event.get("tools", []))
        print(f"  [{tools}]")
    elif etype == "child_completion":
        print("  [child completion received]")


async def _approval_listener(bus: EventBus, gate: HITLGate) -> None:
    """Background task: subscribes to approval events on Redis, prompts user inline."""
    loop = asyncio.get_running_loop()
    async for event in bus.subscribe(types={"approval:required"}):
        approval_id = event["approval_id"]
        tool_name = event.get("tool_name", "unknown")
        tool_args = event.get("tool_args", {})
        risk_level = event.get("risk_level", "unknown")

        print(f"\n  [APPROVAL REQUIRED] {tool_name} (risk: {risk_level})")
        print(f"  args: {tool_args}")

        try:
            answer = await loop.run_in_executor(
                None, lambda: input("  approve? (y/n): ").strip().lower()
            )
            approved = answer in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            approved = False

        reason = "CLI user approved" if approved else "CLI user denied"
        gate.resolve_approval(approval_id, approved=approved, reason=reason)
        status = "APPROVED" if approved else "DENIED"
        print(f"  [{status}]\n")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    bus = EventBus()
    await bus.connect()

    manager = SessionManager()
    manager.set_event_bus(bus)
    manager.set_child_runner(run_child_session)

    gate = HITLGate(manager=manager, event_bus=bus)
    manager.hitl_gate = gate

    # Start approval listener in background
    listener = asyncio.create_task(_approval_listener(bus, gate))

    print("NightOwl CLI — one session, persistent context. Ctrl+C to quit.\n")

    await run_interactive(
        manager=manager,
        get_input=lambda: _async_input("you> "),
        put_output=_print_output,
        on_event=_print_event,
    )

    listener.cancel()
    await bus.close()
    print("\nBye.")


if __name__ == "__main__":
    asyncio.run(main())
