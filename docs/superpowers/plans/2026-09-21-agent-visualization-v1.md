# Ag-Vis V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Codex companion that turns sanitized session activity into short dialogue and an animated robot constructing a large building in a browser popup.

**Architecture:** A Python watcher tails Codex JSONL sessions and feeds a deterministic event classifier with an optional Laya fallback. A localhost HTTP server stores the latest public state and streams it over Server-Sent Events to a dependency-free HTML/CSS/JavaScript renderer.

**Tech Stack:** Python 3.12, Laya 0.3.4, Python standard library HTTP/SSE, HTML, CSS, JavaScript, pytest.

## Global Constraints

- Support local Codex sessions first.
- Bind only to `127.0.0.1` by default.
- Never expose prompts, private reasoning, file contents, environment values, or raw command arguments.
- Laya is optional at runtime; deterministic rules must remain fully functional.
- Browser dialogue must be one short generic sentence.
- Progress must be monotonic and end at 100% only on completion.
- The V1 scene must use simple layered shapes and show a large multi-story building.

---

### Task 1: Public event model and deterministic classification

**Files:**
- Create: `src/ag_vis/__init__.py`
- Create: `src/ag_vis/model.py`
- Create: `src/ag_vis/classifier.py`
- Create: `tests/test_classifier.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: sanitized event dictionaries from the watcher.
- Produces: `VisualState`, `classify_event(event, previous)`, and `public_dict(state)`.

- [ ] **Step 1: Add pytest and write failing classification tests**

```python
def test_tool_call_becomes_building_state():
    state = classify_event({"type": "function_call", "name": "apply_patch"}, VisualState.initial())
    assert state.phase == "building"
    assert state.message == "Building the main structure."

def test_progress_never_moves_backwards():
    previous = VisualState(phase="testing", message="Checking whether it works.", progress=0.8, status="working")
    state = classify_event({"type": "agent_message"}, previous)
    assert state.progress == 0.8

def test_public_state_has_allowlisted_fields_only():
    assert set(public_dict(VisualState.initial())) == {"phase", "message", "progress", "status", "timestamp"}
```

- [ ] **Step 2: Run the tests and confirm the missing package failure**

Run: `uv run pytest tests/test_classifier.py -q`
Expected: collection fails because `ag_vis` does not exist.

- [ ] **Step 3: Implement immutable state and rules**

```python
@dataclass(frozen=True)
class VisualState:
    phase: str
    message: str
    progress: float
    status: str
    timestamp: str = field(default_factory=utc_now)

    @classmethod
    def initial(cls) -> "VisualState":
        return cls("waiting", "Waiting for the agent to begin.", 0.0, "waiting")

def classify_event(event: Mapping[str, Any], previous: VisualState) -> VisualState:
    phase, message, target, status = classify_with_rules(event)
    return VisualState(phase, message, max(previous.progress, target), status)
```

- [ ] **Step 4: Run the focused tests**

Run: `uv run pytest tests/test_classifier.py -q`
Expected: all classification tests pass.

- [ ] **Step 5: Commit the event model**

```bash
git add pyproject.toml uv.lock src/ag_vis tests/test_classifier.py
git commit -m "feat: classify agent activity into visual states"
```

### Task 2: Privacy-preserving Codex JSONL watcher

**Files:**
- Create: `src/ag_vis/watcher.py`
- Create: `tests/fixtures/codex-session.jsonl`
- Create: `tests/test_watcher.py`

**Interfaces:**
- Consumes: a session root `Path`, workspace `Path`, and appended JSONL bytes.
- Produces: `discover_sessions(root, workspace)`, `sanitize_record(record)`, and `follow_jsonl(path, stop_event)`.

- [ ] **Step 1: Write failing watcher tests**

```python
def test_sanitize_record_drops_payload_content():
    result = sanitize_record({"type": "response_item", "payload": {"type": "function_call", "name": "apply_patch", "arguments": "SECRET"}})
    assert result == {"type": "function_call", "name": "apply_patch"}
    assert "SECRET" not in repr(result)

