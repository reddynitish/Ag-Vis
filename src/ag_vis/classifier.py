from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .model import VisualState


def _rule(event: Mapping[str, Any]) -> tuple[str, str, float, str]:
    event_type = str(event.get("type", "unknown"))
    name = str(event.get("name", ""))

    if event_type in {"turn_completed", "task_complete", "completed"}:
        return "finished", "Finished building.", 1.0, "finished"
    if event_type in {"tool_error", "error", "command_error"}:
        return "repairing", "A check failed. Repairing it.", 0.72, "working"
    if event_type in {"turn_started", "task_started"}:
        return "planning", "Planning the structure.", 0.08, "working"
    if event_type in {"approval_request", "user_input_request"}:
        return "waiting", "Waiting for your direction.", 0.5, "waiting"
    if event_type == "function_call":
        if name in {"apply_patch", "write_file", "edit_file"}:
            return "building", "Building the main structure.", 0.48, "working"
        if name in {"exec_command", "write_stdin"}:
            return "testing", "Checking whether it works.", 0.76, "working"
        return "researching", "Inspecting the project.", 0.24, "working"
    if event_type in {"agent_message", "assistant_message"}:
        return "planning", "Working out the next step.", 0.18, "working"
    return "working", "Working on the next piece.", 0.12, "working"


def classify_event(event: Mapping[str, Any], previous: VisualState) -> VisualState:
    phase, message, target, status = _rule(event)
    progress = 1.0 if status == "finished" else min(0.98, max(previous.progress, target))
    return VisualState(phase, message, progress, status)
