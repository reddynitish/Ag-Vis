from ag_vis.cli import build_parser
from ag_vis.demo import DEMO_EVENTS
from ag_vis.laya_adapter import classify_with_laya


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
