# Ag-Vis

Watch your AI agent build its work.

Ag-Vis is a local visualization companion for Codex. It converts observable session events into a small animated construction story: a robot plans, carries materials, raises floors, checks the structure, repairs problems, and finishes a large building. Short dialogue explains the current activity without exposing private reasoning or raw logs.

## Try the demo

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run ag-vis --demo
```

The browser opens automatically at `http://127.0.0.1:8765`.

## Watch Codex

Run Ag-Vis from the project directory you are using with Codex:

```bash
uv run ag-vis
```

Useful options:

```bash
uv run ag-vis --no-open
uv run ag-vis --workspace /path/to/project
uv run ag-vis --session-root /path/to/codex/sessions
uv run ag-vis --port 9000
```

## Privacy

Ag-Vis binds to `127.0.0.1` by default. The watcher reduces Codex records to allowlisted event types and known tool names before classification. Browser responses never contain prompt text, file contents, raw command arguments, environment variables, or private reasoning.

Laya 0.3.4 is included as an optional local decision layer for future ambiguous-event classification. The current deterministic rules remain the default and work without downloading model weights.

## Current limits

- Codex sessions only in V1
- Activity-based progress, not an exact completion estimate
- One construction visual theme
- Browser popup rather than a native window

## Development

```bash
uv run pytest -q
uv run python -m compileall -q src tests
```

Apache-2.0
