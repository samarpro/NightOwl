"""Tests for data models — serialisation, defaults, enum values."""

import json

from nightowl.models.session import (
    SandboxMode,
    Session,
    SessionRole,
    SessionState,
    SpawnRequest,
    TaskCompletionEvent,
)
from nightowl.models.message import ChannelMessage, Message
from nightowl.models.approval import ApprovalRequest, RiskLevel, ToolCallWithRisk
from nightowl.models.observability import AgentCard, IntentGraph, IntentNode, IntentEdge


class TestSessionModel:
    def test_session_serialises_to_json_and_back(self):
        session = Session(
            id="session:abc",
            role=SessionRole.ORCHESTRATOR,
            state=SessionState.RUNNING,
            depth=1,
            task="find restaurants",
            parent_id="session:parent",
            children=["session:child1"],
        )
        data = json.loads(session.model_dump_json())
        restored = Session(**data)
        assert restored.id == "session:abc"
        assert restored.role == SessionRole.ORCHESTRATOR
        assert restored.children == ["session:child1"]

    def test_session_defaults(self):
        session = Session(id="session:x")
        assert session.role == SessionRole.MAIN
        assert session.state == SessionState.PENDING
        assert session.depth == 0
        assert session.children == []
        assert session.expected_completions == set()
        assert session.result is None

    def test_expected_completions_tracks_children(self):
        session = Session(id="session:x", expected_completions={"session:a", "session:b"})
        session.expected_completions.discard("session:a")
        assert session.expected_completions == {"session:b"}


class TestSessionEnums:
    def test_role_values(self):
        assert SessionRole.MAIN.value == "main"
        assert SessionRole.ORCHESTRATOR.value == "orchestrator"
        assert SessionRole.LEAF.value == "leaf"

    def test_state_values(self):
        assert SessionState.PENDING.value == "pending"
        assert SessionState.RUNNING.value == "running"
        assert SessionState.WAITING.value == "waiting"
        assert SessionState.COMPLETED.value == "completed"
        assert SessionState.FAILED.value == "failed"

    def test_sandbox_values(self):
        assert SandboxMode.NONE.value == "none"
        assert SandboxMode.CLI.value == "cli"
        assert SandboxMode.BROWSER.value == "browser"
        assert SandboxMode.COMPUTER.value == "computer"


class TestSpawnRequest:
    def test_defaults(self):
        req = SpawnRequest(task="do stuff")
        assert req.label is None
        assert req.sandbox == SandboxMode.NONE

    def test_with_all_fields(self):
        req = SpawnRequest(task="browse", label="browser-agent", sandbox=SandboxMode.BROWSER)
        assert req.task == "browse"
        assert req.label == "browser-agent"
        assert req.sandbox == SandboxMode.BROWSER


class TestTaskCompletionEvent:
    def test_construction(self):
        event = TaskCompletionEvent(
            child_session_id="session:child",
            parent_session_id="session:parent",
            result="found 5 restaurants",
        )
        assert event.success is True
        assert event.result == "found 5 restaurants"

    def test_failed_event(self):
        event = TaskCompletionEvent(
            child_session_id="session:child",
            parent_session_id="session:parent",
            result="timeout",
            success=False,
        )
        assert event.success is False


class TestMessageModels:
    def test_channel_message(self):
        msg = ChannelMessage(channel="telegram", sender_id="user123", text="hello", chat_id="chat1")
        assert msg.thread_id is None
        assert msg.chat_id == "chat1"
        assert msg.metadata == {}

    def test_message_round_trip(self):
        msg = Message(session_id="session:x", role="user", content="hello agent")
        data = json.loads(msg.model_dump_json())
        restored = Message(**data)
        assert restored.content == "hello agent"
        assert restored.id is None


class TestApprovalModels:
    def test_risk_levels(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_tool_call_with_risk_defaults(self):
        tc = ToolCallWithRisk(tool_name="bash_exec")
        assert tc.risk_level == RiskLevel.LOW
        assert tc.tool_args == {}

    def test_approval_request(self):
        req = ApprovalRequest(
            id="approval:1",
            session_id="session:x",
            tool_name="bash_exec",
            tool_args={"command": "rm -rf /"},
            risk_level=RiskLevel.CRITICAL,
        )
        assert req.status == "pending"


class TestObservabilityModels:
    def test_empty_intent_graph(self):
        graph = IntentGraph()
        assert graph.nodes == []
        assert graph.edges == []

    def test_intent_graph_with_data(self):
        graph = IntentGraph(
            nodes=[
                IntentNode(id="n1", label="calendar check"),
                IntentNode(id="n2", label="restaurant search"),
            ],
            edges=[IntentEdge(source="n1", target="n2", label="then")],
        )
        assert len(graph.nodes) == 2
        assert graph.edges[0].source == "n1"

    def test_agent_card(self):
        card = AgentCard(
            session_id="session:x",
            role="orchestrator",
            label="planner",
            task="plan night out",
            depth=1,
            children=["session:a", "session:b"],
        )
        assert len(card.children) == 2
