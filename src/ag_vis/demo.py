from __future__ import annotations

import threading
import time

from .classifier import classify_event
from .server import StateStore


DEMO_EVENTS = [
    {"type": "turn_started"},
    {"type": "function_call", "name": "view_image"},
    {"type": "function_call", "name": "apply_patch"},
    {"type": "function_call", "name": "exec_command"},
    {"type": "tool_error"},
    {"type": "function_call", "name": "exec_command"},
    {"type": "turn_completed"},
]


def replay(store: StateStore, delay: float = 1.8, repeat: bool = True) -> None:
    while True:
        _, state = store.snapshot()
        for event in DEMO_EVENTS:
            state = classify_event(event, state)
            store.publish(state)
            time.sleep(delay)
        if not repeat:
            return
        time.sleep(delay * 2)
        from .model import VisualState

        store.publish(VisualState.initial())
        time.sleep(delay)


def start_demo(store: StateStore, delay: float = 1.8) -> threading.Thread:
    thread = threading.Thread(target=replay, args=(store, delay), daemon=True)
    thread.start()
    return thread
