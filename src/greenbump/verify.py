"""Phase 4: the final gate. Plain code decides whether a fix counts, never the model."""

from __future__ import annotations

from dataclasses import dataclass, field

from .guardrails import Limits, Violation, check_changes, count_tests
from .models import Bump, TestRun
from .runner import run_pytest
from .workspace import Workspace


@dataclass
class Verdict:
    passed: bool
    tests: TestRun
    expected_tests: int
    changed_files: list[str]
    violations: list[Violation] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def verify(
    ws: Workspace, python: str, bumps: list[Bump], limits: Limits, test_timeout: float = 180.0
) -> Verdict:
    ws.clear_bytecode()
    tests = run_pytest(ws.root, python, test_timeout)
    violations = check_changes(ws.original, ws.snapshot(), {b.import_name for b in bumps}, limits)
    expected = count_tests(ws.original)
    changed = ws.changed_files()

    reasons: list[str] = []
    if not changed:
        reasons.append("no files were changed")
    if not tests.ok:
        reasons.append(f"tests do not pass: {tests.headline()}")
    elif tests.passed < expected:
        reasons.append(f"{tests.passed} tests passed but the repository defines {expected} test functions")
    reasons += [str(v) for v in violations]
    return Verdict(not reasons, tests, expected, changed, violations, reasons)
