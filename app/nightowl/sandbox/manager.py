"""DockerSandboxManager — lifecycle management for ephemeral per-session Docker containers.

Handles create, exec, cleanup, and file extraction. Each sandbox mode
(CLI, BROWSER, COMPUTER) maps to a distinct Docker image with appropriate
tooling pre-installed.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import docker

from nightowl.models.session import SandboxMode

log = logging.getLogger(__name__)

# Image names per sandbox mode
_IMAGES: dict[SandboxMode, str] = {
    SandboxMode.CLI: "nightowl-sandbox-cli",
    SandboxMode.BROWSER: "nightowl-sandbox-browser",
    SandboxMode.COMPUTER: "nightowl-sandbox-computer",
}

# Resource defaults
_DEFAULT_MEM_LIMIT = "512m"
_DEFAULT_CPU_PERIOD = 100_000
_DEFAULT_CPU_QUOTA = 50_000  # 0.5 CPU


def _get_docker_client() -> docker.DockerClient:
    """Return a Docker client connected to the local daemon."""
    return docker.from_env()


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int


class DockerSandboxManager:
    """Manages ephemeral Docker containers for sandboxed agent sessions."""

    def __init__(self) -> None:
        self._session_to_container: dict[str, str] = {}
        self._container_to_session: dict[str, str] = {}

    async def create_container(
        self, session_id: str, sandbox_mode: SandboxMode,
    ) -> str:
        """Create and start a sandboxed container for the given session.

        Returns the container ID.
        """
        if sandbox_mode == SandboxMode.NONE:
            raise ValueError("Cannot create a container for SandboxMode.NONE")

        image = _IMAGES[sandbox_mode]
        client = _get_docker_client()

        container = await asyncio.to_thread(
            client.containers.run,
            image,
            detach=True,
            stdin_open=True,
            network_disabled=False,
            mem_limit=_DEFAULT_MEM_LIMIT,
            cpu_period=_DEFAULT_CPU_PERIOD,
            cpu_quota=_DEFAULT_CPU_QUOTA,
            volumes={},
            labels={"nightowl.session_id": session_id},
        )

        container_id = container.id
        self._session_to_container[session_id] = container_id
        self._container_to_session[container_id] = session_id
        log.info("Created %s container %s for session %s", sandbox_mode, container_id, session_id)
        return container_id

    async def exec_command(self, container_id: str, command: str) -> ExecResult:
        """Execute a command inside the container. Returns ExecResult."""
        try:
            client = _get_docker_client()
            container = await asyncio.to_thread(client.containers.get, container_id)
        except Exception as exc:
            return ExecResult(stdout="", stderr=f"Error: container not found — {exc}", exit_code=1)

        try:
            exit_code, output = await asyncio.to_thread(
                container.exec_run, ["bash", "-c", command], demux=False,
            )
        except Exception as exc:
            return ExecResult(stdout="", stderr=f"Error executing command: {exc}", exit_code=1)

        text = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else str(output)

        if exit_code == 0:
            return ExecResult(stdout=text, stderr="", exit_code=0)
        else:
            return ExecResult(stdout="", stderr=text, exit_code=exit_code)

    async def cleanup(self, container_id: str) -> None:
        """Stop and remove a container. Safe to call on non-existent containers."""
        try:
            client = _get_docker_client()
            container = await asyncio.to_thread(client.containers.get, container_id)
            await asyncio.to_thread(container.stop)
            await asyncio.to_thread(container.remove)
        except Exception:
            log.debug("Cleanup of container %s failed (may already be gone)", container_id)

        # Clean up mappings
        session_id = self._container_to_session.pop(container_id, None)
        if session_id:
            self._session_to_container.pop(session_id, None)

    async def extract_files(
        self, container_id: str, paths: list[str],
    ) -> dict[str, bytes | None]:
        """Copy files out of a container. Returns {path: content_bytes | None}."""
        result: dict[str, bytes | None] = {}
        try:
            client = _get_docker_client()
            container = await asyncio.to_thread(client.containers.get, container_id)
        except Exception:
            return {p: None for p in paths}

        for path in paths:
            try:
                data, _stat = await asyncio.to_thread(container.get_archive, path)
                result[path] = data if isinstance(data, bytes) else bytes(data)
            except Exception:
                result[path] = None

        return result

    async def ensure_container(
        self, session_id: str, sandbox_mode: SandboxMode,
    ) -> str:
        """Return the existing container for this session, or create one lazily.

        If a container already exists but is a different mode, the existing
        container is reused (upgrading requires explicit cleanup + recreate).
        """
        existing = self._session_to_container.get(session_id)
        if existing is not None:
            return existing
        return await self.create_container(session_id, sandbox_mode)

    def get_container_for_session(self, session_id: str) -> str | None:
        """Look up the container ID for a session, or None."""
        return self._session_to_container.get(session_id)
