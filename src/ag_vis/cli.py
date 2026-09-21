from __future__ import annotations

import argparse
import threading
import webbrowser
from pathlib import Path
from typing import Sequence

from .classifier import classify_event
from .demo import start_demo
from .laya_adapter import classify_with_laya
from .model import VisualState
from .server import StateStore, create_server
from .watcher import TailCursor, discover_sessions, read_tail_events


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Watch an AI agent build its work.")
    parser.add_argument("--demo", action="store_true", help="replay a built-in visual story")
    parser.add_argument("--no-open", action="store_true", help="do not open a browser window")
    parser.add_argument("--laya", action="store_true", help="use the optional local Laya classifier")
    parser.add_argument("--session-root", type=Path, default=Path.home() / ".codex" / "sessions")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser


def _poll_once(
    store: StateStore,
    root: Path,
    workspace: Path,
    cursors: dict[Path, TailCursor],
    active: Path | None,
    fallback,
) -> Path | None:
    sessions = discover_sessions(root, workspace)
    latest = sessions[-1] if sessions else None
    if latest is None:
        store.publish(VisualState("waiting", "No Codex session found. Start Codex in this project.", 0.0, "waiting"))
        return None
    if latest != active:
        store.publish(VisualState.initial())
    events, cursors[latest] = read_tail_events(latest, cursors.get(latest, TailCursor()))
    for event in events:
        _, previous = store.snapshot()
        store.publish(classify_event(event, previous, fallback))
    return latest


def _watch(store: StateStore, root: Path, workspace: Path, use_laya: bool = False) -> None:
    stop = threading.Event()
    cursors: dict[Path, TailCursor] = {}
    active: Path | None = None
    fallback = classify_with_laya if use_laya else None
    while not stop.is_set():
        active = _poll_once(store, root, workspace, cursors, active, fallback)
        stop.wait(0.2 if active else 0.75)


def run(args: argparse.Namespace) -> int:
    store = StateStore()
    server = create_server(args.host, args.port, store)
    url = f"http://{args.host}:{server.server_port}"
    if args.demo:
        start_demo(store)
    else:
        threading.Thread(
            target=_watch,
            args=(store, args.session_root, args.workspace.resolve(), args.laya),
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
