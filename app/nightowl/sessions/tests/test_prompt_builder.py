"""Tests for prompt builder — verifies role-scoped prompt content."""

from nightowl.models.session import Session, SessionRole, SessionState
from nightowl.sessions.prompt_builder import build_system_prompt


def _make_session(role: SessionRole, depth: int = 0, **kwargs) -> Session:
    return Session(
        id="session:test",
        role=role,
        depth=depth,
        task=kwargs.get("task", "do the thing"),
        parent_id=kwargs.get("parent_id"),
    )


class TestMainPrompt:
    def test_includes_identity(self):
        prompt = build_system_prompt(_make_session(SessionRole.MAIN))
        assert "NightOwl" in prompt

    def test_includes_session_tools(self):
        prompt = build_system_prompt(_make_session(SessionRole.MAIN))
        assert "sessions_spawn" in prompt

    def test_includes_no_poll_rule(self):
        prompt = build_system_prompt(_make_session(SessionRole.MAIN))
        assert "do NOT" in prompt
        assert "poll" in prompt.lower()

    def test_includes_skills_when_provided(self):
        prompt = build_system_prompt(
            _make_session(SessionRole.MAIN),
            skills_prompt="Can book restaurants via OpenTable",
        )
        assert "OpenTable" in prompt

    def test_omits_skills_section_when_none(self):
        prompt = build_system_prompt(_make_session(SessionRole.MAIN))
        assert "Available skills" not in prompt


class TestOrchestratorPrompt:
    def test_includes_task(self):
        prompt = build_system_prompt(
            _make_session(SessionRole.ORCHESTRATOR, depth=1, task="find restaurants", parent_id="session:parent")
        )
        assert "find restaurants" in prompt

    def test_includes_depth_and_role(self):
        prompt = build_system_prompt(
            _make_session(SessionRole.ORCHESTRATOR, depth=2, parent_id="session:parent")
        )
        assert "depth" in prompt.lower() and "2" in prompt
        assert "orchestrator" in prompt.lower()

    def test_includes_parent_reference(self):
        prompt = build_system_prompt(
            _make_session(SessionRole.ORCHESTRATOR, depth=1, parent_id="session:abc123")
        )
        assert "session:abc123" in prompt

    def test_can_spawn_children(self):
        prompt = build_system_prompt(
            _make_session(SessionRole.ORCHESTRATOR, depth=1, parent_id="session:parent")
        )
        assert "sessions_spawn" in prompt

    def test_includes_no_poll_rule(self):
        prompt = build_system_prompt(
            _make_session(SessionRole.ORCHESTRATOR, depth=1, parent_id="session:parent")
        )
        assert "do NOT" in prompt


class TestLeafPrompt:
    def test_includes_task(self):
        prompt = build_system_prompt(
            _make_session(SessionRole.LEAF, depth=3, task="scrape webpage", parent_id="session:parent")
        )
        assert "scrape webpage" in prompt

    def test_cannot_spawn(self):
        prompt = build_system_prompt(
            _make_session(SessionRole.LEAF, depth=3, parent_id="session:parent")
        )
        assert "CANNOT spawn" in prompt

    def test_does_not_include_spawn_tool(self):
        prompt = build_system_prompt(
            _make_session(SessionRole.LEAF, depth=3, parent_id="session:parent")
        )
        assert "sessions_spawn" not in prompt

    def test_includes_depth_and_role(self):
        prompt = build_system_prompt(
            _make_session(SessionRole.LEAF, depth=3, parent_id="session:parent")
        )
        assert "depth" in prompt.lower() and "3" in prompt
        assert "leaf" in prompt.lower()
