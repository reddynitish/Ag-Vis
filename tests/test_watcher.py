import threading

from ag_vis.watcher import (
    discover_sessions,
    follow_jsonl,
    read_appended_events,
    read_complete_records,
    sanitize_record,
)


def test_sanitize_record_drops_payload_content():
    result = sanitize_record(
        {
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "apply_patch",
                "arguments": "SECRET",
            },
        }
    )
    assert result == {"type": "function_call", "name": "apply_patch"}
    assert "SECRET" not in repr(result)


def test_sanitize_unknown_tool_drops_its_name_and_arguments():
    result = sanitize_record(
        {"type": "function_call", "name": "dangerous_tool", "arguments": "SECRET"}
    )
    assert result == {"type": "function_call"}


def test_partial_jsonl_waits_for_newline(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text('{"type":"turn_started"}')
    assert list(read_complete_records(path)) == []


def test_complete_records_ignore_malformed_lines(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text('not json\n{"type":"turn_started"}\n')
    assert list(read_complete_records(path)) == [{"type": "turn_started"}]


def test_discovery_filters_by_workspace(tmp_path):
    wanted = tmp_path / "wanted.jsonl"
    other = tmp_path / "other.jsonl"
    wanted.write_text('{"cwd":"/project/a"}\n')
    other.write_text('{"cwd":"/project/b"}\n')
    assert discover_sessions(tmp_path, "/project/a") == [wanted]


def test_follow_jsonl_yields_sanitized_events(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text('{"type":"turn_started","body":"SECRET"}\n')
    stop = threading.Event()
    stop.set()
    assert list(follow_jsonl(path, stop)) == [{"type": "turn_started"}]


def test_appended_reader_tracks_offset_and_handles_rotation(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text('{"type":"function_call","name":"apply_patch"}\n')
    events, offset = read_appended_events(path, 0)
    assert events == [{"type": "function_call", "name": "apply_patch"}]
    path.write_text('{"type":"turn_completed"}\n')
    events, new_offset = read_appended_events(path, offset)
    assert events == [{"type": "turn_completed"}]
    assert new_offset > 0


def test_appended_reader_tolerates_disappearing_file(tmp_path):
    assert read_appended_events(tmp_path / "gone.jsonl", 10) == ([], 0)
