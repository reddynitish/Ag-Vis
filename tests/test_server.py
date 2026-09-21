import json
import threading
from urllib.request import urlopen

import pytest

from ag_vis.model import VisualState
from ag_vis.server import StateStore, create_server


@pytest.fixture
def running_server():
    store = StateStore()
    server = create_server("127.0.0.1", 0, store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", store
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_health_endpoint(running_server):
    base, _ = running_server
    response = urlopen(base + "/health")
    assert response.read() == b'{"ok":true}'


def test_state_endpoint_contains_only_public_state(running_server):
    base, _ = running_server
    payload = json.load(urlopen(base + "/api/state"))
    assert set(payload) == {"phase", "message", "progress", "status", "timestamp"}


def test_published_state_is_returned(running_server):
    base, store = running_server
    store.publish(VisualState("building", "Building the main structure.", 0.5, "working"))
    payload = json.load(urlopen(base + "/api/state"))
    assert payload["phase"] == "building"
    assert payload["message"] == "Building the main structure."


def test_unknown_routes_return_not_found(running_server):
    base, _ = running_server
    with pytest.raises(Exception) as error:
        urlopen(base + "/missing")
    assert getattr(error.value, "code", None) == 404


def test_wait_after_timeout_does_not_change_revision():
    store = StateStore()
    revision, _ = store.wait_after(0, timeout=0.001)
    assert revision == 0


def test_store_preserves_every_state_after_revision():
    store = StateStore()
    store.publish(VisualState("planning", "Planning the structure.", 0.08, "working"))
    store.publish(VisualState("building", "Building the main structure.", 0.48, "working"))
    events = store.events_after(0)
    assert [state.phase for _, state in events] == ["planning", "building"]


def test_turn_boundary_drops_previous_history_without_resetting_revision():
    store = StateStore()
    store.publish(VisualState("finished", "Finished building.", 1.0, "finished"))
    previous_revision = store.snapshot()[0]
    store.begin_turn()
    store.publish(VisualState("planning", "I got your prompt. Mapping the build.", 0.02, "working"))
    assert store.initial_revision(None) == previous_revision
    assert [state.phase for _, state in store.events_after(previous_revision)] == ["planning"]


def test_event_batch_is_bounded_by_captured_revision():
    store = StateStore()
    store.publish(VisualState("planning", "Planning.", 0.08, "working"))
    captured = store.snapshot()[0]
    store.publish(VisualState("building", "Building.", 0.48, "working"))
    assert [state.phase for _, state in store.events_between(0, captured)] == ["planning"]


def test_last_event_id_controls_resume_cursor():
    store = StateStore()
    store.publish(VisualState("planning", "Planning.", 0.08, "working"))
    assert store.initial_revision("1") == 1


def test_future_last_event_id_is_clamped_after_server_restart():
    store = StateStore()
    assert store.initial_revision("100") == 0
    store.publish(VisualState("planning", "Planning.", 0.08, "working"))
    assert store.initial_revision("100") == 0
