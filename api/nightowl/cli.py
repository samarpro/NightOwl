"""Slim CLI chat for iterative testing — bypasses HTTP, talks directly to the engine."""

from __future__ import annotations

import asyncio
import sys

from nightowl.sessions.manager import SessionManager
from nightowl.sessions.runner import run_session


async def main() -> None:
    manager = SessionManager()
    print("NightOwl CLI — type your message, press Enter to send. Ctrl+C to quit.\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue

        session = await manager.create_main_session(user_input)
        print(f"[session {session.id}]\n")

        try:
            response = await run_session(session, manager, user_input)
        except Exception as e:
            print(f"[error] {e}\n")
            continue

        print(f"nightowl> {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
