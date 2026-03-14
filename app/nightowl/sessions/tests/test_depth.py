"""Tests for depth and role resolution."""

from nightowl.models.session import SessionRole
from nightowl.sessions.depth import resolve_capabilities, resolve_control_scope, resolve_role


class TestResolveRole:
    def test_depth_zero_is_main(self):
        assert resolve_role(0) == SessionRole.MAIN

    def test_depth_one_is_orchestrator(self):
        assert resolve_role(1) == SessionRole.ORCHESTRATOR

    def test_mid_depth_is_orchestrator(self):
        assert resolve_role(2, max_depth=4) == SessionRole.ORCHESTRATOR

    def test_max_depth_is_leaf(self):
        assert resolve_role(3, max_depth=3) == SessionRole.LEAF

    def test_beyond_max_depth_is_leaf(self):
        assert resolve_role(5, max_depth=3) == SessionRole.LEAF

    def test_negative_depth_treated_as_main(self):
        assert resolve_role(-1) == SessionRole.MAIN

    def test_custom_max_depth_one_makes_depth_one_leaf(self):
        assert resolve_role(1, max_depth=1) == SessionRole.LEAF

    def test_custom_deep_hierarchy(self):
        assert resolve_role(9, max_depth=10) == SessionRole.ORCHESTRATOR
        assert resolve_role(10, max_depth=10) == SessionRole.LEAF


class TestControlScope:
    def test_main_has_children_scope(self):
        assert resolve_control_scope(SessionRole.MAIN) == "children"

    def test_orchestrator_has_children_scope(self):
        assert resolve_control_scope(SessionRole.ORCHESTRATOR) == "children"

    def test_leaf_has_no_scope(self):
        assert resolve_control_scope(SessionRole.LEAF) == "none"


class TestResolveCapabilities:
    def test_main_can_spawn(self):
        caps = resolve_capabilities(0)
        assert caps["role"] == SessionRole.MAIN
        assert caps["can_spawn"] is True

    def test_orchestrator_can_spawn(self):
        caps = resolve_capabilities(1, max_depth=3)
        assert caps["role"] == SessionRole.ORCHESTRATOR
        assert caps["can_spawn"] is True

    def test_leaf_cannot_spawn(self):
        caps = resolve_capabilities(3, max_depth=3)
        assert caps["role"] == SessionRole.LEAF
        assert caps["can_spawn"] is False

    def test_depth_is_normalised(self):
        caps = resolve_capabilities(-5)
        assert caps["depth"] == 0