def test_partial_jsonl_waits_for_newline(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text('{"type":"turn_started"}')
    assert list(read_complete_records(path)) == []
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `uv run pytest tests/test_watcher.py -q`
Expected: import fails because `ag_vis.watcher` does not exist.

- [ ] **Step 3: Implement discovery, complete-line reading, and allowlist sanitization**

```python
ALLOWED_NAMES = {"apply_patch", "exec_command", "write_stdin", "view_image"}

def sanitize_record(record: Mapping[str, Any]) -> dict[str, str] | None:
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else record
    event_type = str(payload.get("type", record.get("type", "unknown")))
    result = {"type": event_type}
    name = payload.get("name")
    if isinstance(name, str) and name in ALLOWED_NAMES:
        result["name"] = name
    return result
```

- [ ] **Step 4: Run watcher and privacy tests**

Run: `uv run pytest tests/test_watcher.py -q`
Expected: all watcher tests pass and fixture secrets never appear in sanitized output.

- [ ] **Step 5: Commit the watcher**

```bash
git add src/ag_vis/watcher.py tests/fixtures/codex-session.jsonl tests/test_watcher.py
git commit -m "feat: watch Codex sessions without exposing content"
```

### Task 3: Local state server and SSE stream

**Files:**
- Create: `src/ag_vis/server.py`
- Create: `tests/test_server.py`

**Interfaces:**
- Consumes: `StateStore.publish(VisualState)` calls from the runtime.
- Produces: `GET /health`, `GET /api/state`, `GET /api/events`, and static asset responses.

- [ ] **Step 1: Write failing server tests**

```python
def test_health_endpoint(running_server):
    response = urlopen(running_server + "/health")
    assert response.read() == b'{"ok":true}'

def test_state_endpoint_contains_only_public_state(running_server):
    payload = json.load(urlopen(running_server + "/api/state"))
    assert set(payload) == {"phase", "message", "progress", "status", "timestamp"}
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `uv run pytest tests/test_server.py -q`
Expected: import fails because `ag_vis.server` does not exist.

- [ ] **Step 3: Implement a threaded localhost server and state store**

```python
class StateStore:
    def __init__(self) -> None:
        self._state = VisualState.initial()
        self._condition = threading.Condition()
        self._revision = 0

    def publish(self, state: VisualState) -> None:
        with self._condition:
            self._state = state
            self._revision += 1
            self._condition.notify_all()
```

- [ ] **Step 4: Verify endpoints and SSE formatting**

Run: `uv run pytest tests/test_server.py -q`
Expected: server tests pass.

- [ ] **Step 5: Commit the server**

```bash
git add src/ag_vis/server.py tests/test_server.py
git commit -m "feat: stream visual state from a local server"
```

### Task 4: Animated construction popup

**Files:**
- Create: `src/ag_vis/static/index.html`
- Create: `src/ag_vis/static/styles.css`
- Create: `src/ag_vis/static/app.js`
- Create: `tests/test_static.py`

**Interfaces:**
- Consumes: `/api/state` and `/api/events` public JSON.
- Produces: a responsive popup scene with `data-phase`, dialogue, progress, robot poses, building floors, scaffold, and crane.

- [ ] **Step 1: Write failing static-contract tests**

```python
def test_scene_contains_accessible_status_and_building_layers():
    html = static_text("index.html")
    assert 'id="dialogue"' in html
    assert 'aria-live="polite"' in html
    assert 'id="building"' in html
    assert 'id="progress"' in html

def test_javascript_uses_sse_and_text_content():
    script = static_text("app.js")
    assert "new EventSource('/api/events')" in script
    assert ".textContent = state.message" in script
    assert "innerHTML" not in script
```

- [ ] **Step 2: Run tests and confirm missing files**

Run: `uv run pytest tests/test_static.py -q`
Expected: tests fail because the static scene does not exist.

- [ ] **Step 3: Build the dependency-free scene and phase animations**

```javascript
function render(state) {
  scene.dataset.phase = state.phase;
  dialogue.textContent = state.message;
  progress.value = Math.round(state.progress * 100);
  building.style.setProperty('--progress', state.progress);
}

fetch('/api/state').then((response) => response.json()).then(render);
const events = new EventSource('/api/events');
events.onmessage = (event) => render(JSON.parse(event.data));
```

- [ ] **Step 4: Run static and full tests**

Run: `uv run pytest -q`
Expected: every test passes.

- [ ] **Step 5: Commit the renderer**

```bash
git add src/ag_vis/static tests/test_static.py
git commit -m "feat: animate the Ag-Vis construction popup"
```

### Task 5: CLI, demo replay, Laya adapter, and documentation

**Files:**
- Create: `src/ag_vis/laya_adapter.py`
- Create: `src/ag_vis/cli.py`
- Create: `src/ag_vis/demo.py`
- Create: `tests/test_cli.py`
- Create: `README.md`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: CLI options `--demo`, `--no-open`, `--session-root`, `--workspace`, `--host`, and `--port`.
- Produces: `ag-vis` console command, optional Laya ambiguity classifier, and deterministic demo replay.

- [ ] **Step 1: Write failing CLI and fallback tests**

```python
def test_parser_defaults_to_localhost():
    args = build_parser().parse_args([])
    assert args.host == "127.0.0.1"

def test_laya_failure_returns_none(monkeypatch):
    monkeypatch.setattr("ag_vis.laya_adapter._load_router", lambda: (_ for _ in ()).throw(RuntimeError()))
    assert classify_with_laya({"type": "unknown"}) is None
```

- [ ] **Step 2: Run tests and confirm missing modules**

Run: `uv run pytest tests/test_cli.py -q`
Expected: imports fail because CLI modules do not exist.

- [ ] **Step 3: Implement CLI orchestration and demo sequence**

```python
DEMO_EVENTS = [
    {"type": "turn_started"},
    {"type": "function_call", "name": "view_image"},
    {"type": "function_call", "name": "apply_patch"},
    {"type": "function_call", "name": "exec_command"},
    {"type": "tool_error"},
    {"type": "turn_completed"},
]

def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)
```

- [ ] **Step 4: Verify tests and a live demo response**

Run: `uv run pytest -q`
Expected: all tests pass.

Run: `uv run ag-vis --demo --no-open --port 8765`
Expected: server starts on `http://127.0.0.1:8765` and replays the construction phases.

