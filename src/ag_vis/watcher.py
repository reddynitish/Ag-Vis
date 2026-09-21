from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any


ALLOWED_TOOL_NAMES = {
    "apply_patch",
    "exec_command",
    "write_stdin",
    "view_image",
    "imagegen",
}


def sanitize_record(record: Mapping[str, Any]) -> dict[str, str] | None:
    payload = record.get("payload")
    source = payload if isinstance(payload, Mapping) else record
    event_type = str(source.get("type", record.get("type", "unknown")))
    result = {"type": event_type}
    name = source.get("name")
    if isinstance(name, str) and name in ALLOWED_TOOL_NAMES:
        result["name"] = name
    return result


def read_complete_records(path: Path, start: int = 0) -> Iterator[dict[str, Any]]:
    with path.open("rb") as stream:
        stream.seek(start)
        for raw_line in stream:
            if not raw_line.endswith(b"\n"):
                break
            try:
                record = json.loads(raw_line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(record, dict):
                yield record


def _mentions_workspace(path: Path, workspace: str) -> bool:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as stream:
            for _ in range(20):
                line = stream.readline()
                if not line:
                    break
                if workspace in line:
                    return True
    except OSError:
        return False
    return False


def discover_sessions(root: Path, workspace: str | Path) -> list[Path]:
    if not root.exists():
        return []
    workspace_text = str(Path(workspace).resolve())
    matches = [path for path in root.rglob("*.jsonl") if _mentions_workspace(path, workspace_text)]
    return sorted(matches, key=lambda path: path.stat().st_mtime)


def follow_jsonl(path: Path, stop_event: threading.Event) -> Iterator[dict[str, str]]:
    offset = 0
    while True:
        try:
            size = path.stat().st_size
        except OSError:
            size = offset
        if size < offset:
            offset = 0
        with path.open("rb") as stream:
            stream.seek(offset)
            while True:
                position = stream.tell()
                line = stream.readline()
                if not line or not line.endswith(b"\n"):
                    stream.seek(position)
                    break
                offset = stream.tell()
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if isinstance(record, dict):
                    public = sanitize_record(record)
                    if public is not None:
                        yield public
        if stop_event.is_set():
            return
        time.sleep(0.15)
