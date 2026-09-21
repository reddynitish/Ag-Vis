from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
import re
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
TOOL_CALL_RE = re.compile(r"tools\.(\w+)\(")


@dataclass(frozen=True, slots=True)
class TailCursor:
    offset: int = 0
    identity: tuple[int, int] | None = None


def sanitize_records(record: Mapping[str, Any]) -> list[dict[str, str]]:
    payload = record.get("payload")
    source = payload if isinstance(payload, Mapping) else record
    event_type = str(source.get("type", record.get("type", "unknown")))
    if record.get("type") == "event_msg" and event_type == "item_completed":
        item = source.get("item")
        if isinstance(item, Mapping) and item.get("type") == "UserMessage":
            return [{"type": "user_prompt"}]
    if record.get("type") == "event_msg" and event_type == "task_complete":
        return [{"type": "turn_completed"}]
    if record.get("type") == "event_msg" and event_type == "task_started":
        return [{"type": "turn_started"}]
    if event_type == "custom_tool_call" and source.get("name") == "exec":
        raw = source.get("input", "")
        names = TOOL_CALL_RE.findall(raw) if isinstance(raw, str) else []
        return [
            {"type": "function_call", "name": name}
            for name in names
            if name in ALLOWED_TOOL_NAMES
        ] or [{"type": "function_call"}]
    result = {"type": event_type}
    name = source.get("name")
    if isinstance(name, str) and name in ALLOWED_TOOL_NAMES:
        result["name"] = name
    if event_type in {"reasoning", "message", "token_count", "item_completed", "custom_tool_call_output", "function_call_output"}:
        return []
    return [result]


def sanitize_record(record: Mapping[str, Any]) -> dict[str, str] | None:
    records = sanitize_records(record)
    return records[0] if records else None


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


def read_appended_events(path: Path, offset: int) -> tuple[list[dict[str, str]], int]:
    events, cursor = read_tail_events(path, TailCursor(offset=offset))
    return events, cursor.offset


def read_tail_events(path: Path, cursor: TailCursor) -> tuple[list[dict[str, str]], TailCursor]:
    try:
        stat = path.stat()
        identity = (stat.st_dev, stat.st_ino)
        offset = cursor.offset if cursor.identity in {None, identity} else 0
        size = stat.st_size
        if size < offset:
            offset = 0
        events: list[dict[str, str]] = []
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
                    events.extend(sanitize_records(record))
        return events, TailCursor(offset, identity)
    except OSError:
        return [], TailCursor()


def follow_jsonl(path: Path, stop_event: threading.Event) -> Iterator[dict[str, str]]:
    offset = 0
    while True:
        events, offset = read_appended_events(path, offset)
        yield from events
        if stop_event.is_set():
            return
        time.sleep(0.15)
