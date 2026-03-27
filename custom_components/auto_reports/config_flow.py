"""Config flow for auto reports."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    CONF_ACTIVE,
    CONF_ANOMALY_THRESHOLD,
    CONF_CSV_DIRECTORY,
    CONF_DAILY_TIME,
    CONF_ENABLE_DAILY,
    CONF_ENABLE_MONTHLY,
    CONF_ENABLE_WEEKLY,
    CONF_ENABLE_YEARLY,
    CONF_ENTITY_ID,
    CONF_INCLUDE_IN_SUMMARY,
    CONF_MEDIUM,
    CONF_MONTHLY_TIME,
    CONF_NAME,
    CONF_NOTIFY_TARGETS,
    CONF_PRICE,
    CONF_RETENTION_MONTHS,
    CONF_ROLE,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SOURCES,
    CONF_UNIT,
    CONF_WEEKLY_TIME,
    CONF_YEARLY_TIME,
    DEFAULT_CSV_DIRECTORY,
    DEFAULT_DAILY_TIME,
    DEFAULT_MONTHLY_TIME,
    DEFAULT_NAME,
    DEFAULT_RETENTION_MONTHS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_WEEKLY_TIME,
    DEFAULT_YEARLY_TIME,
    DOMAIN,
    MEDIA,
    ROLES,
)

MENU_SOURCE = "source_menu"
MENU_NOTIFY = "notify_menu"
MENU_SCHEDULE = "schedule_settings"
STEP_ADD_SOURCE = "add_source"
STEP_REMOVE_SOURCE = "remove_source"
STEP_EDIT_SOURCE_SELECT = "edit_source_select"
STEP_EDIT_SOURCE = "edit_source"
STEP_RESET_SOURCE_SELECT = "reset_source_select"
STEP_ADD_NOTIFY = "add_notify"
STEP_REMOVE_NOTIFY = "remove_notify"


class AutoReportsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_CSV_DIRECTORY: user_input[CONF_CSV_DIRECTORY],
                    CONF_RETENTION_MONTHS: user_input[CONF_RETENTION_MONTHS],
                    CONF_DAILY_TIME: user_input[CONF_DAILY_TIME],
                    CONF_WEEKLY_TIME: user_input[CONF_WEEKLY_TIME],
                    CONF_MONTHLY_TIME: user_input[CONF_MONTHLY_TIME],
                    CONF_YEARLY_TIME: user_input[CONF_YEARLY_TIME],
                    CONF_SCAN_INTERVAL_MINUTES: user_input[CONF_SCAN_INTERVAL_MINUTES],
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_CSV_DIRECTORY, default=DEFAULT_CSV_DIRECTORY): str,
                vol.Required(CONF_RETENTION_MONTHS, default=DEFAULT_RETENTION_MONTHS): selector(
                    {"number": {"min": 12, "max": 120, "step": 1, "mode": "box"}}
                ),
                vol.Required(CONF_SCAN_INTERVAL_MINUTES, default=DEFAULT_SCAN_INTERVAL_MINUTES): selector(
                    {"number": {"min": 1, "max": 240, "step": 1, "mode": "box"}}
                ),
                vol.Required(CONF_DAILY_TIME, default=DEFAULT_DAILY_TIME): selector({"time": {}}),
                vol.Required(CONF_WEEKLY_TIME, default=DEFAULT_WEEKLY_TIME): selector({"time": {}}),
                vol.Required(CONF_MONTHLY_TIME, default=DEFAULT_MONTHLY_TIME): selector({"time": {}}),
                vol.Required(CONF_YEARLY_TIME, default=DEFAULT_YEARLY_TIME): selector({"time": {}}),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return AutoReportsOptionsFlow()


class AutoReportsOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for sources and notifications."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self.options: dict[str, Any] | None = None
        self._edited_source_entity_id: str | None = None

    def _ensure_options(self) -> None:
        """Populate editable options from the config entry."""
        if self.options is not None:
            return

        config_entry = self.config_entry
        self.options = deepcopy(dict(config_entry.options))
        self.options.setdefault(CONF_SOURCES, [])
        self.options.setdefault(CONF_NOTIFY_TARGETS, [])
        self.options.setdefault(CONF_ENABLE_DAILY, True)
        self.options.setdefault(CONF_ENABLE_WEEKLY, True)
        self.options.setdefault(CONF_ENABLE_MONTHLY, True)
        self.options.setdefault(CONF_ENABLE_YEARLY, True)
        self.options.setdefault(
            CONF_RETENTION_MONTHS,
            config_entry.data.get(CONF_RETENTION_MONTHS, DEFAULT_RETENTION_MONTHS),
        )
        self.options.setdefault(
            CONF_CSV_DIRECTORY,
            config_entry.data.get(CONF_CSV_DIRECTORY, DEFAULT_CSV_DIRECTORY),
        )
        self.options.setdefault(
            CONF_SCAN_INTERVAL_MINUTES,
            config_entry.data.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES),
        )
        self.options.setdefault(
            CONF_DAILY_TIME, config_entry.data.get(CONF_DAILY_TIME, DEFAULT_DAILY_TIME)
        )
        self.options.setdefault(
            CONF_WEEKLY_TIME, config_entry.data.get(CONF_WEEKLY_TIME, DEFAULT_WEEKLY_TIME)
        )
        self.options.setdefault(
            CONF_MONTHLY_TIME, config_entry.data.get(CONF_MONTHLY_TIME, DEFAULT_MONTHLY_TIME)
        )
        self.options.setdefault(
            CONF_YEARLY_TIME, config_entry.data.get(CONF_YEARLY_TIME, DEFAULT_YEARLY_TIME)
        )

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        return self.async_show_menu(
            step_id="init",
            menu_options=[MENU_SOURCE, MENU_NOTIFY, MENU_SCHEDULE],
        )

    async def async_step_source_menu(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        return self.async_show_menu(
            step_id=MENU_SOURCE,
            menu_options=[STEP_ADD_SOURCE, STEP_EDIT_SOURCE_SELECT, STEP_RESET_SOURCE_SELECT, STEP_REMOVE_SOURCE, "init"],
        )

    async def async_step_edit_source_select(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        sources = self.options.get(CONF_SOURCES, [])
        if not sources:
            return self.async_abort(reason="no_sources")

        if user_input is not None:
            self._edited_source_entity_id = user_input[CONF_ENTITY_ID]
            return await self.async_step_edit_source()

        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITY_ID): selector(
                    {
                        "select": {
                            "options": [
                                {
                                    "value": item[CONF_ENTITY_ID],
                                    "label": f"{item[CONF_NAME]} ({item[CONF_ENTITY_ID]})",
                                }
                                for item in sources
                            ]
                        }
                    }
                )
            }
        )
        return self.async_show_form(step_id=STEP_EDIT_SOURCE_SELECT, data_schema=schema)

    async def async_step_edit_source(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        if not self._edited_source_entity_id:
            return await self.async_step_edit_source_select()

        sources = self.options.get(CONF_SOURCES, [])
        source = next(
            (item for item in sources if item[CONF_ENTITY_ID] == self._edited_source_entity_id),
            None,
        )
        if source is None:
            self._edited_source_entity_id = None
            return self.async_abort(reason="no_sources")

        if user_input is not None:
            source.update(user_input)
            self._edited_source_entity_id = None
            return self.async_create_entry(data=self.options)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=source.get(CONF_NAME, "")): selector({"text": {}}),
                vol.Required(CONF_MEDIUM, default=source.get(CONF_MEDIUM, MEDIA[0])): selector(
                    {
                        "select": {
                            "options": [
                                {"value": item, "label": item.capitalize()} for item in MEDIA
                            ],
                            "mode": "dropdown",
                        }
                    }
                ),
                vol.Required(CONF_ROLE, default=source.get(CONF_ROLE, ROLES[0])): selector(
                    {
                        "select": {
                            "options": [
                                {"value": item, "label": item.capitalize()} for item in ROLES
                            ],
                            "mode": "dropdown",
                        }
                    }
                ),
                vol.Optional(CONF_UNIT, default=source.get(CONF_UNIT, "")): selector({"text": {}}),
                vol.Optional(CONF_PRICE, default=source.get(CONF_PRICE, 0)): selector(
                    {"number": {"min": 0, "max": 999999999, "step": "any", "mode": "box"}}
                ),
                vol.Required(
                    CONF_INCLUDE_IN_SUMMARY,
                    default=source.get(CONF_INCLUDE_IN_SUMMARY, True),
                ): selector({"boolean": {}}),
                vol.Required(CONF_ACTIVE, default=source.get(CONF_ACTIVE, True)): selector({"boolean": {}}),
                vol.Optional(
                    CONF_ANOMALY_THRESHOLD,
                    default=source.get(CONF_ANOMALY_THRESHOLD, 0),
                ): selector(
                    {
                        "number": {
                            "min": 0,
                            "max": 999999999,
                            "step": "any",
                            "mode": "box",
                        }
                    }
                ),
            }
        )
        return self.async_show_form(step_id=STEP_EDIT_SOURCE, data_schema=schema)

    async def async_step_reset_source_select(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        sources = self.options.get(CONF_SOURCES, [])
        if not sources:
            return self.async_abort(reason="no_sources")

        if user_input is not None:
            selected = user_input[CONF_ENTITY_ID]
            manager = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
            if manager is None:
                return self.async_abort(reason="manager_unavailable")
            await manager.async_reset_source_history(selected)
            return self.async_abort(reason="source_history_reset")

        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITY_ID): selector(
                    {
                        "select": {
                            "options": [
                                {
                                    "value": item[CONF_ENTITY_ID],
                                    "label": f"{item[CONF_NAME]} ({item[CONF_ENTITY_ID]})",
                                }
                                for item in sources
                            ]
                        }
                    }
                )
            }
        )
        return self.async_show_form(step_id=STEP_RESET_SOURCE_SELECT, data_schema=schema)

    async def async_step_notify_menu(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        return self.async_show_menu(
            step_id=MENU_NOTIFY,
            menu_options=[STEP_ADD_NOTIFY, STEP_REMOVE_NOTIFY, "init"],
        )

    async def async_step_schedule_settings(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        if user_input is not None:
            self.options.update(user_input)
            return self.async_create_entry(data=self.options)

        schema = vol.Schema(
            {
                vol.Required(CONF_ENABLE_DAILY, default=self.options[CONF_ENABLE_DAILY]): bool,
                vol.Required(CONF_ENABLE_WEEKLY, default=self.options[CONF_ENABLE_WEEKLY]): bool,
                vol.Required(CONF_ENABLE_MONTHLY, default=self.options[CONF_ENABLE_MONTHLY]): bool,
                vol.Required(CONF_ENABLE_YEARLY, default=self.options[CONF_ENABLE_YEARLY]): bool,
                vol.Required(
                    CONF_SCAN_INTERVAL_MINUTES,
                    default=self.options[CONF_SCAN_INTERVAL_MINUTES],
                ): selector({"number": {"min": 1, "max": 240, "step": 1, "mode": "box"}}),
                vol.Required(CONF_DAILY_TIME, default=self.options[CONF_DAILY_TIME]): selector({"time": {}}),
                vol.Required(CONF_WEEKLY_TIME, default=self.options[CONF_WEEKLY_TIME]): selector({"time": {}}),
                vol.Required(CONF_MONTHLY_TIME, default=self.options[CONF_MONTHLY_TIME]): selector({"time": {}}),
                vol.Required(CONF_YEARLY_TIME, default=self.options[CONF_YEARLY_TIME]): selector({"time": {}}),
                vol.Required(CONF_CSV_DIRECTORY, default=self.options[CONF_CSV_DIRECTORY]): str,
                vol.Required(CONF_RETENTION_MONTHS, default=self.options[CONF_RETENTION_MONTHS]): selector(
                    {"number": {"min": 12, "max": 120, "step": 1, "mode": "box"}}
                ),
            }
        )
        return self.async_show_form(step_id=MENU_SCHEDULE, data_schema=schema)

    async def async_step_add_source(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        errors: dict[str, str] = {}

        if user_input is not None:
            existing_entities = {item[CONF_ENTITY_ID] for item in self.options[CONF_SOURCES]}
            if user_input[CONF_ENTITY_ID] in existing_entities:
                errors[CONF_ENTITY_ID] = "source_exists"
            else:
                source = dict(user_input)
                self.options[CONF_SOURCES].append(source)
                return self.async_create_entry(data=self.options)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): selector({"text": {}}),
                vol.Required(CONF_ENTITY_ID): selector(
                    {
                        "entity": {
                            "filter": [
                                {
                                    "domain": ["sensor", "input_number"],
                                }
                            ]
                        }
                    }
                ),
                vol.Required(CONF_MEDIUM, default=MEDIA[0]): selector(
                    {
                        "select": {
                            "options": [
                                {"value": item, "label": item.capitalize()} for item in MEDIA
                            ],
                            "mode": "dropdown",
                        }
                    }
                ),
                vol.Required(CONF_ROLE, default=ROLES[0]): selector(
                    {
                        "select": {
                            "options": [
                                {"value": item, "label": item.capitalize()} for item in ROLES
                            ],
                            "mode": "dropdown",
                        }
                    }
                ),
                vol.Optional(CONF_UNIT, default=""): selector({"text": {}}),
                vol.Optional(CONF_PRICE, default=0): selector(
                    {
                        "number": {
                            "min": 0,
                            "max": 999999,
                            "step": "any",
                            "mode": "box",
                        }
                    }
                ),
                vol.Required(CONF_INCLUDE_IN_SUMMARY, default=True): selector({"boolean": {}}),
                vol.Required(CONF_ACTIVE, default=True): selector({"boolean": {}}),
                vol.Optional(CONF_ANOMALY_THRESHOLD, default=0): selector(
                    {
                        "number": {
                            "min": 0,
                            "max": 999999999,
                            "step": "any",
                            "mode": "box",
                        }
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id=STEP_ADD_SOURCE,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_remove_source(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        sources = self.options.get(CONF_SOURCES, [])
        if not sources:
            return self.async_abort(reason="no_sources")

        if user_input is not None:
            selected = user_input[CONF_ENTITY_ID]
            self.options[CONF_SOURCES] = [
                item for item in sources if item[CONF_ENTITY_ID] != selected
            ]
            return self.async_create_entry(data=self.options)

        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITY_ID): selector(
                    {
                        "select": {
                            "options": [
                                {
                                    "value": item[CONF_ENTITY_ID],
                                    "label": f"{item[CONF_NAME]} ({item[CONF_ENTITY_ID]})",
                                }
                                for item in sources
                            ]
                        }
                    }
                )
            }
        )
        return self.async_show_form(step_id=STEP_REMOVE_SOURCE, data_schema=schema)

    async def async_step_add_notify(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        errors: dict[str, str] = {}
        targets = self._notify_services()
        if not targets:
            return self.async_abort(reason="no_notify_services")

        if user_input is not None:
            target = user_input[CONF_NOTIFY_TARGETS]
            if target in self.options[CONF_NOTIFY_TARGETS]:
                errors[CONF_NOTIFY_TARGETS] = "notify_exists"
            else:
                self.options[CONF_NOTIFY_TARGETS].append(target)
                return self.async_create_entry(data=self.options)

        schema = vol.Schema(
            {
                vol.Required(CONF_NOTIFY_TARGETS): selector(
                    {
                        "select": {
                            "options": [{"value": item, "label": item} for item in targets]
                        }
                    }
                )
            }
        )
        return self.async_show_form(step_id=STEP_ADD_NOTIFY, data_schema=schema, errors=errors)

    async def async_step_remove_notify(self, user_input: dict[str, Any] | None = None):
        self._ensure_options()
        targets = self.options.get(CONF_NOTIFY_TARGETS, [])
        if not targets:
            return self.async_abort(reason="no_notify_targets")

        if user_input is not None:
            selected = user_input[CONF_NOTIFY_TARGETS]
            self.options[CONF_NOTIFY_TARGETS] = [item for item in targets if item != selected]
            return self.async_create_entry(data=self.options)

        schema = vol.Schema(
            {
                vol.Required(CONF_NOTIFY_TARGETS): selector(
                    {
                        "select": {
                            "options": [{"value": item, "label": item} for item in targets]
                        }
                    }
                )
            }
        )
        return self.async_show_form(step_id=STEP_REMOVE_NOTIFY, data_schema=schema)

    def _notify_services(self) -> list[str]:
        services = self.hass.services.async_services().get("notify", {})
        return [f"notify.{service_name}" for service_name in services.keys()]
