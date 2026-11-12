"""Markdown reports for a single fix and for an eval run."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .context import truncate_middle
from .models import TestRun

if TYPE_CHECKING:
    from .fixer import FixResult


def render_report(result: FixResult, final_tests: TestRun | None) -> str:
    verdict = "VERIFIED FIX" if result.verified else "NOT FIXED"
    out = [
        f"# greenbump: {verdict}",
        "",
        f"- Mode: `{result.mode}`, model: `{result.model}`",
        f"- Agent stopped because: `{result.stop_reason}`",
        f"- Tests before: {result.tests_before}",
        f"- Tests after: {result.tests_after} (repository defines {result.tests_expected} test functions)",
        f"- Steps: {result.steps}, model calls: {result.llm_calls}, "
        f"tokens in/out: {result.prompt_tokens}/{result.completion_tokens}, time: {result.seconds}s",
        f"- Edits applied: {result.edits_applied}, edits refused by guardrails: {result.edits_refused}",
        "",
    ]
    if result.reasons:
        out += ["## Why it does not count as a fix", *(f"- {r}" for r in result.reasons), ""]
    if result.summary:
        out += ["## Model's summary", "", result.summary.strip(), ""]
    if result.guardrail_hits:
        out += ["## Guardrail hits during the run", *(f"- {h}" for h in result.guardrail_hits), ""]
    if result.diff:
        out += ["## Patch", "", "```diff", result.diff.rstrip(), "```", ""]
    if result.changelog_sources:
        out += ["## Changelog sources (untrusted)", *(f"- {s['url']}" for s in result.changelog_sources), ""]
    if result.warnings:
        out += ["## Warnings", *(f"- {w}" for w in result.warnings), ""]
    if result.error:
        out += ["## Error", "", result.error, ""]
    if final_tests is not None and not final_tests.ok:
        out += [
            "## Final test output",
            "",
            "```text",
            truncate_middle(final_tests.output.strip(), 6000),
            "```",
            "",
        ]
    return "\n".join(out)
