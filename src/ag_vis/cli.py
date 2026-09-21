from __future__ import annotations

import argparse
import threading
import webbrowser
from pathlib import Path
from typing import Sequence

from .classifier import classify_event
from .demo import start_demo
from .server import StateStore, create_server
from .watcher import discover_sessions, follow_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Watch an AI agent build its work.")
    parser.add_argument("--demo", action="store_true", help="replay a built-in visual story")
    parser.add_argument("--no-open", action="store_true", help="do not open a browser window")
    parser.add_argument("--session-root", type=Path, default=Path.home() / ".codex" / "sessions")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser


def _watch(store: StateStore, root: Path, workspace: Path) -> None:
    stop = threading.Event()
    seen: Path | None = None
    while not stop.is_set():
        sessions = discover_sessions(root, workspace)
        latest = sessions[-1] if sessions else None
        if latest is None or latest == seen:
            stop.wait(0.75)
            continue
        seen = latest
        for event in follow_jsonl(latest, stop):
            _, previous = store.snapshot()
            store.publish(classify_event(event, previous))


def run(args: argparse.Namespace) -> int:
    store = StateStore()
    server = create_server(args.host, args.port, store)
    url = f"http://{args.host}:{server.server_port}"
    if args.demo:
        start_demo(store)
    else:
        threading.Thread(
            target=_watch,
            args=(store, args.session_root, args.workspace.resolve()),
            daemon=True,
        ).start()
    if not args.no_open:
        webbrowser.open(url)
    print(f"Ag-Vis running at {url} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))
