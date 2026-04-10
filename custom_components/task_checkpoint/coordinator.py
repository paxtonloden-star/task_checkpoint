"""Coordinator for Task Checkpoint."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HOUSEHOLD_NAME,
    CONF_PARENT_NAME,
    CONF_TEEN_NAME,
    COORDINATOR_UPDATE_INTERVAL_SECONDS,
    DEFAULT_TASKS,
    DOMAIN,
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

    def __init__(self, hass: HomeAssistant, entry_id: str, config: dict) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=COORDINATOR_UPDATE_INTERVAL_SECONDS),
        )
        self.entry_id = entry_id
        self.household_name: str = config[CONF_HOUSEHOLD_NAME]
        self.teen_name: str = config[CONF_TEEN_NAME]
        self.parent_name: str = config[CONF_PARENT_NAME]
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
        else:
            self.data = self._build_default_runtime_states()
            await self._async_save()

        await self.async_refresh()

    def _build_default_runtime_states(self) -> dict[str, TaskRuntimeState]:
        now = dt_util.now()
        runtime_states: dict[str, TaskRuntimeState] = {}
        for definition in DEFAULT_TASKS:
            due_at = _next_due_for_definition(definition, now)
            runtime_states[definition.task_id] = TaskRuntimeState(
                task_id=definition.task_id,
                title=definition.title,
                status=STATE_SCHEDULED,
                due_iso=due_at.isoformat(),
            )
        return runtime_states

    async def _async_update_data(self) -> dict[str, TaskRuntimeState]:
        """Advance derived states based on current time."""
        now = dt_util.now()

        for definition in DEFAULT_TASKS:
            task = self.data[definition.task_id]
            due_at = task.due_at

            if task.status == STATE_COMPLETED and now > due_at + timedelta(minutes=1):
                next_due = _next_due_for_definition(definition, now)
                task.status = STATE_SCHEDULED
                task.due_iso = next_due.isoformat()
                task.last_acknowledged_iso = None
                task.last_verified_iso = None
                task.last_completed_iso = None
                task.acknowledged_by = None
                task.acknowledgment_method = None
                task.verified_by = None
                task.escalation_level = 0
                continue

            if task.status == STATE_SCHEDULED and now >= due_at:
                task.status = STATE_AWAITING_ACK
                task.escalation_level = 1
                continue

            if task.status == STATE_AWAITING_ACK:
                overdue_by = now - due_at
                if overdue_by >= timedelta(minutes=definition.ack_timeout_minutes):
                    task.status = STATE_MISSED
                    task.escalation_level = 3

        await self._async_save()
        return self.data

    async def async_acknowledge_task(
        self,
        task_id: str,
        actor: str | None = None,
        method: str | None = None,
    ) -> None:
        """Mark a task as acknowledged."""
        task = self.data[task_id]
        now = dt_util.now().isoformat()
        task.status = STATE_AWAITING_PARENT_VERIFY
        task.last_acknowledged_iso = now
        task.acknowledged_by = actor or self.teen_name
        task.acknowledgment_method = method or "manual"
        task.escalation_level = 0
        await self._async_save()
        await self.async_refresh()

    async def async_parent_verify_task(
        self,
        task_id: str,
        actor: str | None = None,
    ) -> None:
        """Mark a task as parent verified and completed."""
        task = self.data[task_id]
        now = dt_util.now().isoformat()
        task.status = STATE_COMPLETED
        task.last_verified_iso = now
        task.last_completed_iso = now
        task.verified_by = actor or self.parent_name
        task.escalation_level = 0
        await self._async_save()
        await self.async_refresh()

    async def async_reset_task(self, task_id: str) -> None:
        """Reset a task to its next scheduled run."""
        definition = next(item for item in DEFAULT_TASKS if item.task_id == task_id)
        next_due = _next_due_for_definition(definition, dt_util.now())
        self.data[task_id] = TaskRuntimeState(
            task_id=definition.task_id,
            title=definition.title,
            status=STATE_SCHEDULED,
            due_iso=next_due.isoformat(),
        )
        await self._async_save()
        await self.async_refresh()

    async def _async_save(self) -> None:
        await self._store.async_save(
            {"tasks": {task_id: state.as_dict() for task_id, state in self.data.items()}}
        )


def _next_due_for_definition(definition, now: datetime) -> datetime:
    """Return the next due datetime for a task definition."""
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

    fallback = today_target + timedelta(days=1)
    return fallback
