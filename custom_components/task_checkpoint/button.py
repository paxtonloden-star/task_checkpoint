
"""Button entities for Task Checkpoint."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TaskCheckpointCoordinator
from .sensor import TaskCheckpointBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Task Checkpoint buttons."""
    coordinator: TaskCheckpointCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[ButtonEntity] = []

    for task_id in coordinator.data:
        entities.append(TaskCheckpointAcknowledgeButton(coordinator, entry, task_id))
        entities.append(TaskCheckpointParentVerifyButton(coordinator, entry, task_id))
        entities.append(TaskCheckpointResetButton(coordinator, entry, task_id))

    async_add_entities(entities)


class TaskCheckpointAcknowledgeButton(TaskCheckpointBaseEntity, ButtonEntity):
    """Button to acknowledge a task."""

    def __init__(self, coordinator: TaskCheckpointCoordinator, entry: ConfigEntry, task_id: str) -> None:
        super().__init__(coordinator, entry, task_id)
        self._attr_unique_id = f"{entry.entry_id}_{task_id}_acknowledge"
        self._attr_name = f"{self._runtime.title} acknowledge"
        self._attr_icon = "mdi:check-circle-outline"

    async def async_press(self) -> None:
        await self.coordinator.async_acknowledge_task(self.task_id)

class TaskCheckpointParentVerifyButton(TaskCheckpointBaseEntity, ButtonEntity):
    """Button to parent verify a task."""

    def __init__(self, coordinator: TaskCheckpointCoordinator, entry: ConfigEntry, task_id: str) -> None:
        super().__init__(coordinator, entry, task_id)
        self._attr_unique_id = f"{entry.entry_id}_{task_id}_parent_verify"
        self._attr_name = f"{self._runtime.title} parent verify"
        self._attr_icon = "mdi:account-check-outline"

    async def async_press(self) -> None:
        await self.coordinator.async_parent_verify_task(self.task_id)

class TaskCheckpointResetButton(TaskCheckpointBaseEntity, ButtonEntity):
    """Button to reset a task to scheduled."""

    def __init__(self, coordinator: TaskCheckpointCoordinator, entry: ConfigEntry, task_id: str) -> None:
        super().__init__(coordinator, entry, task_id)
        self._attr_unique_id = f"{entry.entry_id}_{task_id}_reset"
        self._attr_name = f"{self._runtime.title} reset"
        self._attr_icon = "mdi:backup-restore"

    async def async_press(self) -> None:
        await self.coordinator.async_reset_task(self.task_id)
