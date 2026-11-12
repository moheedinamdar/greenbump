"""Command line interface."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import __version__
from .agent import Budget
from .changelog import ChangelogCache, ChangelogIndex, load_docs
from .context import build_case
from .evals import CaseError, load_cases, run_eval, supported, timestamp_dir, validate_case
from .fixer import MODES, FixRequest, run_fix
from .guardrails import Limits
from .llm import LLMError, build_client
from .models import Bump
from .runner import run_pytest
from .workspace import Workspace, WorkspaceError

DEFAULT_CACHE = Path(".greenbump-cache")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        code: int = args.func(args)
        return code
    except (CaseError, LLMError, WorkspaceError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="greenbump", description="Fix Python code broken by a dependency upgrade."
    )
    p.add_argument("--version", action="version", version=f"greenbump {__version__}")
    sub = p.add_subparsers(required=True)

    def target(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--repo", type=Path, required=True, help="repository whose tests fail after the bump")
        sp.add_argument(
            "--bump",
            action="append",
            required=True,
            metavar="NAME:[FROM:]TO",
            help="upgraded package, e.g. pydantic:1.10.27:2.14.3 (repeatable)",
        )
        sp.add_argument("--python", help="interpreter with the NEW versions installed (default: REPO/.venv)")
        sp.add_argument(
            "--changelog-url",
            action="append",
            default=[],
            help="raw changelog or migration guide URL (repeatable; default: discover via PyPI)",
        )
        sp.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
        sp.add_argument("--test-timeout", type=float, default=180.0)

    def model(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--provider", choices=["ollama", "openai"], default="ollama")
        sp.add_argument("--model", help="model name (default: qwen2.5:7b on Ollama, or GREENBUMP_MODEL)")
        sp.add_argument("--base-url", help="override OLLAMA_BASE_URL / OPENAI_BASE_URL")
        sp.add_argument("--max-steps", type=int, default=Budget.max_steps)
        sp.add_argument("--max-seconds", type=float, default=Budget.max_seconds)

    ctx = sub.add_parser("context", help="Phase 1 only: print the case file the model would get (no LLM)")
    target(ctx)
    ctx.set_defaults(func=_cmd_context)

    fix = sub.add_parser("fix", help="try to fix the repository; writes a patch and a report")
    target(fix)
    model(fix)
    fix.add_argument("--mode", choices=MODES, default="agent")
    fix.add_argument("--out", type=Path, help="output directory (default: .greenbump/runs/<timestamp>)")
    fix.set_defaults(func=_cmd_fix)

    ev = sub.add_parser("eval", help="benchmark cases: validate them, or run single-shot vs agent")
    ev_sub = ev.add_subparsers(required=True)
    val = ev_sub.add_parser("validate", help="prove each case is broken as shipped and fixed by its solution")
    val.add_argument("--cases", type=Path, default=Path("evals/cases"))
    val.add_argument("--case", action="append", help="only this case (repeatable)")
    val.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    val.set_defaults(func=_cmd_validate)
    run = ev_sub.add_parser("run", help="run the model on every case and write a results table")
    run.add_argument("--cases", type=Path, default=Path("evals/cases"))
    run.add_argument("--case", action="append", help="only this case (repeatable)")
    run.add_argument("--modes", default="single-shot,agent", help="comma separated: single-shot,agent")
    run.add_argument("--repeats", type=int, default=1)
    run.add_argument("--out", type=Path, default=Path("evals/results"))
    run.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    model(run)
    run.set_defaults(func=_cmd_eval_run)
    return p


def _python_for(args: argparse.Namespace) -> str:
    if args.python:
        return str(args.python)
    venv = Path(args.repo) / ".venv" / "bin" / "python"
    if venv.exists():
        return str(venv)
    raise ValueError(
        f"no --python given and {venv} does not exist. Point --python at an interpreter "
        "that has the upgraded package installed."
    )


def _cmd_context(args: argparse.Namespace) -> int:
    bumps = [Bump.parse(s) for s in args.bump]
    out = Path(".greenbump") / "context" / time.strftime("%Y%m%d-%H%M%S")
    ws = Workspace(args.repo, out / "work")
    tests = run_pytest(ws.root, _python_for(args), args.test_timeout)
    if tests.ok:
        print(f"Tests already pass ({tests.headline()}). Nothing to fix.")
        return 0
    docs, warnings = load_docs(bumps, args.changelog_url, ChangelogCache(args.cache_dir))
    print(build_case(ws, bumps, tests, ChangelogIndex(docs, bumps), warnings).render())
    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
    return 0


def _cmd_fix(args: argparse.Namespace) -> int:
    client = build_client(args.provider, args.model, args.base_url)
    out = args.out or Path(".greenbump") / "runs" / time.strftime("%Y%m%d-%H%M%S")
    req = FixRequest(
        repo=args.repo,
        bumps=[Bump.parse(s) for s in args.bump],
        python=_python_for(args),
        out_dir=out,
        cache_dir=args.cache_dir,
        mode=args.mode,
        changelog_urls=args.changelog_url,
        budget=Budget(args.max_steps, args.max_seconds),
        limits=Limits(),
        test_timeout=args.test_timeout,
    )
    result = run_fix(req, client)
    print(
        f"{'VERIFIED FIX' if result.verified else 'NOT FIXED'}: {result.tests_before} -> {result.tests_after}"
    )
    for reason in result.reasons:
        print(f"  - {reason}")
    print(f"Report: {out / 'report.md'}\nPatch:  {out / 'patch.diff'}\nAudit:  {out / 'audit.jsonl'}")
    return 0 if result.verified else 1


def _cmd_validate(args: argparse.Namespace) -> int:
    cases = load_cases(args.cases, args.case)
    work_root = Path(".greenbump") / "validate" / time.strftime("%Y%m%d-%H%M%S")
    failures = 0
    for case in cases:
        if not supported(case):
            print(f"SKIP {case.name}: needs Python {'.'.join(map(str, case.min_python))}+")
            continue
        v = validate_case(case, args.cache_dir, work_root)
        failures += not v.ok
        print(
            f"{'OK  ' if v.ok else 'FAIL'} {case.name}: as shipped [{v.before}] -> with solution [{v.after}]"
        )
        for violation in v.solution_violations:
            print(f"     solution breaks a guardrail: {violation}")
    return 1 if failures else 0


def _cmd_eval_run(args: argparse.Namespace) -> int:
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    unknown = set(modes) - set(MODES)
    if unknown:
        raise ValueError(f"unknown mode(s): {', '.join(sorted(unknown))}")
    client = build_client(args.provider, args.model, args.base_url)
    out = timestamp_dir(args.out, client.name)
    rows = run_eval(
        load_cases(args.cases, args.case),
        modes,
        client,
        out,
        args.cache_dir,
        args.repeats,
        Budget(args.max_steps, args.max_seconds),
        Limits(),
    )
    print((out / "summary.md").read_text(encoding="utf-8"))
    print(f"Results: {out}")
    return 0 if rows else 1