- [ ] **Step 5: Document installation, privacy, commands, and limitations**

```markdown
uv sync
uv run ag-vis --demo
uv run ag-vis
```

- [ ] **Step 6: Commit the runnable V1**

```bash
git add pyproject.toml uv.lock src/ag_vis README.md tests/test_cli.py
git commit -m "feat: ship the runnable Ag-Vis v1"
```

### Task 6: Final verification and GitHub publication

**Files:**
- Modify only files required by verification failures.

**Interfaces:**
- Consumes: completed repository.
- Produces: verified public GitHub repository `Ag-Vis` with `main` pushed.

- [ ] **Step 1: Run the complete verification suite**

Run: `uv run pytest -q`
Expected: all tests pass with no failures.

Run: `uv run python -m compileall -q src tests`
Expected: exit code 0.

- [ ] **Step 2: Check repository cleanliness and secret exposure**

Run: `git status --short && git grep -nE '(sk-[A-Za-z0-9]{20,}|NVIDIA_API_KEY=.+|OPENAI_API_KEY=.+)' -- . ':!uv.lock'`
Expected: no uncommitted files and no secret matches.

- [ ] **Step 3: Create and push the public repository**

```bash
gh repo create Ag-Vis --public --source=. --remote=origin --push
```

- [ ] **Step 4: Confirm the remote and default branch**

Run: `gh repo view --json name,url,visibility,defaultBranchRef`
Expected: name `Ag-Vis`, visibility `PUBLIC`, default branch `main`.
