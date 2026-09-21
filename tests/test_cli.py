from ag_vis.cli import _poll_once, _seed_cursors, build_parser
from ag_vis.demo import DEMO_EVENTS
from ag_vis.laya_adapter import classify_with_laya
from ag_vis.server import StateStore


def test_parser_defaults_to_localhost():
    args = build_parser().parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8765


def test_parser_accepts_demo_without_opening_browser():
    args = build_parser().parse_args(["--demo", "--no-open", "--laya"])
    assert args.demo is True
    assert args.no_open is True
    assert args.laya is True


def test_demo_has_a_complete_visual_story():
    assert DEMO_EVENTS[0]["type"] == "turn_started"
    assert any(event["type"] == "tool_error" for event in DEMO_EVENTS)
    assert DEMO_EVENTS[-1]["type"] == "turn_completed"


def test_laya_failure_returns_none(monkeypatch):
    def fail():
        raise RuntimeError("model unavailable")

    monkeypatch.setattr("ag_vis.laya_adapter._load_router", fail)
    assert classify_with_laya({"type": "unknown"}) is None


def test_new_session_resets_completed_progress(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    root = tmp_path / "sessions"
    root.mkdir()
    first = root / "first.jsonl"
    first.write_text(
        f'{{"cwd":"{workspace}","type":"turn_completed"}}\n'
    )
    store = StateStore()
    cursors = {}
    active = _poll_once(store, root, workspace, cursors, None, None, None)
    assert store.snapshot()[1].progress == 1

    second = root / "second.jsonl"
    second.write_text(f'{{"cwd":"{workspace}","type":"turn_started"}}\n')
    active = _poll_once(store, root, workspace, cursors, active, None, None)
    assert active == second
    state = store.snapshot()[1]
    assert state.phase == "planning"
    assert state.progress == 0.08


def test_seed_cursors_start_existing_sessions_at_live_tail(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    root = tmp_path / "sessions"
    root.mkdir()
    existing = root / "existing.jsonl"
    existing.write_text(f'{{"cwd":"{workspace}","type":"turn_completed"}}\n')
    cursors, active = _seed_cursors(root, workspace)
    assert active == existing
    assert cursors[existing].offset == existing.stat().st_size


def test_prompt_event_invokes_popup_callback(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    root = tmp_path / "sessions"
    root.mkdir()
    session = root / "session.jsonl"
    session.write_text(
        f'{{"cwd":"{workspace}","type":"event_msg","payload":{{"type":"item_completed","item":{{"type":"UserMessage"}}}}}}\n'
    )
    calls = []
    store = StateStore()
    active = _poll_once(store, root, workspace, {}, None, None, lambda: calls.append("open"))
    assert active == session
    assert calls == ["open"]
    assert store.snapshot()[1].phase == "planning"
