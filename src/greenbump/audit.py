"""Append-only JSON Lines record of every model reply and tool call."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, target: Path | None) -> None:
        self.target = target
        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")

    def write(self, event: str, **fields: Any) -> None:
        if self.target is None:
            return
        record = {"ts": round(time.time(), 3), "event": event, **fields}
        with self.target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
