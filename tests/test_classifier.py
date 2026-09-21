from ag_vis.classifier import classify_event
from ag_vis.model import VisualState, public_dict


def test_tool_call_becomes_building_state():
    state = classify_event(
        {"type": "function_call", "name": "apply_patch"}, VisualState.initial()
    )
    assert state.phase == "building"
    assert state.message == "Building the main structure."


def test_progress_never_moves_backwards():
    previous = VisualState(
        phase="testing",
        message="Checking whether it works.",
        progress=0.8,
        status="working",
    )
    state = classify_event({"type": "agent_message"}, previous)
    assert state.progress == 0.8


def test_public_state_has_allowlisted_fields_only():
    assert set(public_dict(VisualState.initial())) == {
        "phase",
        "message",
        "progress",
        "status",
        "timestamp",
    }


def test_completion_is_the_only_event_that_reaches_one_hundred_percent():
    working = classify_event({"type": "function_call", "name": "apply_patch"}, VisualState.initial())
    complete = classify_event({"type": "turn_completed"}, working)
    assert working.progress < 1
    assert complete.progress == 1
    assert complete.status == "finished"


def test_approval_denial_becomes_blocked_state():
    state = classify_event({"type": "approval_denied"}, VisualState.initial())
    assert state.phase == "blocked"
    assert state.status == "blocked"
    assert state.message == "Blocked. Waiting for a safe next step."


def test_unknown_event_can_use_valid_laya_fallback():
    state = classify_event(
        {"type": "mystery"},
        VisualState.initial(),
        ambiguity_classifier=lambda event: "researching",
    )
    assert state.phase == "researching"


def test_invalid_laya_phase_falls_back_to_working():
    state = classify_event(
        {"type": "mystery"},
        VisualState.initial(),
        ambiguity_classifier=lambda event: "SECRET PHASE",
    )
    assert state.phase == "working"
