
"""Task Checkpoint integration."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (
    ATTR_ACTOR,
    ATTR_METHOD,
    ATTR_TASK_ID,
    DOMAIN,
    PLATFORMS,
    SERVICE_ACKNOWLEDGE_TASK,
    SERVICE_PARENT_VERIFY_TASK,
    SERVICE_RESET_TASK,
)
from .coordinator import TaskCheckpointCoordinator
from .scheduler import TaskCheckpointScheduler

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TASK_ID): cv.string,
        vol.Optional(ATTR_ACTOR): cv.string,
        vol.Optional(ATTR_METHOD): cv.string,
    }
)

RESET_SCHEMA = vol.Schema({vol.Required(ATTR_TASK_ID): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Task Checkpoint component."""
    hass.data.setdefault(DOMAIN, {})
    await _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Task Checkpoint from a config entry."""
    coordinator = TaskCheckpointCoordinator(hass, entry.entry_id, entry.data)
    await coordinator.async_initialize()

    scheduler = TaskCheckpointScheduler(hass, coordinator)
    scheduler.async_start()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "scheduler": scheduler,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data:
        scheduler: TaskCheckpointScheduler = entry_data["scheduler"]
        scheduler.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_ACKNOWLEDGE_TASK):
        return

    async def handle_acknowledge(call: ServiceCall) -> None:
        coordinator = _find_coordinator_for_task(hass, call.data[ATTR_TASK_ID])
        await coordinator.async_acknowledge_task(
            call.data[ATTR_TASK_ID],
            actor=call.data.get(ATTR_ACTOR),
            method=call.data.get(ATTR_METHOD),
        )

    async def handle_parent_verify(call: ServiceCall) -> None:
        coordinator = _find_coordinator_for_task(hass, call.data[ATTR_TASK_ID])
        await coordinator.async_parent_verify_task(
            call.data[ATTR_TASK_ID],
            actor=call.data.get(ATTR_ACTOR),
        )

    async def handle_reset(call: ServiceCall) -> None:
        coordinator = _find_coordinator_for_task(hass, call.data[ATTR_TASK_ID])
        await coordinator.async_reset_task(call.data[ATTR_TASK_ID])

    hass.services.async_register(
        DOMAIN,
        SERVICE_ACKNOWLEDGE_TASK,
        handle_acknowledge,
        schema=SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PARENT_VERIFY_TASK,
        handle_parent_verify,
        schema=SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_TASK,
        handle_reset,
        schema=RESET_SCHEMA,
    )


def _find_coordinator_for_task(hass: HomeAssistant, task_id: str) -> TaskCheckpointCoordinator:
    """Find the coordinator that owns a task."""
    entries: Iterable[dict[str, Any]] = hass.data.get(DOMAIN, {}).values()
    for entry_data in entries:
        coordinator: TaskCheckpointCoordinator = entry_data["coordinator"]
        if task_id in coordinator.data:
            return coordinator
    raise HomeAssistantError(f"Unknown task_id: {task_id}")
