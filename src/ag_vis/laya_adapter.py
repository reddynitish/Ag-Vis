from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def _load_router():
    from laya import Router

    return Router(max_loaded=1)


def classify_with_laya(event: dict[str, str]) -> str | None:
    """Classify an already-sanitized event, returning no private content to Laya."""
    try:
        router = _load_router()
        result = router.predict(
            {"event_type": event.get("type", "unknown"), "tool": event.get("name", "")},
            {
                "activity": {
                    "type": "choice",
                    "instructions": "Which visible activity best represents this agent event?",
                    "criteria": {
                        "planning": "starting or deciding",
                        "researching": "reading or inspecting",
                        "building": "writing or editing",
                        "testing": "running or checking",
                        "repairing": "recovering from an error",
                    },
                }
            },
            model="typed-decisions",
        )
        answer: Any = result["answers"]["activity"].get("choice")
        return answer if isinstance(answer, str) else None
    except Exception:
        return None
