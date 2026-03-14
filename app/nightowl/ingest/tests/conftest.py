"""Shared fixtures for ingest tests."""

import pytest

from nightowl.sessions.manager import SessionManager


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager()
