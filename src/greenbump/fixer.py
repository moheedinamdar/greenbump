"""Glue: copy the repo, collect context, run the chosen strategy, verify, write artifacts."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .agent import Budget, LoopStats, run_agent
from .audit import AuditLog
from .changelog import ChangelogCache, ChangelogIndex, Doc, load_docs
from .context import CaseFile, build_case
from .guardrails import Limits
from .llm import ChatClient
from .models import Bump, TestRun
from .report import render_report
from .runner import run_pytest
from .single_shot import run_single_shot
from .tools import Toolbox
from .verify import verify
from .workspace import Workspace

MODES = ("agent", "single-shot")


@dataclass
class FixRequest:
    repo: Path
    bumps: list[Bump]
    python: str
    out_dir: Path
    cache_dir: Path
    mode: str = "agent"
    changelog_urls: list[str] = field(default_factory=list)
    budget: Budget = field(default_factory=Budget)
    limits: Limits = field(default_factory=Limits)
    test_timeout: float = 180.0


@dataclass
class Prepared:
    ws: Workspace
    initial: TestRun
    docs: list[Doc]
    index: ChangelogIndex
    case: CaseFile | None


@dataclass
class FixResult:
    mode: str
    model: str
    verified: bool
    stop_reason: str
    summary: str
    reasons: list[str]
    tests_before: str
    tests_after: str
    tests_passed: int
    tests_expected: int
    changed_files: list[str]
    steps: int
    llm_calls: int
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    edits_applied: int
    edits_refused: int
    test_runs: int
    guardrail_hits: list[str]
    changelog_sources: list[dict[str, str]]
    warnings: list[str]
    error: str = ""
    diff: str = ""

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def prepare(req: FixRequest) -> Prepared:
    """Phase 1 on its own: everything up to (not including) the model."""
    ws = Workspace(req.repo, req.out_dir / "work")
    initial = run_pytest_once(ws, req)
    if initial.ok:
        return Prepared(ws, initial, [], ChangelogIndex([]), None)
    docs, warnings = load_docs(req.bumps, req.changelog_urls, ChangelogCache(req.cache_dir))
    index = ChangelogIndex(docs, req.bumps)
    case = build_case(ws, req.bumps, initial, index, warnings)
    return Prepared(ws, initial, docs, index, case)


def run_pytest_once(ws: Workspace, req: FixRequest) -> TestRun:
    ws.clear_bytecode()
    return run_pytest(ws.root, req.python, req.test_timeout)


def run_fix(req: FixRequest, client: ChatClient) -> FixResult:
    if req.mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    started = time.monotonic()
    req.out_dir.mkdir(parents=True, exist_ok=True)
    audit = AuditLog(req.out_dir / "audit.jsonl")
    prep = prepare(req)
    sources = [{"url": d.url, "sha256": d.sha256} for d in prep.docs]
    if prep.case is None:
        before = prep.initial
        result = FixResult(
            mode=req.mode,
            model=client.name,
            verified=False,
            stop_reason="already-passing",
            summary="",
            reasons=["tests already pass; nothing to fix"],
            tests_before=before.headline(),
            tests_after=before.headline(),
            tests_passed=before.passed,
            tests_expected=before.passed,
            changed_files=[],
            steps=0,
            llm_calls=0,
            prompt_tokens=0,
            completion_tokens=0,
            seconds=round(time.monotonic() - started, 1),
            edits_applied=0,
            edits_refused=0,
            test_runs=1,
            guardrail_hits=[],
            changelog_sources=sources,
            warnings=[],
        )
        _write(req.out_dir, result, None)
        return result

    case_text = prep.case.render()
    (req.out_dir / "case.md").write_text(case_text, encoding="utf-8")
    audit.write(
        "start",
        mode=req.mode,
        model=client.name,
        bumps=[b.describe() for b in req.bumps],
        tests_before=prep.initial.headline(),
        changelog_sources=sources,
    )
    toolbox = Toolbox(prep.ws, req.python, prep.index, req.bumps, req.test_timeout)
    stats: LoopStats
    if req.mode == "agent":
        stats = run_agent(client, toolbox, case_text, req.budget, audit)
    else:
        stats = run_single_shot(client, toolbox, case_text, audit)

    verdict = verify(prep.ws, req.python, req.bumps, req.limits, req.test_timeout)
    audit.write("verdict", passed=verdict.passed, reasons=verdict.reasons, tests=verdict.tests.headline())
    result = FixResult(
        mode=req.mode,
        model=client.name,
        verified=verdict.passed,
        stop_reason=stats.stop_reason,
        summary=stats.summary,
        reasons=verdict.reasons,
        tests_before=prep.initial.headline(),
        tests_after=verdict.tests.headline(),
        tests_passed=verdict.tests.passed,
        tests_expected=verdict.expected_tests,
        changed_files=verdict.changed_files,
        steps=stats.steps,
        llm_calls=stats.llm_calls,
        prompt_tokens=stats.prompt_tokens,
        completion_tokens=stats.completion_tokens,
        seconds=round(time.monotonic() - started, 1),
        edits_applied=toolbox.edits_applied,
        edits_refused=toolbox.edits_refused,
        test_runs=len(toolbox.test_runs) + 2,
        guardrail_hits=toolbox.guardrail_hits,
        changelog_sources=sources,
        warnings=prep.case.warnings,
        error=stats.error,
        diff=prep.ws.diff(),
    )
    _write(req.out_dir, result, verdict.tests)
    return result


def _write(out_dir: Path, result: FixResult, final_tests: TestRun | None) -> None:
    (out_dir / "result.json").write_text(json.dumps(result.to_json(), indent=2), encoding="utf-8")
    (out_dir / "patch.diff").write_text(result.diff, encoding="utf-8")
    (out_dir / "report.md").write_text(render_report(result, final_tests), encoding="utf-8")
