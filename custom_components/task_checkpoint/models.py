
"""Runtime models for Task Checkpoint."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class TaskRuntimeState:
    """Represents the live state of a task."""

    task_id: str
    title: str
    status: str
    due_iso: str
    warning_sent_minutes: list[int] = field(default_factory=list)
    last_warning_iso: str | None = None
    last_due_alert_iso: str | None = None
    last_nag_iso: str | None = None
    last_parent_prompt_iso: str | None = None
    last_acknowledged_iso: str | None = None
    last_verified_iso: str | None = None
    last_completed_iso: str | None = None
    acknowledged_by: str | None = None
    acknowledgment_method: str | None = None
    verified_by: str | None = None
    escalation_level: int = 0

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable form of the state."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskRuntimeState":
        """Restore state from storage."""
        return cls(**data)

    @property
    def due_at(self) -> datetime:
        """Return due time as a datetime."""
        return datetime.fromisoformat(self.due_iso)
