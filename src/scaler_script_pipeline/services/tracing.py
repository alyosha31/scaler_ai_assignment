from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TraceStore:
    def __init__(self, trace_dir: str, enabled: bool = True) -> None:
        self.trace_dir = Path(trace_dir)
        self.enabled = enabled
        if self.enabled:
            self.trace_dir.mkdir(parents=True, exist_ok=True)

    def record_span(
        self,
        *,
        name: str,
        kind: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
        started_at: str | None = None,
        elapsed_ms: int | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        trace = {
            "trace_id": f"trace_{uuid4().hex[:12]}",
            "name": name,
            "kind": kind,
            "status": "ERROR" if error else "OK",
            "started_at": started_at or utcnow_iso(),
            "ended_at": utcnow_iso(),
            "elapsed_ms": elapsed_ms,
            "metadata": metadata or {},
            "inputs": inputs,
            "outputs": outputs or {},
            "error": error,
        }
        path = self.trace_dir / f"{trace['trace_id']}.json"
        path.write_text(json.dumps(trace, indent=2, default=str), encoding="utf-8")
        return trace

    def list_traces(self, limit: int = 50, project_id: str | None = None) -> list[dict[str, Any]]:
        if not self.enabled or not self.trace_dir.exists():
            return []
        traces: list[dict[str, Any]] = []
        for path in sorted(self.trace_dir.glob("trace_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            trace = json.loads(path.read_text(encoding="utf-8"))
            if project_id and trace.get("metadata", {}).get("project_id") != project_id:
                continue
            traces.append(_summary(trace))
            if len(traces) >= limit:
                break
        return traces

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        path = self.trace_dir / f"{trace_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


class TraceTimer:
    def __init__(self) -> None:
        self.started_at = utcnow_iso()
        self._start = time.perf_counter()

    @property
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)


def _summary(trace: dict[str, Any]) -> dict[str, Any]:
    metadata = trace.get("metadata", {})
    return {
        "trace_id": trace.get("trace_id"),
        "name": trace.get("name"),
        "kind": trace.get("kind"),
        "status": trace.get("status"),
        "started_at": trace.get("started_at"),
        "elapsed_ms": trace.get("elapsed_ms"),
        "project_id": metadata.get("project_id"),
        "segment_id": metadata.get("segment_id"),
        "response_model": metadata.get("response_model"),
    }
