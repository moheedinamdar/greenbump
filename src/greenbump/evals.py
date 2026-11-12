"""Phase 5: the eval harness.

Each case is a small repository written against the OLD major version of a library, with its
requirements already bumped to the NEW one (what a Renovate or Dependabot PR leaves behind), plus
a reference solution. ``validate`` proves every case is real (broken as shipped, fixed by the
reference, reference passes the guardrails). ``run`` measures single-shot against the agent.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__
from .agent import Budget
from .fixer import FixRequest, FixResult, run_fix
from .guardrails import Limits, check_changes
from .llm import ChatClient
from .models import Bump
from .runner import run_pytest
from .workspace import Workspace

REQUIREMENT_FILES = ("requirements.txt", "requirements-dev.txt")


class CaseError(RuntimeError):
    """A case directory is malformed or its environment cannot be built."""


@dataclass
class Case:
    name: str
    path: Path
    description: str
    bumps: list[Bump]
    changelog_urls: list[str]
    min_python: tuple[int, int] = (3, 11)
    notes: list[str] = field(default_factory=list)

    @property
    def repo(self) -> Path:
        return self.path / "repo"

    @property
    def solution(self) -> Path:
        return self.path / "solution"


@dataclass
class Validation:
    case: str
    broken_as_shipped: bool
    before: str
    solution_passes: bool
    after: str
    solution_violations: list[str]

    @property
    def ok(self) -> bool:
        return self.broken_as_shipped and self.solution_passes and not self.solution_violations


def load_cases(root: Path, names: list[str] | None = None) -> list[Case]:
    if not root.is_dir():
        raise CaseError(f"no cases directory at {root}")
    cases = []
    for case_dir in sorted(p for p in root.iterdir() if (p / "case.json").is_file()):
        if names and case_dir.name not in names:
            continue
        data = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
        bumps = [Bump(b["package"], b["to"], b.get("from")) for b in data["bumps"]]
        major, minor = (int(x) for x in str(data.get("min_python", "3.11")).split("."))
        cases.append(
            Case(
                case_dir.name,
                case_dir,
                data.get("description", ""),
                bumps,
                list(data.get("changelog_urls", [])),
                (major, minor),
                list(data.get("notes", [])),
            )
        )
    missing = set(names or []) - {c.name for c in cases}
    if missing:
        raise CaseError(f"unknown case(s): {', '.join(sorted(missing))}")
    return cases


def case_python(case: Case, cache_dir: Path) -> str:
    """Build (once) a virtualenv with the case's bumped requirements and return its interpreter."""
    req_files = [case.repo / f for f in REQUIREMENT_FILES if (case.repo / f).is_file()]
    if not req_files:
        raise CaseError(f"{case.name}: repo/ has no requirements file")
    digest = hashlib.sha256(sys.version.encode())
    for f in req_files:
        digest.update(f.read_bytes())
    venv = cache_dir / "venvs" / f"{case.name}-{digest.hexdigest()[:12]}"
    python = venv / "bin" / "python"
    if python.exists():
        return str(python)
    building = venv.with_name(venv.name + ".building")
    shutil.rmtree(building, ignore_errors=True)
    print(f"[greenbump] building environment for {case.name} in {venv}", flush=True)
    subprocess.run([sys.executable, "-m", "venv", str(building)], check=True)
    pip = [str(building / "bin" / "python"), "-m", "pip", "install", "--disable-pip-version-check"]
    for f in req_files:
        pip += ["-r", str(f)]
    if subprocess.run(pip, check=False).returncode != 0:
        raise CaseError(f"{case.name}: pip install failed, see the output above")
    building.rename(venv)
    return str(python)


def supported(case: Case) -> bool:
    return sys.version_info[:2] >= case.min_python


def validate_case(case: Case, cache_dir: Path, work_root: Path) -> Validation:
    python = case_python(case, cache_dir)
    ws = Workspace(case.repo, work_root / case.name)
    before = run_pytest(ws.root, python)
    if not case.solution.is_dir():
        raise CaseError(f"{case.name}: no solution/ directory")
    for src in sorted(p for p in case.solution.rglob("*") if p.is_file()):
        rel = src.relative_to(case.solution).as_posix()
        ws.write(rel, src.read_text(encoding="utf-8"))
    ws.clear_bytecode()
    after = run_pytest(ws.root, python)
    violations = check_changes(ws.original, ws.snapshot(), {b.import_name for b in case.bumps}, Limits())
    return Validation(
        case.name, not before.ok, before.headline(), after.ok, after.headline(), [str(v) for v in violations]
    )


