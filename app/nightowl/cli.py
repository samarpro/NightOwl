"""Slim CLI chat — thin wrapper around the session runner."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nightowl.events import EventBus
from nightowl.hitl.gate import HITLGate
from nightowl.models.approval import ApprovalDecision
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
                None, lambda: input("  decision? (a=approve, r=reject, d=redirect): ").strip()
            )
            normalized = answer.lower()
            if normalized in ("a", "approve", "y", "yes"):
                decision = ApprovalDecision.APPROVE
                reason = "CLI user approved"
                redirect_message = None
            elif normalized in ("d", "redirect"):
                redirect_message = await loop.run_in_executor(
                    None, lambda: input("  redirect instruction: ").strip()
                )
                decision = ApprovalDecision.REDIRECT
                reason = "CLI user redirected"
            else:
                decision = ApprovalDecision.REJECT
                reason = "CLI user denied"
                redirect_message = None
        except (EOFError, KeyboardInterrupt):
            decision = ApprovalDecision.REJECT
            reason = "CLI user denied"
            redirect_message = None

        gate.resolve_approval(
            approval_id,
            decision=decision,
            reason=reason,
            redirect_message=redirect_message,
        )
        status = decision.value.upper()
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
