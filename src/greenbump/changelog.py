"""Fetch upstream changelogs and migration guides, cache them, and search them with BM25.

Everything fetched here is untrusted text from the internet. It is only ever shown to the
model wrapped in <untrusted> tags, and nothing in it can widen what the agent may do.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from . import net
from .models import Bump

CANDIDATE_FILES = (
    "CHANGELOG.md",
    "CHANGES.md",
    "CHANGES.rst",
    "CHANGELOG.rst",
    "HISTORY.md",
    "HISTORY.rst",
    "NEWS.md",
    "NEWS.rst",
    "docs/changelog.md",
    "docs/changelog.rst",
    "docs/changes.rst",
)
_GITHUB_RE = re.compile(r"^https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:[/#?]|$)")
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_HEADING_RE = re.compile(r"^(#{1,6} |[=\-~^*]{4,}\s*$|Version \d|v?\d+\.\d+(\.\d+)?\b)")
_VERSION_HEAD_RE = re.compile(r"^\s*(?:#+\s*)?(?:Version\s+|Release\s+|v)?(\d+)\.(\d+)(?:\.(\d+))?\b")
_UNDERLINE_RE = re.compile(r"^\s*([-=*~^#])\1{2,}\s*$")
_MIGRATION_RE = re.compile(r"deprecat|remov|renam|replac|instead|no longer", re.IGNORECASE)
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "use",
    "used",
    "are",
    "was",
    "not",
    "now",
    "has",
    "have",
    "can",
    "will",
    "you",
    "your",
    "its",
    "into",
    "when",
    "which",
    "instead",
    "of",
    "to",
    "in",
    "is",
    "be",
    "a",
    "an",
    "or",
    "on",
    "as",
    "by",
    "it",
    "if",
    "no",
    "e",
    "g",
}


@dataclass(frozen=True)
class Doc:
    url: str
    text: str
    sha256: str


@dataclass(frozen=True)
class Passage:
    url: str
    line: int
    text: str
    score: float


class ChangelogCache:
    """Fetch each URL once and keep it on disk, so eval runs see identical text."""

    def __init__(self, cache_dir: Path) -> None:
        self.dir = cache_dir / "changelogs"

    def fetch(self, url: str) -> Doc | None:
        """Return the document, or None when the URL does not exist (HTTP 404)."""
        key = hashlib.sha256(url.encode()).hexdigest()[:24]
        body_file, meta_file = self.dir / f"{key}.txt", self.dir / f"{key}.json"
        if body_file.is_file():
            text = body_file.read_text(encoding="utf-8")
        else:
            try:
                text = net.get_text(url)
            except net.NetworkError as exc:
                if exc.status == 404:
                    return None
                raise
            self.dir.mkdir(parents=True, exist_ok=True)
            body_file.write_text(text, encoding="utf-8")
            meta_file.write_text(json.dumps({"url": url}), encoding="utf-8")
        return Doc(url=url, text=text, sha256=hashlib.sha256(text.encode()).hexdigest())


def discover_urls(bump: Bump) -> list[str]:
    """Guess raw changelog URLs from the GitHub repository listed on PyPI."""
    info = (net.get_json(f"https://pypi.org/pypi/{quote(bump.package)}/json") or {}).get("info") or {}
    candidates = [*(info.get("project_urls") or {}).values(), info.get("home_page") or ""]
    for url in candidates:
        match = _GITHUB_RE.match(str(url))
        if match:
            owner, repo = match.groups()
            return [f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{f}" for f in CANDIDATE_FILES]
    return []


def load_docs(
    bumps: list[Bump], urls: list[str], cache: ChangelogCache, max_auto_docs: int = 2
) -> tuple[list[Doc], list[str]]:
    """Fetch explicit URLs, or discover per package when none are given. Returns docs and warnings."""
    docs: list[Doc] = []
    warnings: list[str] = []
    if urls:
        for url in urls:
            try:
                doc = cache.fetch(url)
            except net.NetworkError as exc:
                warnings.append(f"could not fetch {url}: {exc}")
                continue
            if doc is None:
                warnings.append(f"not found: {url}")
            else:
                docs.append(doc)
        return docs, warnings
    for bump in bumps:
        try:
            candidates = discover_urls(bump)
        except net.NetworkError as exc:
            warnings.append(f"PyPI lookup failed for {bump.package}: {exc}")
            continue
        found = 0
        for url in candidates:
            try:
                doc = cache.fetch(url)
            except net.NetworkError as exc:
                warnings.append(f"could not fetch {url}: {exc}")
                continue
            if doc is not None:
                docs.append(doc)
                found += 1
                if found >= max_auto_docs:
                    break
        if not found:
            warnings.append(f"no changelog found for {bump.package}; pass --changelog-url")
    return docs, warnings


def tokens(text: str) -> list[str]:
    out: list[str] = []
    for tok in _TOKEN_RE.findall(text):
        low = tok.lower()
        if low in _STOPWORDS or len(low) < 2:
            continue
        out.append(low)
        stripped = low.strip("_")
        if stripped != low and len(stripped) >= 2:
            out.append(stripped)
    return out


class ChangelogIndex:
    """BM25 over paragraph-sized chunks, weighted by which release each chunk belongs to.

    Notes released after the old version matter most. Notes from the same major line still
    matter, because "removed" entries often just say "remove previously deprecated code" and
    the useful detail is in the earlier deprecation notice. Much older notes matter least.
    """

    def __init__(self, docs: list[Doc], bumps: list[Bump] | None = None, chunk_chars: int = 900) -> None:
        self.chunks: list[tuple[str, int, str]] = []
        self._weights: list[float] = []
        for doc in docs:
            bump = _bump_for(doc.url, bumps or [])
            marks = _version_marks(doc.text.splitlines())
            for line, text in _chunk(doc.text, chunk_chars):
                self.chunks.append((doc.url, line, text))
                weight = version_weight(marks[line - 1] if marks else None, bump)
                self._weights.append(weight * (1.3 if _MIGRATION_RE.search(text) else 1.0))
        self._tfs = [Counter(tokens(text)) for _, _, text in self.chunks]
        self._lens = [sum(tf.values()) for tf in self._tfs]
        self._avg = (sum(self._lens) / len(self._lens)) if self._lens else 1.0
        df: Counter[str] = Counter()
        for tf in self._tfs:
            df.update(tf.keys())
        n = len(self.chunks)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def __len__(self) -> int:
        return len(self.chunks)

    def search(self, query: str, k: int = 4) -> list[Passage]:
        q_terms = set(tokens(query))
        if not q_terms or not self.chunks:
            return []
        k1, b = 1.2, 0.75
        scored: list[Passage] = []
        for i, (url, line, text) in enumerate(self.chunks):
            tf = self._tfs[i]
            score = 0.0
            for term in q_terms:
                f = tf.get(term, 0)
                if f:
                    norm = f + k1 * (1 - b + b * self._lens[i] / self._avg)
                    score += self._idf.get(term, 0.0) * f * (k1 + 1) / norm
            if score and query.strip() and query.strip() in text:
                score += 2.0
            score *= self._weights[i]
            if score > 0:
                scored.append(Passage(url=url, line=line, text=text, score=score))
        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:k]


def version_weight(version: tuple[int, ...] | None, bump: Bump | None) -> float:
    if version is None or bump is None:
        return 1.0
    v = _pad(version)
    if v > _pad(_parse_version(bump.to_version) or ()):
        return 0.5
    old = _parse_version(bump.from_version or "")
    if old is None:
        return 1.0
    if v > _pad(old):
        return 1.5
    return 1.0 if v[0] == old[0] else 0.3


def _parse_version(text: str) -> tuple[int, ...] | None:
    m = re.match(r"v?(\d+)\.(\d+)(?:\.(\d+))?", text.strip())
    return tuple(int(g) for g in m.groups() if g is not None) if m else None


def _pad(v: tuple[int, ...]) -> tuple[int, ...]:
    return (*v, 0, 0, 0)[:3] if v else (10**9,)


def _bump_for(url: str, bumps: list[Bump]) -> Bump | None:
    low = url.lower()
    matches = [b for b in bumps if b.package.lower() in low or b.import_name.lower() in low]
    return max(matches, key=lambda b: len(b.package)) if matches else None


def _version_marks(lines: list[str]) -> list[tuple[int, ...] | None]:
    """For every line, the release heading it sits under (None before the first heading)."""
    marks: list[tuple[int, ...] | None] = []
    current: tuple[int, ...] | None = None
    for i, line in enumerate(lines):
        m = _VERSION_HEAD_RE.match(line)
        underlined = i + 1 < len(lines) and _UNDERLINE_RE.match(lines[i + 1]) is not None
        if m and (underlined or line.lstrip().startswith(("#", "Version", "Release"))):
            current = tuple(int(g) for g in m.groups() if g is not None)
        marks.append(current)
    return marks


def render_passages(passages: list[Passage]) -> str:
    if not passages:
        return "(no matching passages)"
    blocks = []
    for p in passages:
        body = p.text.replace("</untrusted>", "</ untrusted>")
        blocks.append(f'<untrusted source="{p.url}#L{p.line}">\n{body}\n</untrusted>')
    return "\n\n".join(blocks)


def _chunk(text: str, max_chars: int) -> list[tuple[int, str]]:
    """Split on blank lines and headings, then merge small paragraphs up to ``max_chars``."""
    paragraphs: list[tuple[int, list[str]]] = []
    current: list[str] = []
    start = 1
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or (_HEADING_RE.match(line) and current):
            if current:
                paragraphs.append((start, current))
            current = [line] if line.strip() else []
            start = number
            continue
        if not current:
            start = number
        current.append(line)
    if current:
        paragraphs.append((start, current))

    chunks: list[tuple[int, str]] = []
    buf: list[str] = []
    buf_start = 1
    for para_start, lines in paragraphs:
        para = "\n".join(lines)
        if buf and len("\n".join(buf)) + len(para) > max_chars:
            chunks.append((buf_start, "\n".join(buf)))
            buf = []
        if not buf:
            buf_start = para_start
        buf.append(para if len(para) <= max_chars * 2 else para[: max_chars * 2])
    if buf:
        chunks.append((buf_start, "\n".join(buf)))
    return chunks