def run_eval(
    cases: list[Case],
    modes: list[str],
    client: ChatClient,
    out_dir: Path,
    cache_dir: Path,
    repeats: int = 1,
    budget: Budget | None = None,
    limits: Limits | None = None,
) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    started = datetime.now(UTC)
    for case in cases:
        if not supported(case):
            print(
                f"[greenbump] skip {case.name}: needs Python {'.'.join(map(str, case.min_python))}+",
                flush=True,
            )
            continue
        python = case_python(case, cache_dir)
        for mode in modes:
            for rep in range(1, repeats + 1):
                label = f"{case.name} / {mode}" + (f" / run {rep}" if repeats > 1 else "")
                print(f"[greenbump] {label} ...", flush=True)
                run_dir = out_dir / case.name / (mode if repeats == 1 else f"{mode}-{rep}")
                req = FixRequest(
                    repo=case.repo,
                    bumps=case.bumps,
                    python=python,
                    out_dir=run_dir,
                    cache_dir=cache_dir,
                    mode=mode,
                    changelog_urls=case.changelog_urls,
                    budget=budget or Budget(),
                    limits=limits or Limits(),
                )
                result = run_fix(req, client)
                print(
                    f"[greenbump] {label}: {'VERIFIED' if result.verified else 'not fixed'} "
                    f"({result.stop_reason}, {result.seconds}s)",
                    flush=True,
                )
                rows.append({"case": case.name, "repeat": rep, **_row(result)})
    meta = {
        "started": started.isoformat(timespec="seconds"),
        "finished": datetime.now(UTC).isoformat(timespec="seconds"),
        "greenbump": __version__,
        "model": client.name,
        "python": platform.python_version(),
        "platform": platform.platform(terse=True),
        "modes": modes,
        "repeats": repeats,
        "budget": vars(budget or Budget()),
    }
    (out_dir / "results.json").write_text(
        json.dumps({"meta": meta, "runs": rows}, indent=2), encoding="utf-8"
    )
    (out_dir / "summary.md").write_text(render_summary(meta, rows), encoding="utf-8")
    return rows


def _row(r: FixResult) -> dict[str, Any]:
    return {
        "mode": r.mode,
        "verified": r.verified,
        "stop_reason": r.stop_reason,
        "tests_after": r.tests_after,
        "tests_passed": r.tests_passed,
        "tests_expected": r.tests_expected,
        "steps": r.steps,
        "llm_calls": r.llm_calls,
        "prompt_tokens": r.prompt_tokens,
        "completion_tokens": r.completion_tokens,
        "seconds": r.seconds,
        "edits_applied": r.edits_applied,
        "edits_refused": r.edits_refused,
        "guardrail_hits": len(r.guardrail_hits),
        "rejected_by_verifier": [x for x in r.reasons if x.startswith("[")],
        "changed_files": r.changed_files,
    }


def render_summary(meta: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    out = [
        f"# Eval run {meta['started']}",
        "",
        f"- Model: `{meta['model']}`, greenbump {meta['greenbump']}, "
        f"Python {meta['python']}, {meta['platform']}",
        f"- Budget per agent run: {meta['budget']['max_steps']} steps, {meta['budget']['max_seconds']:.0f}s",
        "",
        "## Fix rate",
        "",
        "| Mode | Verified fixes | Cheats blocked (edits refused) | Median time (s) "
        "| Tokens in / out (total) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for mode in meta["modes"]:
        mine = [r for r in rows if r["mode"] == mode]
        if not mine:
            continue
        fixed = sum(r["verified"] for r in mine)
        out.append(
            f"| {mode} | {fixed}/{len(mine)} | {sum(r['edits_refused'] for r in mine)} | "
            f"{statistics.median(r['seconds'] for r in mine):.0f} | "
            f"{sum(r['prompt_tokens'] for r in mine):,} / {sum(r['completion_tokens'] for r in mine):,} |"
        )
    out += [
        "",
        "## Per case",
        "",
        "| Case | Mode | Verified | Stopped because | Tests after | Steps | Model calls "
        "| Tokens in / out | Time (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        out.append(
            f"| {r['case']} | {r['mode']} | {'yes' if r['verified'] else 'no'} | {r['stop_reason']} | "
            f"{r['tests_passed']}/{r['tests_expected']} | {r['steps']} | {r['llm_calls']} | "
            f"{r['prompt_tokens']:,} / {r['completion_tokens']:,} | {r['seconds']:.0f} |"
        )
    return "\n".join(out) + "\n"


def timestamp_dir(root: Path, model: str) -> Path:
    slug = "".join(ch if ch.isalnum() or ch in "-." else "-" for ch in model)
    return root / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}"
