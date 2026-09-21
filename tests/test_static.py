from pathlib import Path


STATIC = Path(__file__).parents[1] / "src" / "ag_vis" / "static"


def static_text(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def test_scene_contains_accessible_status_and_building_layers():
    html = static_text("index.html")
    assert 'id="dialogue"' in html
    assert 'aria-live="polite"' in html
    assert 'id="building"' in html
    assert 'id="progress"' in html
    assert html.count('class="floor') >= 6


def test_javascript_uses_sse_and_text_content():
    script = static_text("app.js")
    assert "new EventSource('/api/events')" in script
    assert ".textContent = state.message" in script
    assert "innerHTML" not in script
    assert "const actionQueue" in script
    assert "await playAction" in script


def test_each_visible_action_has_a_minimum_screen_time():
    script = static_text("app.js")
    assert "MIN_ACTION_MS" in script
    assert "setTimeout" in script


def test_styles_include_all_activity_phases():
    styles = static_text("styles.css")
    for phase in ("planning", "researching", "building", "testing", "repairing", "blocked", "finished"):
        assert f'[data-phase="{phase}"]' in styles


def test_scene_uses_reduced_motion_preference():
    assert "prefers-reduced-motion" in static_text("styles.css")
