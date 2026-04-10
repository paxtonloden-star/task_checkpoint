
"""Coordinator for Task Checkpoint."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HOUSEHOLD_NAME,
    CONF_PARENT_NAME,
    CONF_PARENT_NOTIFY_SERVICE,
    CONF_TEEN_NAME,
    CONF_TEEN_NOTIFY_SERVICE,
    DEFAULT_TASKS,
    DEFAULT_TASKS_BY_ID,
    DOMAIN,
    EVENT_ACKNOWLEDGED,
    EVENT_PARENT_VERIFIED,
    EVENT_RESET,
    STATE_AWAITING_ACK,
    STATE_AWAITING_PARENT_VERIFY,
    STATE_COMPLETED,
    STATE_MISSED,
    STATE_SCHEDULED,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .models import TaskRuntimeState

_LOGGER = logging.getLogger(__name__)


class TaskCheckpointCoordinator(DataUpdateCoordinator[dict[str, TaskRuntimeState]]):
    """Coordinate runtime state for Task Checkpoint."""

    config_entry_title = "Task Checkpoint"

    def __init__(self, hass: HomeAssistant, entry_id: str, config: dict[str, Any]) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.entry_id = entry_id
        self.household_name: str = config[CONF_HOUSEHOLD_NAME]
        self.teen_name: str = config[CONF_TEEN_NAME]
        self.parent_name: str = config[CONF_PARENT_NAME]
        self.teen_notify_service: str | None = config.get(CONF_TEEN_NOTIFY_SERVICE) or None
        self.parent_notify_service: str | None = config.get(CONF_PARENT_NOTIFY_SERVICE) or None
        self._store: Store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}")
        self.data: dict[str, TaskRuntimeState] = {}

    async def async_initialize(self) -> None:
        """Load persisted state or create defaults."""
        stored = await self._store.async_load()
        if stored and "tasks" in stored:
            self.data = {
                task_id: TaskRuntimeState.from_dict(payload)
                for task_id, payload in stored["tasks"].items()
            }
            self._migrate_loaded_tasks()
        else:
            self.data = self._build_default_runtime_states()

        await self._async_commit()

    async def _async_update_data(self) -> dict[str, TaskRuntimeState]:
        """Return the latest in-memory data."""
        return self.data

    def _migrate_loaded_tasks(self) -> None:
        """Backfill new fields after storage schema changes."""
        for definition in DEFAULT_TASKS:
            runtime = self.data.get(definition.task_id)
            if runtime is None:
                due_at = self.get_next_due(definition.task_id, dt_util.now())
                self.data[definition.task_id] = TaskRuntimeState(
                    task_id=definition.task_id,
                    title=definition.title,
                    status=STATE_SCHEDULED,
                    due_iso=due_at.isoformat(),
                )

    def _build_default_runtime_states(self) -> dict[str, TaskRuntimeState]:
        now = dt_util.now()
        runtime_states: dict[str, TaskRuntimeState] = {}
        for definition in DEFAULT_TASKS:
            due_at = self.get_next_due(definition.task_id, now)
            runtime_states[definition.task_id] = TaskRuntimeState(
                task_id=definition.task_id,
                title=definition.title,
                status=STATE_SCHEDULED,
                due_iso=due_at.isoformat(),
            )
        return runtime_states

    def get_next_due(self, task_id: str, now: datetime) -> datetime:
        """Return the next due datetime for a task."""
        definition = DEFAULT_TASKS_BY_ID[task_id]
        today_target = now.replace(
            hour=definition.due_time.hour,
            minute=definition.due_time.minute,
            second=0,
            microsecond=0,
        )

        for offset in range(0, 14):
            candidate = today_target + timedelta(days=offset)
            if candidate.weekday() not in definition.days_of_week:
                continue
            if offset == 0 and candidate <= now:
                continue
            return candidate

        return today_target + timedelta(days=1)

    async def async_record_warning(self, task_id: str, warning_minutes: int) -> None:
        """Record that a warning has been sent."""
        runtime = self.data[task_id]
        if warning_minutes not in runtime.warning_sent_minutes:
            runtime.warning_sent_minutes.append(warning_minutes)
        runtime.last_warning_iso = dt_util.now().isoformat()
        await self._async_commit()

    async def async_mark_due(self, task_id: str) -> None:
        """Move a task into awaiting acknowledgement."""
        runtime = self.data[task_id]
        if runtime.status != STATE_SCHEDULED:
            return
        runtime.status = STATE_AWAITING_ACK
        runtime.escalation_level = 1
        await self._async_commit()

    async def async_record_due_alert(self, task_id: str) -> None:
        """Record that the due alert was sent."""
        runtime = self.data[task_id]
        runtime.last_due_alert_iso = dt_util.now().isoformat()
        await self._async_commit()

    async def async_set_escalation_level(self, task_id: str, level: int) -> None:
        """Set the escalation level for a task."""
        runtime = self.data[task_id]
        runtime.escalation_level = level
        await self._async_commit()

    async def async_record_nag(self, task_id: str) -> None:
        """Record a repeated nag notification."""
        runtime = self.data[task_id]
        runtime.last_nag_iso = dt_util.now().isoformat()
        await self._async_commit()

    async def async_record_parent_prompt(self, task_id: str) -> None:
        """Record a parent verification prompt."""
        runtime = self.data[task_id]
        runtime.last_parent_prompt_iso = dt_util.now().isoformat()
        await self._async_commit()

    async def async_acknowledge_task(
        self,
        task_id: str,
        actor: str | None = None,
        method: str | None = None,
    ) -> None:
        """Mark a task as acknowledged."""
        runtime = self.data[task_id]
        now = dt_util.now().isoformat()
        runtime.status = STATE_AWAITING_PARENT_VERIFY
        runtime.last_acknowledged_iso = now
        runtime.acknowledged_by = actor or self.teen_name
        runtime.acknowledgment_method = method or "manual"
        runtime.escalation_level = 0
        runtime.last_nag_iso = None
        await self._async_commit()
        await self.async_fire_event(EVENT_ACKNOWLEDGED, task_id=task_id)

    async def async_parent_verify_task(
        self,
        task_id: str,
        actor: str | None = None,
    ) -> None:
        """Mark a task as parent verified and completed."""
        runtime = self.data[task_id]
        now = dt_util.now()
        runtime.status = STATE_COMPLETED
        runtime.last_verified_iso = now.isoformat()
        runtime.last_completed_iso = now.isoformat()
        runtime.verified_by = actor or self.parent_name
        runtime.escalation_level = 0
        runtime.last_parent_prompt_iso = None
        runtime.due_iso = self.get_next_due(task_id, now).isoformat()
        runtime.warning_sent_minutes = []
        runtime.last_warning_iso = None
        runtime.last_due_alert_iso = None
        runtime.last_nag_iso = None
        await self._async_commit()
        await self.async_fire_event(EVENT_PARENT_VERIFIED, task_id=task_id)

    async def async_mark_missed(self, task_id: str) -> None:
        """Mark a task as missed."""
        runtime = self.data[task_id]
        runtime.status = STATE_MISSED
        runtime.escalation_level = max(runtime.escalation_level, 4)
        await self._async_commit()

    async def async_prepare_next_run(self, task_id: str, next_due: datetime) -> None:
        """Prepare the next scheduled run."""
        runtime = self.data[task_id]
        runtime.status = STATE_SCHEDULED
        runtime.due_iso = next_due.isoformat()
        runtime.warning_sent_minutes = []
        runtime.last_warning_iso = None
        runtime.last_due_alert_iso = None
        runtime.last_nag_iso = None
        runtime.last_parent_prompt_iso = None
        runtime.last_acknowledged_iso = None
        runtime.last_verified_iso = None
        runtime.last_completed_iso = None
        runtime.acknowledged_by = None
        runtime.acknowledgment_method = None
        runtime.verified_by = None
        runtime.escalation_level = 0
        await self._async_commit()

    async def async_reset_task(self, task_id: str) -> None:
        """Reset a task to its next scheduled run."""
        next_due = self.get_next_due(task_id, dt_util.now())
        await self.async_prepare_next_run(task_id, next_due)
        await self.async_fire_event(EVENT_RESET, task_id=task_id)

    async def async_fire_event(
        self,
        event_type: str,
        *,
        task_id: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Fire a task checkpoint event."""
        runtime = self.data[task_id]
        payload = {
            "entry_id": self.entry_id,
            "household_name": self.household_name,
            "teen_name": self.teen_name,
            "parent_name": self.parent_name,
            "task_id": task_id,
            "task_title": runtime.title,
            "status": runtime.status,
            "due_at": runtime.due_iso,
            "type": event_type,
            "escalation_level": runtime.escalation_level,
        }
        if extra:
            payload.update(extra)
        self.hass.bus.async_fire(f"{DOMAIN}_event", payload)

    async def _async_commit(self) -> None:
        """Persist and publish state updates."""
        await self._store.async_save(
            {"tasks": {task_id: state.as_dict() for task_id, state in self.data.items()}}
        )
        self.async_set_updated_data(dict(self.data))
