"""Slim CLI chat — thin wrapper around the session runner."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nightowl.hitl.gate import HITLGate
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.runner import run_child_session, run_interactive


async def _async_input(prompt: str) -> str | None:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, lambda: input(prompt))
    except (EOFError, KeyboardInterrupt):
        return None


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    manager = SessionManager()
    manager.set_child_runner(run_child_session)

    broadcast: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    manager.set_broadcast_queue(broadcast)
    gate = HITLGate(manager=manager, broadcast_queue=broadcast)

    print("NightOwl CLI — one session, persistent context. Ctrl+C to quit.\n")

    await run_interactive(
        manager=manager,
        get_input=lambda: _async_input("you> "),
        put_output=lambda text: _print_output(text),
    )

    print("\nBye.")


async def _print_output(text: str) -> None:
    print(f"nightowl> {text}\n")


if __name__ == "__main__":
    asyncio.run(main())
