# Task Checkpoint

Task Checkpoint is a custom Home Assistant integration for teen time management and chore accountability.

This first scaffold provides:

- UI setup through a config flow
- default chore definitions for shower, walk dog morning, walk dog evening, dishes, and laundry
- per-task status sensors
- overdue and awaiting-parent binary sensors
- button entities to acknowledge and parent-verify tasks
- services to acknowledge, verify, and reset tasks
- a coordinator-based runtime model ready for scheduling and escalation logic

## Installation

1. Copy `custom_components/task_checkpoint` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **Task Checkpoint**.

## Current scope

This is the initial scaffold. It includes a working integration shell and entity model, but it does not yet include:

- real due-time scheduling
- escalating notifications
- NFC/button event routing package
- parent actionable notifications
- persistent history/streak reporting

Those are the next build steps.
