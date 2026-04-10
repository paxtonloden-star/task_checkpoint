
"""Config flow for Task Checkpoint."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import (
    CONF_HOUSEHOLD_NAME,
    CONF_PARENT_NAME,
    CONF_PARENT_NOTIFY_SERVICE,
    CONF_TEEN_NAME,
    CONF_TEEN_NOTIFY_SERVICE,
    DOMAIN,
)


class TaskCheckpointConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Task Checkpoint."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id("task_checkpoint_primary")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_HOUSEHOLD_NAME],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self._build_schema(),
            errors=errors,
        )

    @staticmethod
    def _build_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
        """Build the config form schema."""
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_HOUSEHOLD_NAME,
                    default=defaults.get(CONF_HOUSEHOLD_NAME, "Home"),
                ): str,
                vol.Required(
                    CONF_TEEN_NAME,
                    default=defaults.get(CONF_TEEN_NAME, "Teen"),
                ): str,
                vol.Required(
                    CONF_PARENT_NAME,
                    default=defaults.get(CONF_PARENT_NAME, "Parent"),
                ): str,
                vol.Optional(
                    CONF_TEEN_NOTIFY_SERVICE,
                    default=defaults.get(CONF_TEEN_NOTIFY_SERVICE, ""),
                ): str,
                vol.Optional(
                    CONF_PARENT_NOTIFY_SERVICE,
                    default=defaults.get(CONF_PARENT_NOTIFY_SERVICE, ""),
                ): str,
            }
        )
