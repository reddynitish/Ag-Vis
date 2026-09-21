from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class VisualState:
    phase: str
    message: str
    progress: float
    status: str
    timestamp: str = field(default_factory=utc_now)

    @classmethod
    def initial(cls) -> "VisualState":
        return cls("waiting", "Waiting for the agent to begin.", 0.0, "waiting")


def public_dict(state: VisualState) -> dict[str, Any]:
    return asdict(state)
