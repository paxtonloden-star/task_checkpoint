"""Binary sensors for Task Checkpoint."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATE_AWAITING_PARENT_VERIFY, STATE_MISSED
from .coordinator import TaskCheckpointCoordinator
from .sensor import TaskCheckpointBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Task Checkpoint binary sensors."""
    coordinator: TaskCheckpointCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    for task_id in coordinator.data:
        entities.append(TaskCheckpointOverdueBinarySensor(coordinator, entry, task_id))
        entities.append(TaskCheckpointAwaitingParentBinarySensor(coordinator, entry, task_id))

    async_add_entities(entities)


class TaskCheckpointOverdueBinarySensor(TaskCheckpointBaseEntity, BinarySensorEntity):
    """True when a task has been missed."""

    def __init__(self, coordinator: TaskCheckpointCoordinator, entry: ConfigEntry, task_id: str) -> None:
        super().__init__(coordinator, entry, task_id)
        self._attr_unique_id = f"{entry.entry_id}_{task_id}_overdue"
        self._attr_name = f"{self._runtime.title} overdue"
        self._attr_icon = "mdi:alert-circle-outline"

    @property
    def is_on(self) -> bool:
        return self._runtime.status == STATE_MISSED


class TaskCheckpointAwaitingParentBinarySensor(TaskCheckpointBaseEntity, BinarySensorEntity):
    """True when waiting on parent verification."""

    def __init__(self, coordinator: TaskCheckpointCoordinator, entry: ConfigEntry, task_id: str) -> None:
        super().__init__(coordinator, entry, task_id)
        self._attr_unique_id = f"{entry.entry_id}_{task_id}_awaiting_parent"
        self._attr_name = f"{self._runtime.title} awaiting parent"
        self._attr_icon = "mdi:account-supervisor-circle-outline"

    @property
    def is_on(self) -> bool:
        return self._runtime.status == STATE_AWAITING_PARENT_VERIFY
