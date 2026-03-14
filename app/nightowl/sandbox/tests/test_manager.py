"""Tests for DockerSandboxManager.

Module under test: nightowl/sandbox/manager.py

DockerSandboxManager handles the lifecycle of ephemeral Docker containers:
- create_container(session_id, sandbox_mode) → container_id
- exec_command(container_id, command) → ExecResult(stdout, stderr, exit_code)
- cleanup(container_id) → stops + removes
- extract_files(container_id, paths) → dict[path, bytes]

Containers are ephemeral per-session, resource-limited, network-isolated by default.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightowl.models.session import SandboxMode
from nightowl.sandbox.manager import DockerSandboxManager


# ---------------------------------------------------------------------------
# Container creation
# ---------------------------------------------------------------------------


class TestCreateContainer:
    async def test_cli_mode_creates_container(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock(id="abc123")
            mock_client.containers.run = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            container_id = await mgr.create_container("session:1", SandboxMode.CLI)

        assert container_id is not None
        assert len(container_id) > 0

    async def test_browser_mode_creates_container(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock(id="def456")
            mock_client.containers.run = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            container_id = await mgr.create_container("session:2", SandboxMode.BROWSER)

        assert container_id is not None

    async def test_computer_mode_creates_container(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock(id="ghi789")
            mock_client.containers.run = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            container_id = await mgr.create_container("session:3", SandboxMode.COMPUTER)

        assert container_id is not None

    async def test_each_mode_uses_different_image(self):
        """CLI, browser, and computer modes should use distinct Docker images."""
        images_used = []

        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock(id="x")
            mock_client.containers.run = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            for mode in (SandboxMode.CLI, SandboxMode.BROWSER, SandboxMode.COMPUTER):
                await mgr.create_container(f"session:{mode}", mode)
                call_args = str(mock_client.containers.run.call_args)
                images_used.append(call_args)
                mock_client.containers.run.reset_mock()

        # All three should have used different image names
        assert len(set(images_used)) == 3

    async def test_none_mode_raises(self):
        """SandboxMode.NONE means no container — should reject."""
        mgr = DockerSandboxManager()
        with pytest.raises((ValueError, TypeError)):
            await mgr.create_container("session:x", SandboxMode.NONE)


# ---------------------------------------------------------------------------
# Security constraints on creation
# ---------------------------------------------------------------------------


class TestContainerSecurityDefaults:
    async def test_network_disabled_by_default(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock(id="x")
            mock_client.containers.run = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            await mgr.create_container("session:1", SandboxMode.CLI)

        call_str = str(mock_client.containers.run.call_args)
        # network_disabled or network_mode="none" must be present
        assert "network" in call_str.lower()

    async def test_cpu_memory_limits_set(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock(id="x")
            mock_client.containers.run = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            await mgr.create_container("session:1", SandboxMode.CLI)

        call_str = str(mock_client.containers.run.call_args)
        # Must set resource limits
        assert "mem_limit" in call_str or "memory" in call_str.lower()
        assert "cpu" in call_str.lower() or "nano_cpus" in call_str

    async def test_no_host_mounts_by_default(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock(id="x")
            mock_client.containers.run = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            await mgr.create_container("session:1", SandboxMode.CLI)

        call_kwargs = mock_client.containers.run.call_args
        # volumes/mounts should be empty or absent
        volumes = call_kwargs[1].get("volumes") if call_kwargs[1] else None
        if volumes:
            assert len(volumes) == 0


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------


class TestExecCommand:
    async def test_returns_stdout(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.exec_run = MagicMock(return_value=(0, b"hello world\n"))
            mock_client.containers.get = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            result = await mgr.exec_command("container:abc", "echo hello world")

        assert "hello world" in result.stdout

    async def test_returns_stderr_on_error(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.exec_run = MagicMock(return_value=(1, b"command not found\n"))
            mock_client.containers.get = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            result = await mgr.exec_command("container:abc", "nonexistent_cmd")

        assert result.exit_code != 0
        assert len(result.stderr) > 0 or len(result.stdout) > 0

    async def test_returns_exit_code(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.exec_run = MagicMock(return_value=(42, b""))
            mock_client.containers.get = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            result = await mgr.exec_command("container:abc", "exit 42")

        assert result.exit_code == 42

    async def test_exec_on_nonexistent_container_returns_error(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_client.containers.get = MagicMock(side_effect=Exception("No such container"))
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            result = await mgr.exec_command("container:gone", "ls")

        assert result.exit_code != 0
        assert "error" in result.stderr.lower() or "not" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    async def test_cleanup_stops_and_removes_container(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_client.containers.get = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            await mgr.cleanup("container:abc")

        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()

    async def test_cleanup_nonexistent_container_does_not_crash(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_client.containers.get = MagicMock(side_effect=Exception("No such container"))
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            # Must not raise
            await mgr.cleanup("container:gone")


# ---------------------------------------------------------------------------
# File extraction
# ---------------------------------------------------------------------------


class TestExtractFiles:
    async def test_extract_returns_file_contents(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            # get_archive returns (tar_stream, stat)
            mock_container.get_archive = MagicMock(return_value=(b"tardata", {"size": 100}))
            mock_client.containers.get = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            result = await mgr.extract_files("container:abc", ["/output/report.csv"])

        assert "/output/report.csv" in result
        assert result["/output/report.csv"] is not None

    async def test_extract_nonexistent_file_returns_error(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.get_archive = MagicMock(side_effect=Exception("Not found"))
            mock_client.containers.get = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            result = await mgr.extract_files("container:abc", ["/no/such/file"])

        # Should handle gracefully — either missing key or None value
        val = result.get("/no/such/file")
        assert val is None or isinstance(val, str)


# ---------------------------------------------------------------------------
# Session-container mapping
# ---------------------------------------------------------------------------


class TestSessionContainerMapping:
    async def test_tracks_container_per_session(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock(id="c1")
            mock_client.containers.run = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            cid = await mgr.create_container("session:1", SandboxMode.CLI)

        assert mgr.get_container_for_session("session:1") == cid

    async def test_unknown_session_returns_none(self):
        mgr = DockerSandboxManager()
        assert mgr.get_container_for_session("session:nonexistent") is None

    async def test_cleanup_removes_session_mapping(self):
        with patch("nightowl.sandbox.manager._get_docker_client") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock(id="c1")
            mock_client.containers.run = MagicMock(return_value=mock_container)
            mock_client.containers.get = MagicMock(return_value=mock_container)
            mock_docker.return_value = mock_client

            mgr = DockerSandboxManager()
            await mgr.create_container("session:1", SandboxMode.CLI)
            await mgr.cleanup(mgr.get_container_for_session("session:1"))

        assert mgr.get_container_for_session("session:1") is None
