from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .model import VisualState


PHASE_DETAILS = {
    "planning": ("Planning the structure.", 0.08),
    "researching": ("Inspecting the project.", 0.24),
    "building": ("Building the main structure.", 0.48),
    "testing": ("Checking whether it works.", 0.76),
    "repairing": ("A check failed. Repairing it.", 0.72),
}


def _rule(event: Mapping[str, Any]) -> tuple[str, str, float, str] | None:
    event_type = str(event.get("type", "unknown"))
    name = str(event.get("name", ""))

    if event_type in {"turn_completed", "task_complete", "completed"}:
        return "finished", "Finished building.", 1.0, "finished"
    if event_type in {"tool_error", "error", "command_error"}:
        return "repairing", "A check failed. Repairing it.", 0.72, "working"
    if event_type in {"approval_denied", "blocked", "permission_denied"}:
        return "blocked", "Blocked. Waiting for a safe next step.", 0.5, "blocked"
    if event_type in {"turn_started", "task_started"}:
        return "planning", "Planning the structure.", 0.08, "working"
    if event_type == "user_prompt":
        return "planning", "I got your prompt. Mapping the build.", 0.02, "working"
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
    return None


def classify_event(
    event: Mapping[str, Any],
    previous: VisualState,
    ambiguity_classifier: Callable[[dict[str, str]], str | None] | None = None,
) -> VisualState:
    result = _rule(event)
    if result is None and ambiguity_classifier is not None:
        public_event = {key: str(event[key]) for key in ("type", "name") if key in event}
        phase = ambiguity_classifier(public_event)
        if phase in PHASE_DETAILS:
            message, target = PHASE_DETAILS[phase]
            result = phase, message, target, "working"
    if result is None:
        result = "working", "Working on the next piece.", 0.12, "working"
    phase, message, target, status = result
    progress = 1.0 if status == "finished" else min(0.98, max(previous.progress, target))
    return VisualState(phase, message, progress, status)
