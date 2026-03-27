"""sza86 Auto Reports integration."""
from __future__ import annotations

import logging
from functools import partial

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ENTRY_ID,
    ATTR_PERIOD,
    CONF_ENTITY_ID,
    DOMAIN,
    PLATFORMS,
    SERVICE_GENERATE_REPORT,
    SERVICE_RESET_SNAPSHOTS,
    SERVICE_RESET_SOURCE_HISTORY,
)
from .report_manager import ReportManager

_LOGGER = logging.getLogger(__name__)

SERVICE_GENERATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PERIOD): vol.In(["day", "week", "month", "year"]),
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)

SERVICE_RESET_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY_ID): cv.string})
SERVICE_RESET_SOURCE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    manager = ReportManager(hass, entry)
    await manager.async_setup()
    hass.data[DOMAIN][entry.entry_id] = manager

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_GENERATE_REPORT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GENERATE_REPORT,
            partial(_handle_generate_report, hass),
            schema=SERVICE_GENERATE_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_RESET_SNAPSHOTS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESET_SNAPSHOTS,
            partial(_handle_reset_snapshots, hass),
            schema=SERVICE_RESET_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_RESET_SOURCE_HISTORY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESET_SOURCE_HISTORY,
            partial(_handle_reset_source_history, hass),
            schema=SERVICE_RESET_SOURCE_SCHEMA,
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    manager: ReportManager | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if manager:
        await manager.async_unload()

    if not hass.data.get(DOMAIN):
        for service_name in (
            SERVICE_GENERATE_REPORT,
            SERVICE_RESET_SNAPSHOTS,
            SERVICE_RESET_SOURCE_HISTORY,
        ):
            if hass.services.has_service(DOMAIN, service_name):
                hass.services.async_remove(DOMAIN, service_name)
        hass.data.pop(DOMAIN, None)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _handle_generate_report(hass: HomeAssistant, call: ServiceCall) -> None:
    period = call.data[ATTR_PERIOD]
    manager = _resolve_manager(hass, call.data.get(ATTR_ENTRY_ID))
    await manager.async_generate_report(period, send_notifications=True)


async def _handle_reset_snapshots(hass: HomeAssistant, call: ServiceCall) -> None:
    manager = _resolve_manager(hass, call.data.get(ATTR_ENTRY_ID))
    await manager.async_reset_snapshots()


async def _handle_reset_source_history(hass: HomeAssistant, call: ServiceCall) -> None:
    manager = _resolve_manager(hass, call.data.get(ATTR_ENTRY_ID))
    await manager.async_reset_source_history(call.data[CONF_ENTITY_ID])


def _resolve_manager(hass: HomeAssistant, entry_id: str | None) -> ReportManager:
    managers: dict[str, ReportManager] = hass.data.get(DOMAIN, {})
    if not managers:
        raise HomeAssistantError("Integracja nie jest skonfigurowana")
    if entry_id:
        try:
            return managers[entry_id]
        except KeyError as err:
            raise HomeAssistantError(f"Nie znaleziono wpisu integracji: {entry_id}") from err
    return next(iter(managers.values()))
