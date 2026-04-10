"""Constants for Task Checkpoint."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

DOMAIN = "task_checkpoint"
PLATFORMS = ["sensor", "binary_sensor", "button"]

CONF_HOUSEHOLD_NAME = "household_name"
CONF_TEEN_NAME = "teen_name"
CONF_PARENT_NAME = "parent_name"

SERVICE_ACKNOWLEDGE_TASK = "acknowledge_task"
SERVICE_PARENT_VERIFY_TASK = "parent_verify_task"
SERVICE_RESET_TASK = "reset_task"

ATTR_TASK_ID = "task_id"
ATTR_ACTOR = "actor"
ATTR_METHOD = "method"

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1
COORDINATOR_UPDATE_INTERVAL_SECONDS = 30


@dataclass(frozen=True, slots=True)
class DefaultTaskDefinition:
    """Static task definition used by the initial scaffold."""

    task_id: str
    title: str
    due_time: time
    days_of_week: tuple[int, ...]
    warning_minutes: tuple[int, ...]
    ack_timeout_minutes: int
    verify_required: bool


DEFAULT_TASKS: tuple[DefaultTaskDefinition, ...] = (
    DefaultTaskDefinition(
        task_id="shower",
        title="Shower",
        due_time=time(hour=20, minute=0),
        days_of_week=(0, 1, 2, 3, 6),
        warning_minutes=(15, 5),
        ack_timeout_minutes=3,
        verify_required=True,
    ),
    DefaultTaskDefinition(
        task_id="walk_dog_morning",
        title="Walk Dog Morning",
        due_time=time(hour=7, minute=0),
        days_of_week=(0, 1, 2, 3, 4, 5, 6),
        warning_minutes=(15, 5),
        ack_timeout_minutes=4,
        verify_required=True,
    ),
    DefaultTaskDefinition(
        task_id="walk_dog_evening",
        title="Walk Dog Evening",
        due_time=time(hour=18, minute=30),
        days_of_week=(0, 1, 2, 3, 4, 5, 6),
        warning_minutes=(15, 5),
        ack_timeout_minutes=4,
        verify_required=True,
    ),
    DefaultTaskDefinition(
        task_id="dishes",
        title="Dishes",
        due_time=time(hour=19, minute=15),
        days_of_week=(0, 1, 2, 3, 4, 5, 6),
        warning_minutes=(15, 5),
        ack_timeout_minutes=3,
        verify_required=True,
    ),
    DefaultTaskDefinition(
        task_id="laundry",
        title="Laundry",
        due_time=time(hour=10, minute=0),
        days_of_week=(5,),
        warning_minutes=(30, 10),
        ack_timeout_minutes=5,
        verify_required=True,
    ),
)

STATE_SCHEDULED = "scheduled"
STATE_AWAITING_ACK = "awaiting_ack"
STATE_ACKNOWLEDGED = "acknowledged"
STATE_AWAITING_PARENT_VERIFY = "awaiting_parent_verify"
STATE_COMPLETED = "completed"
STATE_MISSED = "missed"
