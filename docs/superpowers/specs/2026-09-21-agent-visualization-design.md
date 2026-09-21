# Agent Visualization V1 Design

Project and GitHub repository name: **Ag-Vis**.

## Goal

Create a local companion that opens a browser popup while a Codex agent works. A small animated robot constructs a large multi-story building as the agent progresses. Short dialogue bubbles explain the current activity in plain language without exposing private reasoning or dumping raw logs.

## V1 Scope

- Support local Codex sessions first.
- Read Codex session files without modifying Codex.
- Start a local HTTP server and open one visualization popup.
- Translate observable session events into a small shared event model.
- Show planning, reading, building, testing, repairing, waiting, blocked, and finished states.
- Use deterministic rules first and an optional Laya classifier when a local model is available.
- Keep all processing local and avoid displaying prompt contents, secrets, raw command arguments, or chain-of-thought.

Claude Code hooks, tool proxies, multiple visual themes, audio, and enforcement are outside V1.

## User Experience

The user starts the visualizer from the repository and then uses Codex normally. A rounded browser popup opens and shows a construction site. The same robot appears in different positions to represent activity over time. The building gains structural sections as progress events arrive.

A dialogue bubble contains one short sentence, such as:

- “Inspecting the project.”
- “Building the main structure.”
- “Checking whether it works.”
- “A check failed. Repairing it.”
- “Running final checks.”
- “Finished.”

The popup shows only observable activity. It may describe an upcoming action only when the agent explicitly announced it.

## Architecture

### Session watcher

The watcher discovers Codex JSONL session files, follows appended records, ignores unrelated working directories, and emits sanitized source events. It tolerates partial JSONL writes, file rotation, and restarts.

### Event translator

The translator maps noisy source events into a stable schema:

```json
{
  "phase": "building",
  "message": "Building the main structure.",
  "progress": 0.45,
  "status": "working",
  "timestamp": "2026-09-21T12:00:00Z"
}
```

Rules recognize common tool and lifecycle events. Laya is an optional decision layer for ambiguous activity classification; failure to load Laya or its model falls back to rules and never stops the visualization.

### Local server

A small Python server owns current state, serves static assets, and streams updates to the browser with Server-Sent Events. A health endpoint and a current-state endpoint make the system easy to test.

### Renderer

The browser uses layered HTML, CSS, and lightweight SVG shapes. The scene contains a reusable popup shell, construction site, large building, crane, robot poses, dialogue bubble, and status marker. CSS animations handle motion so V1 needs no game engine.

## Progress Model

Progress is activity-based rather than a claim of exact completion:

- Prompt received: 5%
- Planning and inspection: 10–25%
- Reading and research: 20–40%
- Building and editing: 30–75%
- Testing and repair: 65–90%
- Final verification: 90–98%
- Completed: 100%

Progress never moves backward. A repair event changes the animation and dialogue without lowering the displayed value.

## Privacy and Safety

- Bind the server to `127.0.0.1` by default.
- Never send session data to a hosted service.
- Do not expose raw prompts, model reasoning, file contents, environment values, or complete command arguments.
- Reduce events to an allowlisted phase, status, generic message, progress value, and timestamp.
- Escape all browser-rendered strings.

## Failure Handling

- Missing Codex directory: show a waiting state with setup guidance.
- Malformed or partial JSONL: skip until the record is complete.
- Browser disconnected: retain the latest state and reconnect automatically.
- Laya unavailable: continue with deterministic rules.
- Unknown event: retain current progress and show a neutral working message.

## Testing

- Unit tests for sanitization, event classification, progress monotonicity, and partial JSONL handling.
- Server tests for health, state, and event streaming.
- Browser smoke test for initial render and state changes.
- Fixture-based replay of a small synthetic Codex session; no real private session content in the repository.

## Success Criteria

Running one command opens a local popup. Replaying the included fixture visibly moves through planning, building, testing, repairing, and completion. Dialogue stays short and generic, progress reaches 100%, no private event payload appears in browser responses, and all automated tests pass.
