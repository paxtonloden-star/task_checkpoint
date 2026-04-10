"""Sensor platform for Task Checkpoint."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TaskCheckpointCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Task Checkpoint sensors."""
    coordinator: TaskCheckpointCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for task_id in coordinator.data:
        entities.append(TaskCheckpointStatusSensor(coordinator, entry, task_id))
        entities.append(TaskCheckpointNextDueSensor(coordinator, entry, task_id))

    async_add_entities(entities)


class TaskCheckpointBaseEntity(CoordinatorEntity[TaskCheckpointCoordinator]):
    """Shared base for Task Checkpoint entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TaskCheckpointCoordinator, entry: ConfigEntry, task_id: str) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.task_id = task_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Task Checkpoint {coordinator.teen_name}",
            manufacturer="Task Checkpoint",
            model="Teen Task Manager",
            configuration_url="https://github.com/paxtonloden-star/task_checkpoint",
        )

    @property
    def _runtime(self):
        return self.coordinator.data[self.task_id]


class TaskCheckpointStatusSensor(TaskCheckpointBaseEntity, SensorEntity):
    """Shows the current status of a task."""

    def __init__(self, coordinator: TaskCheckpointCoordinator, entry: ConfigEntry, task_id: str) -> None:
        super().__init__(coordinator, entry, task_id)
        self._attr_unique_id = f"{entry.entry_id}_{task_id}_status"
        self._attr_name = f"{self._runtime.title} status"
        self._attr_icon = "mdi:clipboard-check-outline"

    @property
    def native_value(self) -> str:
        return self._runtime.status

    @property
    def extra_state_attributes(self) -> dict:
        runtime = self._runtime
        return {
            "task_id": runtime.task_id,
            "due_at": runtime.due_iso,
            "last_acknowledged": runtime.last_acknowledged_iso,
            "last_verified": runtime.last_verified_iso,
            "last_completed": runtime.last_completed_iso,
            "acknowledged_by": runtime.acknowledged_by,
            "acknowledgment_method": runtime.acknowledgment_method,
            "verified_by": runtime.verified_by,
            "escalation_level": runtime.escalation_level,
        }


class TaskCheckpointNextDueSensor(TaskCheckpointBaseEntity, SensorEntity):
    """Shows the next due time for a task."""

    _attr_device_class = "timestamp"

    def __init__(self, coordinator: TaskCheckpointCoordinator, entry: ConfigEntry, task_id: str) -> None:
        super().__init__(coordinator, entry, task_id)
        self._attr_unique_id = f"{entry.entry_id}_{task_id}_next_due"
        self._attr_name = f"{self._runtime.title} next due"
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> datetime:
        return self._runtime.due_at
