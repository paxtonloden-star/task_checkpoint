
"""Notification helpers for Task Checkpoint."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceNotFound

_LOGGER = logging.getLogger(__name__)


async def async_send_notification(
    hass: HomeAssistant,
    *,
    title: str,
    message: str,
    notify_service: str | None = None,
    notification_id: str | None = None,
    persistent: bool = False,
    extra_data: dict[str, Any] | None = None,
) -> None:
    """Send a Task Checkpoint notification.

    If a notify service is configured, it will be called first.
    A persistent notification can also be created for fallback or emphasis.
    """
    if notify_service:
        try:
            await hass.services.async_call(
                "notify",
                notify_service,
                {
                    "title": title,
                    "message": message,
                    "data": extra_data or {},
                },
                blocking=True,
            )
        except ServiceNotFound:
            _LOGGER.warning("Notify service %s was not found", notify_service)
        except Exception:  # pragma: no cover - defensive logging
            _LOGGER.exception("Unexpected error sending Task Checkpoint notification")

    if persistent or not notify_service:
        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": message,
                "notification_id": notification_id or "task_checkpoint",
            },
            blocking=True,
        )
