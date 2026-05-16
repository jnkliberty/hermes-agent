from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def hermes_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    yield home


def test_goalify_missing_measurable_criteria_asks_first(hermes_home):
    from hermes_cli.goalify import GoalifyManager

    mgr = GoalifyManager("sid-criteria")
    result = mgr.start(
        "I want to make the dashboard fast and clean for founders in the gtm app",
        cwd="/Users/juli/src/gtm-run",
    )

    assert result.kind == "clarify"
    assert "measurable criteria" in result.message.lower()
    assert "you said 'fast'" in result.message.lower()
    assert "2s" in result.message


def test_goalify_proposal_renders_full_template_and_sources(hermes_home):
    from hermes_cli.goalify import GoalifyManager

    mgr = GoalifyManager("sid-propose")
    raw = (
        "Build the health endpoint for the API. "
        "Project is gtm-run. Stack is Python FastAPI. "
        "Right now there is no health route. Audience is internal operators. "
        "Done when GET /api/health returns 200 with status ok, pytest tests/api/test_health.py passes, "
        "and docs/CHANGELOG.md includes a health endpoint entry."
    )
    result = mgr.start(raw, cwd="/Users/juli/src/gtm-run")

    assert result.kind == "propose"
    assert "```" in result.message
    assert "/goal Build the health endpoint for the API" in result.message
    assert "— OPERATING RULES — NON-NEGOTIABLE —" in result.message
    assert "USE THE RIGHT TOOLS" in result.message
    assert "Field sources:" in result.message
    assert "FINAL_OUTCOME" in result.message
    assert "Lock and engage goal-loop?" in result.message


def test_goalify_natural_yes_locks_and_returns_prompt(hermes_home):
    from hermes_cli.goalify import GoalifyManager, load_pending

    mgr = GoalifyManager("sid-lock")
    raw = (
        "Fix login tests. Project is auth-service. Stack is pytest and Python. "
        "Current state is two login tests fail. Audience is maintainers. "
        "Success means pytest tests/auth/test_login.py passes, ruff check . exits 0, "
        "and no files outside auth package change."
    )
    mgr.start(raw, cwd="/tmp/auth-service")
    result = mgr.followup("yeah looks good go ahead and lock it")

    assert result.kind == "execute"
    assert "Goal locked. Engaging goal-loop now." in result.message
    assert result.locked_prompt
    assert result.locked_prompt.startswith("/goal Fix login tests")
    assert load_pending("sid-lock") is None


def test_goalify_natural_language_edit_updates_only_field(hermes_home):
    from hermes_cli.goalify import GoalifyManager

    mgr = GoalifyManager("sid-edit")
    raw = (
        "Fix login tests. Project is auth-service. Stack is pytest and Python. "
        "Current state is two login tests fail. Audience is maintainers. "
        "Success means pytest tests/auth/test_login.py passes, ruff check . exits 0, "
        "and no files outside auth package change."
    )
    mgr.start(raw, cwd="/tmp/auth-service")
    result = mgr.followup("change the audience to product engineers")

    assert result.kind == "propose"
    assert "· Audience: product engineers" in result.message
    assert "Fix login tests" in result.message


def test_goalify_audit_writes_on_lock(hermes_home):
    from hermes_cli.goalify import GoalifyManager, goalify_home

    mgr = GoalifyManager("sid-audit")
    raw = (
        "Ship health check. Project is ops-api. Stack is FastAPI. Current state missing route. "
        "Audience is operators. Done when GET /health returns 200, pytest tests/test_health.py passes, "
        "and README includes the endpoint."
    )
    mgr.start(raw, cwd="/tmp/ops-api")
    mgr.followup("yes start")

    audit = goalify_home() / "runs.jsonl"
    assert audit.exists()
    text = audit.read_text(encoding="utf-8")
    assert "sid-audit" in text
    assert "Ship health check" in text


def test_goalify_classifies_hardening_and_migration_modes(hermes_home):
    from hermes_cli.goalify import GoalifyManager, goalify_home

    mgr = GoalifyManager("sid-modes")
    raw = (
        "Upgrade the Stripe SDK migration and make CI production ready. "
        "Project is billing-api. Stack is Python. Current state is old SDK and floating GitHub actions. "
        "Audience is maintainers. Done when pytest tests/billing passes, rollback instructions exist, "
        "and no unpinned CI actions remain."
    )
    result = mgr.start(raw, cwd="/tmp/billing-api")

    assert result.kind == "propose"
    assert "— MODE CONTRACT —" in result.message
    assert "Primary mode: migration" in result.message
    assert "Secondary modes: hardening" in result.message
    assert "Tested rollback path" in result.message
    assert "Every fix includes a regression-preventing guardrail" in result.message
    assert (goalify_home() / "modes.yml").exists()


def test_goalify_refactor_mode_injects_behavior_preservation_stop_rules(hermes_home):
    from hermes_cli.goalify import GoalifyManager

    mgr = GoalifyManager("sid-refactor")
    raw = (
        "Refactor the auth module with zero behavior change. Project is auth-service. Stack is Python. "
        "Current state is auth.py is too large. Audience is maintainers. "
        "Done when pytest tests/auth passes, public API imports still work, and git diff has no feature changes."
    )
    result = mgr.start(raw, cwd="/tmp/auth-service")

    assert result.kind == "propose"
    assert "Primary mode: refactoring/restructuring" in result.message
    assert "Preserve behavior; do not co-mingle behavior changes with structural changes." in result.message
    assert "Run pre/post tests" in result.message


def test_goalify_deep_ideation_asks_one_question_and_does_not_propose(hermes_home):
    from hermes_cli.goalify import GoalifyManager

    mgr = GoalifyManager("sid-deep")
    result = mgr.start("--deep I have an idea for a modern agent dashboard", cwd="/tmp/agent-dashboard")

    assert result.kind == "clarify"
    assert "Deep Goalify interview" in result.message
    question_lines = [line for line in result.message.splitlines() if line.strip().startswith("1.")]
    assert len(question_lines) == 1
    assert "problem" in question_lines[0].lower() or "success" in question_lines[0].lower()


def test_goalify_consolidation_mode_prioritizes_caller_inventory(hermes_home):
    from hermes_cli.goalify import GoalifyManager

    mgr = GoalifyManager("sid-consolidate")
    raw = (
        "Consolidate the duplicate auth clients into one canonical implementation. "
        "Project is web-app. Stack is TypeScript. Current state is three SDK wrappers. "
        "Audience is app maintainers. Done when all callers use one client, pnpm test passes, "
        "and the old duplicate wrappers are deleted."
    )
    result = mgr.start(raw, cwd="/tmp/web-app")

    assert result.kind == "propose"
    assert "Primary mode: consolidation" in result.message
    assert "Inventory every parallel implementation and caller" in result.message
    assert "Do not delete non-canonical implementations until all callers are migrated and verified." in result.message
