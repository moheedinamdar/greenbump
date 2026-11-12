from __future__ import annotations

from pathlib import Path

import pytest

from greenbump.runner import parse_summary, redact_paths, run_pytest
from greenbump.workspace import Workspace, WorkspaceError


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("2 failed, 5 passed in 0.12s", {"failed": 2, "passed": 5}),
        ("1 error in 0.10s", {"errors": 1}),
        ("3 passed, 1 skipped, 2 warnings in 1.01s", {"passed": 3, "skipped": 1}),
        ("==== 1 failed, 2 errors in 3.00s ====", {"failed": 1, "errors": 2}),
        ("no tests ran in 0.01s", {}),
    ],
)
def test_parse_summary(line: str, expected: dict[str, int]) -> None:
    counts = parse_summary(f"....\nsome output\n{line}\n")
    assert {k: v for k, v in counts.items() if k != "warnings"} == expected


def test_parse_summary_without_summary_line() -> None:
    assert parse_summary("Traceback (most recent call last):\nboom\n") == {}


def test_workspace_copies_without_venv_and_refuses_escapes(mini_repo: Path, tmp_path: Path) -> None:
    ws = Workspace(mini_repo, tmp_path / "work")
    assert not (ws.root / ".venv").exists()
    for bad in ["../x", "/etc/passwd", "", "tests/../../x"]:
        with pytest.raises(WorkspaceError):
            ws.resolve(bad)


def test_workspace_refuses_symlink_escape(mini_repo: Path, tmp_path: Path) -> None:
    (tmp_path / "secret.txt").write_text("secret")
    (mini_repo / "link.txt").symlink_to(tmp_path / "secret.txt")
    ws = Workspace(mini_repo, tmp_path / "work")
    with pytest.raises(WorkspaceError):
        ws.read("link.txt")


def test_replace_unique_ambiguous_and_missing(mini_repo: Path, tmp_path: Path) -> None:
    ws = Workspace(mini_repo, tmp_path / "work")
    (ws.root / "dup.py").write_text("a = 1\na = 1\n")
    with pytest.raises(WorkspaceError, match="2 times"):
        ws.replace("dup.py", "a = 1", "a = 2")
    assert ws.replace("dup.py", "a = 1", "a = 2", replace_all=True) == 2
    with pytest.raises(WorkspaceError, match="not found"):
        ws.replace("app.py", "nope", "x")
    with pytest.raises(WorkspaceError, match=r"Closest lines in the file:\n    2 \| return x \* 3"):
        ws.replace("app.py", "return x*3", "return x * 2")
    with pytest.raises(WorkspaceError, match="only edits existing files"):
        ws.write("new.py", "x = 1\n")


def test_diff_and_changed_files(mini_repo: Path, tmp_path: Path) -> None:
    ws = Workspace(mini_repo, tmp_path / "work")
    assert ws.diff() == ""
    ws.replace("app.py", "x * 3", "x * 2")
    assert ws.changed_files() == ["app.py"]
    assert "+    return x * 2" in ws.diff()


def test_run_pytest_scrubs_secrets(
    mini_repo: Path, tmp_path: Path, python: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "should-not-leak")
    (mini_repo / "tests" / "test_env.py").write_text(
        "import os\n\n\ndef test_env():\n    assert 'GITHUB_TOKEN' not in os.environ\n"
    )
    run = run_pytest(mini_repo, python)
    assert run.passed == 1 and run.failed == 1
    assert str(mini_repo) not in run.output
    assert str(Path.home()) not in run.output


def test_redact_paths(tmp_path: Path) -> None:
    venv_python = str(tmp_path / "venv" / "bin" / "python")
    text = f"{tmp_path}/repo/a.py and {tmp_path}/venv/lib/x.py and {Path.home()}/other"
    out = redact_paths(text, tmp_path / "repo", venv_python)
    assert out == "<repo>/a.py and <venv>/lib/x.py and ~/other"
