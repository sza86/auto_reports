"""Sensor platform for auto reports."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import DOMAIN, ENTITY_KEYS, PERIOD_DAY, PERIOD_MONTH, PERIOD_WEEK, PERIOD_YEAR
from .report_manager import ReportManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up report sensors from config entry."""
    manager: ReportManager = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        ReportStatusSensor(manager, entry),
        DatabaseOverviewSensor(manager, entry),
        PeriodReportSensor(manager, entry, PERIOD_DAY),
        PeriodReportSensor(manager, entry, PERIOD_WEEK),
        PeriodReportSensor(manager, entry, PERIOD_MONTH),
        PeriodReportSensor(manager, entry, PERIOD_YEAR),
    ]

    for source in manager.sources:
        entities.extend(
            [
                SourceCurrentValueSensor(manager, entry, source),
                SourceLastStoredValueSensor(manager, entry, source),
                SourceStatusSensor(manager, entry, source),
            ]
        )

    async_add_entities(entities)


class BaseReportSensor(RestoreEntity, SensorEntity):
    """Base class for report sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: ReportManager, entry: ConfigEntry) -> None:
        self.manager = manager
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self.entity_suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "sza86",
            "model": "Automatyzacja raportów",
        }
        self._remove_listener = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._remove_listener = self.manager.register_listener(self._async_manager_updated)
        state = await self.async_get_last_state()
        if state and self.native_value is None:
            self._attr_native_value = state.state

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener:
            self._remove_listener()
        await super().async_will_remove_from_hass()

    @callback
    def _async_manager_updated(self) -> None:
        self.async_write_ha_state()


class ReportStatusSensor(BaseReportSensor):
    """Global status sensor."""

    entity_suffix = "status"
    _attr_translation_key = ENTITY_KEYS["status"]
    _attr_icon = "mdi:file-chart"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str | None:
        return self.manager.overall_status().get("status")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.manager.overall_status()


class DatabaseOverviewSensor(BaseReportSensor):
    """Storage and CSV overview sensor."""

    entity_suffix = "database_overview"
    _attr_translation_key = ENTITY_KEYS["database_overview"]
    _attr_icon = "mdi:database-eye"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str | None:
        return self.manager.database_overview().get("status")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.manager.database_overview()


class PeriodReportSensor(BaseReportSensor):
    """Sensor exposing last report per period."""

    def __init__(self, manager: ReportManager, entry: ConfigEntry, period: str) -> None:
        self.period = period
        self.entity_suffix = period
        self._attr_translation_key = ENTITY_KEYS[period]
        self._attr_icon = "mdi:file-document-outline"
        super().__init__(manager, entry)

    @property
    def native_value(self) -> str | None:
        report = self.manager.last_report(self.period)
        return report.get("status")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        report = self.manager.last_report(self.period)
        return report or {"message": "Brak wygenerowanego raportu"}


class BaseSourceSensor(BaseReportSensor):
    """Base class for dynamic source sensors."""

    _attr_has_entity_name = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, manager: ReportManager, entry: ConfigEntry, source: dict[str, Any]) -> None:
        self.source = source
        self.source_entity_id = source["entity_id"]
        self.source_slug = slugify(self.source_entity_id)
        self.source_name = source["name"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "sza86",
            "model": "Automatyzacja raportów",
        }
        super().__init__(manager, entry)

    def _source_state(self) -> dict[str, Any]:
        return self.manager.source_state(self.source_entity_id)


class SourceCurrentValueSensor(BaseSourceSensor):
    """Current value of a configured source."""

    _attr_icon = "mdi:counter"

    def __init__(self, manager: ReportManager, entry: ConfigEntry, source: dict[str, Any]) -> None:
        self.entity_suffix = f"source_{slugify(source['entity_id'])}_current"
        self._attr_name = f"{source['name']} obecny odczyt"
        super().__init__(manager, entry, source)

    @property
    def native_value(self) -> float | None:
        return self._source_state().get("current_value")

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._source_state().get("unit") or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        source_state = self._source_state()
        return {
            "source_name": source_state.get("name", self.source_name),
            "entity_id": self.source_entity_id,
            "previous_value": source_state.get("previous_value"),
            "last_valid_value": source_state.get("last_valid_value"),
            "raw_state": source_state.get("raw_state"),
            "last_scan": source_state.get("last_scan"),
            "issue": source_state.get("issue"),
        }


class SourceLastStoredValueSensor(BaseSourceSensor):
    """Last valid value stored in integration storage."""

    _attr_icon = "mdi:database"

    def __init__(self, manager: ReportManager, entry: ConfigEntry, source: dict[str, Any]) -> None:
        self.entity_suffix = f"source_{slugify(source['entity_id'])}_previous"
        self._attr_name = f"{source['name']} ostatni odczyt z bazy"
        super().__init__(manager, entry, source)

    @property
    def native_value(self) -> float | None:
        return self._source_state().get("last_valid_value")

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._source_state().get("unit") or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        source_state = self._source_state()
        return {
            "source_name": source_state.get("name", self.source_name),
            "entity_id": self.source_entity_id,
            "current_value": source_state.get("current_value"),
            "previous_value": source_state.get("previous_value"),
            "last_valid_value": source_state.get("last_valid_value"),
            "last_scan": source_state.get("last_scan"),
        }


class SourceStatusSensor(BaseSourceSensor):
    """Diagnostic status sensor per configured source."""

    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, manager: ReportManager, entry: ConfigEntry, source: dict[str, Any]) -> None:
        self.entity_suffix = f"source_{slugify(source['entity_id'])}_status"
        self._attr_name = f"{source['name']} status źródła"
        super().__init__(manager, entry, source)

    @property
    def native_value(self) -> str | None:
        source_state = self._source_state()
        return source_state.get("issue") or source_state.get("status") or "Brak danych"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        source_state = self._source_state()
        if not source_state:
            return {
                "source_name": self.source_name,
                "entity_id": self.source_entity_id,
                "message": "Brak danych diagnostycznych dla źródła",
            }

        periods = source_state.get("periods", {})
        return {
            "source_name": source_state.get("name", self.source_name),
            "entity_id": self.source_entity_id,
            "medium": source_state.get("medium"),
            "role": source_state.get("role"),
            "unit": source_state.get("unit"),
            "status": source_state.get("status"),
            "message": source_state.get("message"),
            "current_value": source_state.get("current_value"),
            "previous_value": source_state.get("previous_value"),
            "last_valid_value": source_state.get("last_valid_value"),
            "raw_state": source_state.get("raw_state"),
            "valid": source_state.get("valid"),
            "issue": source_state.get("issue"),
            "error_origin": source_state.get("error_origin"),
            "error_at": source_state.get("error_at"),
            "last_scan": source_state.get("last_scan"),
            "scan_interval_minutes": source_state.get("scan_interval_minutes"),
            "day_start": source_state.get("day_start"),
            "day_current": source_state.get("day_current"),
            "day_delta": source_state.get("day_delta"),
            "week_start": source_state.get("week_start"),
            "week_current": source_state.get("week_current"),
            "week_delta": source_state.get("week_delta"),
            "month_start": source_state.get("month_start"),
            "month_current": source_state.get("month_current"),
            "month_delta": source_state.get("month_delta"),
            "year_start": source_state.get("year_start"),
            "year_current": source_state.get("year_current"),
            "year_delta": source_state.get("year_delta"),
            "periods": periods,
        }
