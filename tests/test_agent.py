from __future__ import annotations

import json
from pathlib import Path

from conftest import ScriptedClient
from greenbump.agent import Budget
from greenbump.fixer import FixRequest, run_fix
from greenbump.models import Bump

FIX = {"path": "app.py", "old_text": "return x * 3", "new_text": "return x * 2"}


def _req(repo: Path, tmp_path: Path, python: str, mode: str = "agent", steps: int = 10) -> FixRequest:
    return FixRequest(
        repo=repo,
        bumps=[Bump("fakelib", "2.0", "1.0")],
        python=python,
        out_dir=tmp_path / "out",
        cache_dir=tmp_path / "cache",
        mode=mode,
        budget=Budget(max_steps=steps, max_seconds=120),
    )


def test_agent_fixes_and_verifier_accepts(
    mini_repo: Path, tmp_path: Path, python: str, no_changelog: None
) -> None:
    client = ScriptedClient(
        [("run_tests", {}), ("edit_file", FIX), ("run_tests", {}), ("finish", {"summary": "x2"})]
    )
    result = run_fix(_req(mini_repo, tmp_path, python), client)
    assert result.verified
    assert result.stop_reason == "finish"
    assert result.changed_files == ["app.py"]
    assert "-    return x * 3" in result.diff
    assert (mini_repo / "app.py").read_text().endswith("x * 3\n"), "the original repo must never be touched"
    events = [
        json.loads(line)["event"] for line in (tmp_path / "out" / "audit.jsonl").read_text().splitlines()
    ]
    assert events[0] == "start" and events[-1] == "verdict" and "tool" in events
    assert (tmp_path / "out" / "patch.diff").read_text() == result.diff


def test_finish_is_refused_while_tests_fail(
    mini_repo: Path, tmp_path: Path, python: str, no_changelog: None
) -> None:
    client = ScriptedClient(
        [("finish", {"summary": "done"}), ("edit_file", FIX), ("finish", {"summary": "ok"})]
    )
    result = run_fix(_req(mini_repo, tmp_path, python), client)
    assert result.verified
    assert result.steps == 3


def test_cheating_edit_is_refused(mini_repo: Path, tmp_path: Path, python: str, no_changelog: None) -> None:
    skip = {
        "path": "tests/test_app.py",
        "old_text": "def test_double():",
        "new_text": "import pytest\n\n\n@pytest.mark.skip\ndef test_double():",
    }
    client = ScriptedClient([("edit_file", skip), ("give_up", {"reason": "blocked"})])
    result = run_fix(_req(mini_repo, tmp_path, python), client)
    assert not result.verified
    assert result.edits_refused == 1
    assert any("skips-tests" in hit for hit in result.guardrail_hits)
    assert result.changed_files == []


def test_requirements_edit_is_refused(
    mini_repo: Path, tmp_path: Path, python: str, no_changelog: None
) -> None:
    pin = {"path": "requirements.txt", "old_text": "fakelib==2.0", "new_text": "fakelib==1.0"}
    client = ScriptedClient([("edit_file", pin), ("give_up", {"reason": "blocked"})])
    result = run_fix(_req(mini_repo, tmp_path, python), client)
    assert result.edits_refused == 1
    assert (tmp_path / "out" / "work" / "requirements.txt").read_text() == "fakelib==2.0\n"


def test_step_budget_stops_the_loop(mini_repo: Path, tmp_path: Path, python: str, no_changelog: None) -> None:
    client = ScriptedClient([("list_files", {})] * 10)
    result = run_fix(_req(mini_repo, tmp_path, python, steps=3), client)
    assert result.stop_reason == "step-budget"
    assert result.steps == 3
    assert not result.verified


def test_repeated_failing_call_gets_a_warning(
    mini_repo: Path, tmp_path: Path, python: str, no_changelog: None
) -> None:
    bad = {"path": "app.py", "old_text": "return x*3", "new_text": "return x * 2"}
    client = ScriptedClient(
        [("edit_file", bad), ("edit_file", {**bad, "replace_all": False}), ("give_up", {"reason": "x"})]
    )
    run_fix(_req(mini_repo, tmp_path, python), client)
    results = [
        json.loads(line)["result"]
        for line in (tmp_path / "out" / "audit.jsonl").read_text().splitlines()
        if json.loads(line)["event"] == "tool"
    ]
    assert "exactly this call before" not in results[0]
    assert "exactly this call before" in results[1]


def test_model_that_never_calls_tools_is_stopped(
    mini_repo: Path, tmp_path: Path, python: str, no_changelog: None
) -> None:
    client = ScriptedClient([])
    result = run_fix(_req(mini_repo, tmp_path, python), client)
    assert result.stop_reason == "no-tool-call"
    assert client.temperatures[0] == 0.0 and all(t > 0 for t in client.temperatures[1:])
    assert all(m["content"] != "I am thinking" for m in client.seen[-1]), (
        "tool-less replies stay out of history"
    )


def test_edit_feedback_shows_the_result_and_flags_dropped_imports(
    mini_repo: Path, tmp_path: Path, python: str, no_changelog: None
) -> None:
    (mini_repo / "app.py").write_text(
        "from os import sep\n\n\ndef double(x):\n    return x * 3 if sep else 0\n"
    )
    drop = {"path": "app.py", "old_text": "from os import sep\n", "new_text": ""}
    broken = {"path": "app.py", "old_text": "return x * 3", "new_text": "return (x * 3"}
    client = ScriptedClient([("edit_file", drop), ("edit_file", broken), ("give_up", {"reason": "x"})])
    run_fix(_req(mini_repo, tmp_path, python), client)
    results = [
        json.loads(line)["result"]
        for line in (tmp_path / "out" / "audit.jsonl").read_text().splitlines()
        if json.loads(line)["event"] == "tool"
    ]
    assert "The file now reads:" in results[0]
    assert "`sep` is no longer imported" in results[0]
    assert "invalid Python" in results[1]
    assert "return x * 3" in (tmp_path / "out" / "work" / "app.py").read_text()


def test_single_shot_applies_edits_once(
    mini_repo: Path, tmp_path: Path, python: str, no_changelog: None
) -> None:
    client = ScriptedClient(content=json.dumps({"edits": [{**FIX, "replace_all": False}], "summary": "x2"}))
    result = run_fix(_req(mini_repo, tmp_path, python, mode="single-shot"), client)
    assert result.verified
    assert result.llm_calls == 1
    assert result.stop_reason == "answered"


def test_already_passing_repo_is_left_alone(
    mini_repo: Path, tmp_path: Path, python: str, no_changelog: None
) -> None:
    (mini_repo / "app.py").write_text("def double(x):\n    return x * 2\n")
    result = run_fix(_req(mini_repo, tmp_path, python), ScriptedClient([]))
    assert result.stop_reason == "already-passing"
    assert result.llm_calls == 0


def test_path_escape_is_an_error_not_a_crash(
    mini_repo: Path, tmp_path: Path, python: str, no_changelog: None
) -> None:
    client = ScriptedClient([("read_file", {"path": "../../etc/passwd"}), ("give_up", {"reason": "x"})])
    run_fix(_req(mini_repo, tmp_path, python), client)
    tool_results = [
        json.loads(line)
        for line in (tmp_path / "out" / "audit.jsonl").read_text().splitlines()
        if json.loads(line)["event"] == "tool"
    ]
    assert tool_results[0]["result"].startswith("ERROR: path escapes the repository")
