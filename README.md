
# Task Checkpoint

Task Checkpoint is a custom Home Assistant integration for teen time management and chore accountability.

This scaffold now provides:

- UI setup through a config flow
- default chore definitions for shower, walk dog morning, walk dog evening, dishes, and laundry
- per-task status sensors
- overdue and awaiting-parent binary sensors
- button entities to acknowledge and parent-verify tasks
- services to acknowledge, verify, and reset tasks
- scheduled warnings before due time
- due-now alerts
- repeated escalation reminders until acknowledgement
- repeated parent verification reminders after acknowledgement
- Task Checkpoint bus events for automations and physical-device workflows

## Installation

1. Copy `custom_components/task_checkpoint` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **Task Checkpoint**.

## Current scope

This version includes:

- default scheduled task engine
- warning, due, escalation, and parent reminder notifications
- persistent notification fallback
- optional notify service targets for teen and parent
- event firing through `task_checkpoint_event`

Still planned:

- full options flow
- richer dashboard cards
- NFC/button setup wizard
- long-term history and streak reporting
- richer sensor evidence rules
- brand assets
