
"""Scheduling and escalation engine for Task Checkpoint."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_NAG_INTERVAL_MINUTES,
    DEFAULT_PARENT_REMINDER_INTERVAL_MINUTES,
    DEFAULT_TASKS,
    DEFAULT_TASKS_BY_ID,
    EVENT_DUE,
    EVENT_ESCALATED,
    EVENT_MISSED,
    EVENT_PARENT_VERIFICATION_REQUESTED,
    EVENT_WARNING_SENT,
    HARD_MISS_AFTER_MINUTES,
    STATE_AWAITING_ACK,
    STATE_AWAITING_PARENT_VERIFY,
    STATE_COMPLETED,
    STATE_MISSED,
    STATE_SCHEDULED,
)
from .coordinator import TaskCheckpointCoordinator
from .notifications import async_send_notification

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TaskCheckpointScheduler:
    """Run warnings, due transitions, and escalation loops."""

    hass: HomeAssistant
    coordinator: TaskCheckpointCoordinator

    def __post_init__(self) -> None:
        self._unsub_interval = None

    @callback
    def async_start(self) -> None:
        """Start background listeners."""
        if self._unsub_interval is not None:
            return
        self._unsub_interval = async_track_time_interval(
            self.hass,
            self._async_handle_tick,
            timedelta(seconds=30),
        )
        self.hass.async_create_task(self._async_handle_tick(dt_util.now()))

    @callback
    def async_stop(self) -> None:
        """Stop background listeners."""
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None

    async def _async_handle_tick(self, now) -> None:
        """Evaluate every task against current time."""
        for definition in DEFAULT_TASKS:
            runtime = self.coordinator.data[definition.task_id]
            due_at = runtime.due_at
            remaining = due_at - now
            overdue = now - due_at

            if runtime.status == STATE_SCHEDULED:
                for warning_minutes in sorted(definition.warning_minutes, reverse=True):
                    seconds_until_warning = warning_minutes * 60
                    if (
                        warning_minutes not in runtime.warning_sent_minutes
                        and 0 <= remaining.total_seconds() <= seconds_until_warning
                        and remaining.total_seconds() >= max(seconds_until_warning - 60, 0)
                    ):
                        await self._async_send_warning(definition.task_id, warning_minutes)

                if now >= due_at:
                    await self.coordinator.async_mark_due(definition.task_id)
                    await self._async_send_due(definition.task_id)

            elif runtime.status == STATE_AWAITING_ACK:
                if overdue >= timedelta(minutes=HARD_MISS_AFTER_MINUTES):
                    await self.coordinator.async_mark_missed(definition.task_id)
                    await self._async_send_missed(definition.task_id)
                    continue

                grace_minutes = definition.ack_timeout_minutes
                if overdue >= timedelta(minutes=grace_minutes + 3):
                    target_level = 3
                elif overdue >= timedelta(minutes=grace_minutes):
                    target_level = 2
                else:
                    target_level = 1

                if target_level > runtime.escalation_level:
                    await self.coordinator.async_set_escalation_level(
                        definition.task_id,
                        target_level,
                    )
                    await self._async_send_escalation(definition.task_id, target_level)

                if overdue >= timedelta(minutes=grace_minutes) and self._should_repeat(
                    runtime.last_nag_iso,
                    DEFAULT_NAG_INTERVAL_MINUTES,
                ):
                    await self._async_send_escalation(definition.task_id, runtime.escalation_level or 2)

            elif runtime.status == STATE_AWAITING_PARENT_VERIFY and self._should_repeat(
                runtime.last_parent_prompt_iso,
                DEFAULT_PARENT_REMINDER_INTERVAL_MINUTES,
            ):
                await self._async_send_parent_prompt(definition.task_id, repeated=True)

            elif runtime.status == STATE_COMPLETED and now >= due_at:
                next_due = self.coordinator.get_next_due(definition.task_id, now)
                await self.coordinator.async_prepare_next_run(definition.task_id, next_due)

            elif runtime.status == STATE_MISSED and now >= due_at + timedelta(days=1):
                next_due = self.coordinator.get_next_due(definition.task_id, now)
                await self.coordinator.async_prepare_next_run(definition.task_id, next_due)

    def _should_repeat(self, last_iso: str | None, interval_minutes: int) -> bool:
        """Return True if enough time has passed to repeat a notification."""
        if last_iso is None:
            return True
        last_dt = dt_util.parse_datetime(last_iso)
        if last_dt is None:
            return True
        return dt_util.now() >= last_dt + timedelta(minutes=interval_minutes)

    async def _async_send_warning(self, task_id: str, warning_minutes: int) -> None:
        runtime = self.coordinator.data[task_id]
        await self.coordinator.async_record_warning(task_id, warning_minutes)
        await self.coordinator.async_fire_event(
            EVENT_WARNING_SENT,
            task_id=task_id,
            extra={"warning_minutes": warning_minutes},
        )
        await async_send_notification(
            self.hass,
            title=f"Task Checkpoint: {runtime.title} soon",
            message=f"{runtime.title} is due in {warning_minutes} minutes.",
            notify_service=self.coordinator.teen_notify_service,
            notification_id=f"task_checkpoint_{task_id}_warning",
            persistent=False,
        )

    async def _async_send_due(self, task_id: str) -> None:
        runtime = self.coordinator.data[task_id]
        await self.coordinator.async_record_due_alert(task_id)
        await self.coordinator.async_fire_event(EVENT_DUE, task_id=task_id)
        await async_send_notification(
            self.hass,
            title=f"Task Checkpoint: {runtime.title} due now",
            message=(
                f"{runtime.title} is due now. Acknowledge the task on your dashboard, "
                f"phone, NFC tag, or task button."
            ),
            notify_service=self.coordinator.teen_notify_service,
            notification_id=f"task_checkpoint_{task_id}_due",
            persistent=True,
        )

    async def _async_send_escalation(self, task_id: str, level: int) -> None:
        runtime = self.coordinator.data[task_id]
        await self.coordinator.async_record_nag(task_id)
        await self.coordinator.async_fire_event(
            EVENT_ESCALATED,
            task_id=task_id,
            extra={"escalation_level": level},
        )

        teen_message = (
            f"{runtime.title} still has not been acknowledged. "
            "Go handle it now and acknowledge the task."
        )
        parent_message = (
            f"{self.coordinator.teen_name} has not acknowledged {runtime.title} yet. "
            f"Escalation level {level} is active."
        )

        await async_send_notification(
            self.hass,
            title=f"Task Checkpoint escalation: {runtime.title}",
            message=teen_message,
            notify_service=self.coordinator.teen_notify_service,
            notification_id=f"task_checkpoint_{task_id}_teen_escalation",
            persistent=True,
            extra_data={"tag": f"task_checkpoint_{task_id}_teen"},
        )

        if level >= 2:
            await async_send_notification(
                self.hass,
                title=f"Task Checkpoint parent alert: {runtime.title}",
                message=parent_message,
                notify_service=self.coordinator.parent_notify_service,
                notification_id=f"task_checkpoint_{task_id}_parent_alert",
                persistent=True,
                extra_data={"tag": f"task_checkpoint_{task_id}_parent"},
            )

    async def _async_send_parent_prompt(self, task_id: str, repeated: bool = False) -> None:
        runtime = self.coordinator.data[task_id]
        await self.coordinator.async_record_parent_prompt(task_id)
        await self.coordinator.async_fire_event(
            EVENT_PARENT_VERIFICATION_REQUESTED,
            task_id=task_id,
            extra={"repeated": repeated},
        )

        repeat_prefix = "Reminder: " if repeated else ""
        parent_message = (
            f"{repeat_prefix}{self.coordinator.teen_name} acknowledged {runtime.title}. "
            "Please verify they are doing it."
        )

        await async_send_notification(
            self.hass,
            title=f"Task Checkpoint verify: {runtime.title}",
            message=parent_message,
            notify_service=self.coordinator.parent_notify_service,
            notification_id=f"task_checkpoint_{task_id}_verify",
            persistent=True,
            extra_data={
                "tag": f"task_checkpoint_{task_id}_verify",
                "actions": [
                    {
                        "action": f"TASK_CHECKPOINT_VERIFY_{task_id.upper()}",
                        "title": "Verify",
                    }
                ],
            },
        )

    async def _async_send_missed(self, task_id: str) -> None:
        runtime = self.coordinator.data[task_id]
        await self.coordinator.async_fire_event(EVENT_MISSED, task_id=task_id)
        await async_send_notification(
            self.hass,
            title=f"Task Checkpoint missed: {runtime.title}",
            message=f"{runtime.title} was not acknowledged and is now marked missed.",
            notify_service=self.coordinator.parent_notify_service,
            notification_id=f"task_checkpoint_{task_id}_missed",
            persistent=True,
        )
        await async_send_notification(
            self.hass,
            title=f"Task Checkpoint missed: {runtime.title}",
            message=f"{runtime.title} was missed.",
            notify_service=self.coordinator.teen_notify_service,
            notification_id=f"task_checkpoint_{task_id}_missed_teen",
            persistent=True,
        )
