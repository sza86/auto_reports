"""Report manager for auto reports."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, time, timedelta
import csv
import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_COMPARISON,
    ATTR_CSV_FILE,
    ATTR_DETAILS,
    ATTR_GENERATED_AT,
    ATTR_ISSUES_COUNT,
    ATTR_MESSAGE,
    ATTR_PERIOD,
    ATTR_STATUS,
    ATTR_SUMMARY,
    ATTR_TOTAL_COST,
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
    DEFAULT_OPTIONS,
    DOMAIN,
    MEDIA,
    PERIOD_DAY,
    PERIOD_LABELS_PL,
    PERIOD_MONTH,
    PERIOD_WEEK,
    PERIOD_YEAR,
    PERIODS,
    ROLE_EXPORT,
    ROLE_INFORMATIONAL,
    STATUS_OK,
    STATUS_PROBLEM,
    STATUS_WARNING,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ReportResult:
    """Container for generated report data."""

    period: str
    generated_at: str
    status: str
    message: str
    total_cost: float
    issues_count: int
    summary: dict[str, Any]
    details: list[dict[str, Any]]
    comparison: dict[str, Any]
    csv_file: str | None
    period_label: str

    def as_dict(self) -> dict[str, Any]:
        """Return result as dictionary."""
        return {
            ATTR_PERIOD: self.period,
            ATTR_GENERATED_AT: self.generated_at,
            ATTR_STATUS: self.status,
            ATTR_MESSAGE: self.message,
            ATTR_TOTAL_COST: round(self.total_cost, 2),
            ATTR_ISSUES_COUNT: self.issues_count,
            ATTR_SUMMARY: self.summary,
            ATTR_DETAILS: self.details,
            ATTR_COMPARISON: self.comparison,
            ATTR_CSV_FILE: self.csv_file,
            "period_label": self.period_label,
        }


class ReportManager:
    """Handle snapshots, reports, CSV and notifications."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}")
        self.data: dict[str, Any] = {}
        self._listeners: list[Any] = []
        self._update_callbacks: list[Any] = []
        self._last_scan: datetime | None = None

    @property
    def config(self) -> dict[str, Any]:
        """Return merged config for the entry."""
        merged = deepcopy(DEFAULT_OPTIONS)
        merged.update(self.entry.data)
        merged.update(self.entry.options)
        return merged

    @property
    def title(self) -> str:
        return self.entry.title

    @property
    def sources(self) -> list[dict[str, Any]]:
        return [s for s in self.config.get(CONF_SOURCES, []) if s.get(CONF_ACTIVE, True)]

    @property
    def notify_targets(self) -> list[str]:
        return self.config.get(CONF_NOTIFY_TARGETS, [])

    @property
    def scan_interval_minutes(self) -> int:
        value = self.config.get(CONF_SCAN_INTERVAL_MINUTES, 10)
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 10

    async def async_setup(self) -> None:
        """Load storage and schedule jobs."""
        stored = await self.store.async_load()
        self.data = self._normalize_store(stored or self._empty_store())
        await self._async_initialize_snapshots_if_needed()
        await self.async_scan_sources()
        await self._async_refresh_recent_csv_files()
        self._schedule_jobs()

    async def async_unload(self) -> None:
        """Unload manager listeners."""
        for unsub in self._listeners:
            try:
                unsub()
            except Exception:  # pragma: no cover - defensive
                _LOGGER.debug("Failed to unsubscribe cleanly", exc_info=True)
        self._listeners.clear()
        self._update_callbacks.clear()

    def _empty_store(self) -> dict[str, Any]:
        return {
            "initialized": False,
            "snapshots": {period: {} for period in PERIODS},
            "last_valid": {},
            "issues": {},
            "last_reports": {},
            "last_scan": None,
            "source_states": {},
            "recent_csv_files": [],
        }

    def _normalize_store(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = deepcopy(payload)
        normalized.setdefault("initialized", False)
        normalized.setdefault("snapshots", {})
        for period in PERIODS:
            normalized["snapshots"].setdefault(period, {})
        normalized.setdefault("last_valid", {})
        normalized.setdefault("issues", {})
        normalized.setdefault("last_reports", {})
        normalized.setdefault("last_scan", None)
        normalized.setdefault("source_states", {})
        normalized.setdefault("recent_csv_files", [])
        return normalized

    async def _async_initialize_snapshots_if_needed(self) -> None:
        """Initialize snapshots using current sensor values on first run."""
        if self.data.get("initialized"):
            return

        current = self._read_current_values()
        for period in PERIODS:
            self.data["snapshots"][period] = {
                entity_id: values["value"]
                for entity_id, values in current.items()
                if values["valid"] and values["value"] is not None
            }
        self.data["last_valid"] = {
            entity_id: values["value"]
            for entity_id, values in current.items()
            if values["valid"] and values["value"] is not None
        }
        self.data["initialized"] = True
        self.data["last_scan"] = dt_util.utcnow().isoformat()
        await self._async_save()

    def _schedule_jobs(self) -> None:
        """Create poll and schedule listeners."""
        self._listeners.append(
            async_track_time_interval(
                self.hass,
                self._async_poll_callback,
                timedelta(minutes=self.scan_interval_minutes),
            )
        )

        if self.config.get(CONF_ENABLE_DAILY, True):
            self._listeners.append(
                async_track_time_change(
                    self.hass,
                    self._async_daily_callback,
                    **self._parse_time(self.config[CONF_DAILY_TIME]),
                )
            )
        if self.config.get(CONF_ENABLE_WEEKLY, True):
            self._listeners.append(
                async_track_time_change(
                    self.hass,
                    self._async_weekly_callback,
                    **self._parse_time(self.config[CONF_WEEKLY_TIME]),
                )
            )
        if self.config.get(CONF_ENABLE_MONTHLY, True):
            self._listeners.append(
                async_track_time_change(
                    self.hass,
                    self._async_monthly_callback,
                    **self._parse_time(self.config[CONF_MONTHLY_TIME]),
                )
            )
        if self.config.get(CONF_ENABLE_YEARLY, True):
            self._listeners.append(
                async_track_time_change(
                    self.hass,
                    self._async_yearly_callback,
                    **self._parse_time(self.config[CONF_YEARLY_TIME]),
                )
            )

    @callback
    async def _async_poll_callback(self, now: datetime) -> None:
        await self.async_scan_sources()

    @callback
    async def _async_daily_callback(self, now: datetime) -> None:
        await self.async_generate_report(PERIOD_DAY, send_notifications=True)

    @callback
    async def _async_weekly_callback(self, now: datetime) -> None:
        if now.weekday() == 0:
            await self.async_generate_report(PERIOD_WEEK, send_notifications=True)

    @callback
    async def _async_monthly_callback(self, now: datetime) -> None:
        if now.day == 1:
            await self.async_generate_report(PERIOD_MONTH, send_notifications=True)

    @callback
    async def _async_yearly_callback(self, now: datetime) -> None:
        if now.month == 1 and now.day == 1:
            await self.async_generate_report(PERIOD_YEAR, send_notifications=True)

    async def _async_save(self) -> None:
        await self.store.async_save(self.data)

    def _parse_time(self, value: str) -> dict[str, int]:
        parsed = time.fromisoformat(value)
        return {"hour": parsed.hour, "minute": parsed.minute, "second": parsed.second}

    def _read_current_values(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        last_valid: dict[str, float] = self.data.get("last_valid", {})

        for source in self.sources:
            entity_id = source[CONF_ENTITY_ID]
            state = self.hass.states.get(entity_id)
            issue = None
            error_origin = None
            value: float | None = None
            valid = False
            raw_state = state.state if state is not None else None
            unit = source.get(CONF_UNIT) or (
                state.attributes.get("unit_of_measurement") if state else None
            )

            if state is None:
                issue = "Encja nie istnieje"
                error_origin = "Źródłowa encja nie została znaleziona w Home Assistant"
            elif state.state in {"unknown", "unavailable", "none", "None"}:
                issue = "Brak danych"
                error_origin = "Stan encji źródłowej jest unknown lub unavailable"
            else:
                try:
                    value = float(state.state)
                    valid = True
                    previous = last_valid.get(entity_id)
                    threshold = source.get(CONF_ANOMALY_THRESHOLD)
                    if previous is not None and value < previous:
                        issue = "Licznik cofnął się lub został zresetowany"
                        error_origin = (
                            "Bieżący odczyt jest mniejszy od poprzedniego poprawnego odczytu"
                        )
                        valid = False
                    elif previous is not None and threshold not in (None, ""):
                        try:
                            threshold_f = float(threshold)
                        except (TypeError, ValueError):
                            threshold_f = None
                        if (
                            threshold_f is not None
                            and threshold_f > 0
                            and abs(value - previous) > threshold_f
                        ):
                            issue = "Wykryto anomalię odczytu"
                            error_origin = (
                                "Różnica względem poprzedniego poprawnego odczytu przekroczyła próg anomalii"
                            )
                            valid = False
                except (TypeError, ValueError):
                    issue = "Nieprawidłowa wartość licznika"
                    error_origin = "Nie udało się zamienić stanu encji na liczbę"

            result[entity_id] = {
                "value": value,
                "valid": valid,
                "issue": issue,
                "unit": unit,
                "raw_state": raw_state,
                "error_origin": error_origin,
            }
        return result

    def _prune_removed_sources(self) -> None:
        active_entity_ids = {source[CONF_ENTITY_ID] for source in self.sources}
        self.data["last_valid"] = {
            entity_id: value
            for entity_id, value in self.data.get("last_valid", {}).items()
            if entity_id in active_entity_ids
        }
        self.data["issues"] = {
            entity_id: value
            for entity_id, value in self.data.get("issues", {}).items()
            if entity_id in active_entity_ids
        }
        self.data["source_states"] = {
            entity_id: value
            for entity_id, value in self.data.get("source_states", {}).items()
            if entity_id in active_entity_ids
        }
        for period in PERIODS:
            snapshots = self.data.get("snapshots", {}).get(period, {})
            self.data["snapshots"][period] = {
                entity_id: value
                for entity_id, value in snapshots.items()
                if entity_id in active_entity_ids
            }

    def _build_period_state(
        self,
        entity_id: str,
        current_item: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        periods: dict[str, dict[str, Any]] = {}
        current_value = current_item.get("value")
        current_valid = current_item.get("valid", False)
        for period in PERIODS:
            start_value = self.data.get("snapshots", {}).get(period, {}).get(entity_id)
            delta = None
            if current_valid and start_value is not None and current_value is not None:
                raw_delta = current_value - start_value
                if raw_delta >= 0:
                    delta = round(raw_delta, 3)
            periods[period] = {
                "start": start_value,
                "current": current_value,
                "delta": delta,
            }
        return periods

    async def async_scan_sources(self) -> None:
        """Scan current values and store last valid values."""
        self._prune_removed_sources()
        current = self._read_current_values()
        issues: dict[str, dict[str, Any]] = {}
        previous_states: dict[str, dict[str, Any]] = self.data.get("source_states", {})
        now_iso = dt_util.utcnow().isoformat()
        source_states: dict[str, dict[str, Any]] = {}

        for source in self.sources:
            entity_id = source[CONF_ENTITY_ID]
            item = current[entity_id]
            previous_state = previous_states.get(entity_id, {})
            previous_value = previous_state.get("current_value")
            if previous_value is None:
                previous_value = previous_state.get("last_valid_value")

            if item["valid"] and item["value"] is not None:
                self.data.setdefault("last_valid", {})[entity_id] = item["value"]
                error_at = None
            else:
                error_at = now_iso if item["issue"] else None
                if item["issue"]:
                    issues[entity_id] = {
                        "name": source[CONF_NAME],
                        "entity_id": entity_id,
                        "issue": item["issue"],
                        "origin": item.get("error_origin"),
                        "raw_state": item.get("raw_state"),
                        "at": error_at,
                    }

            last_valid_value = self.data.get("last_valid", {}).get(entity_id)
            periods = self._build_period_state(entity_id, item)
            source_state = {
                "name": source[CONF_NAME],
                "entity_id": entity_id,
                "medium": source.get(CONF_MEDIUM),
                "role": source.get(CONF_ROLE),
                "unit": item.get("unit") or source.get(CONF_UNIT) or "",
                "raw_state": item.get("raw_state"),
                "current_value": item.get("value"),
                "previous_value": previous_value,
                "last_valid_value": last_valid_value,
                "valid": item.get("valid", False),
                "issue": item.get("issue"),
                "error_origin": item.get("error_origin"),
                "error_at": error_at,
                "last_scan": now_iso,
                "periods": periods,
            }
            for period, values in periods.items():
                source_state[f"{period}_start"] = values["start"]
                source_state[f"{period}_current"] = values["current"]
                source_state[f"{period}_delta"] = values["delta"]
            source_states[entity_id] = source_state

        self.data["source_states"] = source_states
        self.data["issues"] = issues
        self.data["last_scan"] = now_iso
        self._last_scan = dt_util.utcnow()
        await self._async_save()
        self._fire_update_signal()

    def _get_issue(self, entity_id: str) -> str | None:
        issue = self.data.get("issues", {}).get(entity_id)
        return issue["issue"] if issue else None

    async def async_generate_report(self, period: str, send_notifications: bool = True) -> ReportResult:
        """Generate report for the selected period."""
        if period not in PERIODS:
            raise HomeAssistantError(f"Nieobsługiwany okres raportu: {period}")

        await self.async_scan_sources()
        current = self._read_current_values()
        start_snapshot: dict[str, float] = self.data["snapshots"].get(period, {})
        generated_at = dt_util.now().isoformat()

        details: list[dict[str, Any]] = []
        summary: dict[str, dict[str, Any]] = {}
        issues_count = 0
        total_cost = 0.0

        aggregated: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for source in self.sources:
            entity_id = source[CONF_ENTITY_ID]
            source_name = source[CONF_NAME]
            medium = source[CONF_MEDIUM]
            role = source[CONF_ROLE]
            unit = source.get(CONF_UNIT) or current[entity_id]["unit"] or ""
            price = self._as_float(source.get(CONF_PRICE))
            include = source.get(CONF_INCLUDE_IN_SUMMARY, True)
            current_item = current[entity_id]
            start_value = start_snapshot.get(entity_id)
            issue = current_item["issue"] or self._get_issue(entity_id)
            delta = None
            cost = None

            if current_item["valid"] and current_item["value"] is not None and start_value is not None:
                delta = current_item["value"] - start_value
                if delta < 0:
                    issue = "Wartość okresowa ujemna — sprawdź licznik"
                    delta = None
            else:
                issue = issue or "Brak danych startowych okresu"

            if delta is not None and price is not None and role not in {ROLE_EXPORT, ROLE_INFORMATIONAL}:
                cost = round(delta * price, 2)
                total_cost += cost

            if issue:
                issues_count += 1

            detail = {
                "name": source_name,
                "entity_id": entity_id,
                "medium": medium,
                "role": role,
                "unit": unit,
                "start": start_value,
                "current": current_item["value"],
                "delta": round(delta, 3) if delta is not None else None,
                "price": price,
                "cost": cost,
                "issue": issue,
            }
            details.append(detail)

            if include and delta is not None:
                aggregated[medium][role] += delta
                if cost is not None:
                    aggregated[medium]["cost"] += cost

        for medium in MEDIA:
            if medium in aggregated:
                summary[medium] = {
                    key: round(value, 3 if key != "cost" else 2)
                    for key, value in aggregated[medium].items()
                }

        status = STATUS_OK
        if issues_count > 0:
            status = STATUS_WARNING
        if issues_count and all(item.get("delta") is None for item in details):
            status = STATUS_PROBLEM

        comparison = self._build_comparison(period, summary)
        message = self._build_message(period, status, issues_count, total_cost, summary, comparison)
        csv_file = await self._async_write_csv(
            period,
            generated_at,
            summary,
            details,
            comparison,
            status,
            total_cost,
        )

        result = ReportResult(
            period=period,
            generated_at=generated_at,
            status=status,
            message=message,
            total_cost=round(total_cost, 2),
            issues_count=issues_count,
            summary=summary,
            details=details,
            comparison=comparison,
            csv_file=csv_file,
            period_label=PERIOD_LABELS_PL[period],
        )

        self.data.setdefault("last_reports", {})[period] = result.as_dict()
        self.data["snapshots"][period] = {
            entity_id: item["value"]
            for entity_id, item in current.items()
            if item["valid"] and item["value"] is not None
        }
        await self._async_save()
        self._fire_update_signal()

        if send_notifications:
            await self._async_send_notifications(result)

        return result

    def _build_comparison(self, period: str, summary: dict[str, Any]) -> dict[str, Any]:
        if period not in {PERIOD_MONTH, PERIOD_YEAR}:
            return {}

        previous = self.data.get("last_reports", {}).get(period)
        if not previous:
            return {}

        comparison: dict[str, Any] = {}
        previous_summary: dict[str, dict[str, Any]] = previous.get(ATTR_SUMMARY, {})
        for medium, current_values in summary.items():
            prev_medium = previous_summary.get(medium)
            if not prev_medium:
                continue
            comparison[medium] = {}
            for key, current_value in current_values.items():
                previous_value = prev_medium.get(key)
                if previous_value in (None, 0):
                    continue
                diff = round(current_value - previous_value, 3 if key != "cost" else 2)
                percent = round((diff / previous_value) * 100, 1)
                comparison[medium][key] = {
                    "previous": previous_value,
                    "difference": diff,
                    "percent": percent,
                }
        return comparison

    async def _async_write_csv(
        self,
        period: str,
        generated_at: str,
        summary: dict[str, Any],
        details: list[dict[str, Any]],
        comparison: dict[str, Any],
        status: str,
        total_cost: float,
    ) -> str | None:
        directory = Path(self.config[CONF_CSV_DIRECTORY])
        now = dt_util.now()
        filename = directory / f"reports_{now.year}.csv"
        await self.hass.async_add_executor_job(lambda: directory.mkdir(parents=True, exist_ok=True))

        rows: list[dict[str, Any]] = []
        for detail in details:
            rows.append(
                {
                    "generated_at": generated_at,
                    "period": period,
                    "status": status,
                    "source_name": detail["name"],
                    "entity_id": detail["entity_id"],
                    "medium": detail["medium"],
                    "role": detail["role"],
                    "unit": detail["unit"],
                    "start": detail["start"],
                    "current": detail["current"],
                    "delta": detail["delta"],
                    "price": detail["price"],
                    "cost": detail["cost"],
                    "issue": detail["issue"],
                    "summary_json": "",
                    "comparison_json": "",
                    "total_cost": total_cost,
                }
            )

        rows.append(
            {
                "generated_at": generated_at,
                "period": period,
                "status": status,
                "source_name": "__SUMMARY__",
                "entity_id": "",
                "medium": "all",
                "role": "summary",
                "unit": "",
                "start": "",
                "current": "",
                "delta": "",
                "price": "",
                "cost": "",
                "issue": "",
                "summary_json": json.dumps(summary, ensure_ascii=False),
                "comparison_json": json.dumps(comparison, ensure_ascii=False),
                "total_cost": total_cost,
            }
        )

        headers = list(rows[0].keys()) if rows else []
        await self.hass.async_add_executor_job(self._write_csv_sync, filename, headers, rows)
        await self.hass.async_add_executor_job(self._cleanup_old_csv_files, directory)
        await self._async_refresh_recent_csv_files()
        return str(filename)

    def _write_csv_sync(self, filename: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
        exists = filename.exists()
        with filename.open("a", newline="", encoding="utf-8") as file_handle:
            writer = csv.DictWriter(file_handle, fieldnames=headers)
            if not exists:
                writer.writeheader()
            writer.writerows(rows)

    def _cleanup_old_csv_files(self, directory: Path) -> None:
        retention_years = max(1, int(self.config[CONF_RETENTION_MONTHS] / 12))
        min_year = dt_util.now().year - retention_years
        for path in directory.glob("reports_*.csv"):
            try:
                year_str = path.stem.replace("reports_", "")
                year = int(year_str)
            except ValueError:
                continue
            if year < min_year:
                path.unlink(missing_ok=True)

    async def _async_send_notifications(self, result: ReportResult) -> None:
        title = f"Raport {result.period_label} — {self.title}"
        for target in self.notify_targets:
            try:
                domain, service = target.split(".", 1)
            except ValueError:
                _LOGGER.warning("Invalid notify target configured: %s", target)
                continue
            if not self.hass.services.has_service(domain, service):
                _LOGGER.warning("Notify target %s is not available", target)
                continue
            await self.hass.services.async_call(
                domain,
                service,
                {"title": title, "message": result.message},
                blocking=True,
            )

    def _build_message(
        self,
        period: str,
        status: str,
        issues_count: int,
        total_cost: float,
        summary: dict[str, Any],
        comparison: dict[str, Any],
    ) -> str:
        lines = [f"Raport {PERIOD_LABELS_PL[period]}: {status}"]
        for medium, values in summary.items():
            line = f"- {medium.capitalize()}: "
            parts = []
            for key, value in values.items():
                if key == "cost":
                    parts.append(f"koszt {value:.2f} zł")
                else:
                    parts.append(f"{key} {value}")
            lines.append(line + ", ".join(parts))
        lines.append(f"Koszt łączny: {total_cost:.2f} zł")
        if issues_count:
            lines.append(f"Problemy z danymi: {issues_count}")
        if comparison:
            lines.append("Porównanie do poprzedniego okresu dostępne w atrybutach raportu.")
        return "\n".join(lines)

    def last_report(self, period: str) -> dict[str, Any]:
        return self.data.get("last_reports", {}).get(period, {})

    def source_state(self, entity_id: str) -> dict[str, Any]:
        source_state = deepcopy(self.data.get("source_states", {}).get(entity_id, {}))
        if not source_state:
            return {}

        issue_info = self.data.get("issues", {}).get(entity_id, {})
        source_state[ATTR_STATUS] = STATUS_OK if not issue_info else STATUS_WARNING
        source_state[ATTR_MESSAGE] = issue_info.get("issue") or "Brak aktywnych problemów"
        source_state[ATTR_ISSUES_COUNT] = 0 if not issue_info else 1
        source_state["scan_interval_minutes"] = self.scan_interval_minutes
        source_state["csv_directory"] = self.config.get(CONF_CSV_DIRECTORY)
        source_state["error_origin"] = issue_info.get("origin") or source_state.get("error_origin")
        source_state["error_at"] = issue_info.get("at") or source_state.get("error_at")
        return source_state

    def overall_status(self) -> dict[str, Any]:
        issues = self.data.get("issues", {})
        status = STATUS_OK if not issues else STATUS_WARNING
        return {
            ATTR_STATUS: status,
            ATTR_ISSUES_COUNT: len(issues),
            ATTR_MESSAGE: "Brak aktywnych problemów" if not issues else "Wykryto problemy z danymi",
            "issues": list(issues.values()),
            "last_scan": self.data.get("last_scan"),
            "sources_count": len(self.sources),
            "notify_targets": self.notify_targets,
            "scan_interval_minutes": self.scan_interval_minutes,
        }

    def database_overview(self) -> dict[str, Any]:
        issues = self.data.get("issues", {})
        last_reports = self.data.get("last_reports", {})
        snapshots = self.data.get("snapshots", {})
        source_states = self.data.get("source_states", {})

        reports_summary = {
            period: {
                ATTR_STATUS: report.get(ATTR_STATUS),
                ATTR_GENERATED_AT: report.get(ATTR_GENERATED_AT),
                ATTR_ISSUES_COUNT: report.get(ATTR_ISSUES_COUNT),
                ATTR_TOTAL_COST: report.get(ATTR_TOTAL_COST),
                ATTR_CSV_FILE: report.get(ATTR_CSV_FILE),
            }
            for period, report in last_reports.items()
        }

        return {
            ATTR_STATUS: STATUS_OK if not issues else STATUS_WARNING,
            ATTR_MESSAGE: "Podgląd storage i CSV gotowy",
            "store_key": f"{DOMAIN}_{self.entry.entry_id}",
            "entry_id": self.entry.entry_id,
            "last_scan": self.data.get("last_scan"),
            "scan_interval_minutes": self.scan_interval_minutes,
            "csv_directory": self.config.get(CONF_CSV_DIRECTORY),
            "sources_count": len(self.sources),
            "tracked_entities": [source[CONF_ENTITY_ID] for source in self.sources],
            "issues_count": len(issues),
            "issue_entities": list(issues.keys()),
            "snapshots_count": {
                period: len(snapshots.get(period, {})) for period in PERIODS
            },
            "source_states_count": len(source_states),
            "last_reports": reports_summary,
            "recent_csv_files": deepcopy(self.data.get("recent_csv_files", [])),
        }

    async def async_reset_snapshots(self) -> None:
        current = self._read_current_values()
        for period in PERIODS:
            self.data["snapshots"][period] = {
                entity_id: item["value"]
                for entity_id, item in current.items()
                if item["valid"] and item["value"] is not None
            }
        await self._async_save()
        self._fire_update_signal()

    async def async_reset_source_history(self, entity_id: str) -> None:
        """Reset stored history for a single configured source."""
        configured_entities = {source[CONF_ENTITY_ID] for source in self.sources}
        if entity_id not in configured_entities:
            raise HomeAssistantError(f"Źródło nie jest skonfigurowane: {entity_id}")

        self.data.setdefault("last_valid", {}).pop(entity_id, None)
        self.data.setdefault("issues", {}).pop(entity_id, None)
        self.data.setdefault("source_states", {}).pop(entity_id, None)
        for period in PERIODS:
            self.data.setdefault("snapshots", {}).setdefault(period, {}).pop(entity_id, None)

        current = self._read_current_values().get(entity_id)
        if current and current.get("valid") and current.get("value") is not None:
            current_value = current["value"]
            self.data.setdefault("last_valid", {})[entity_id] = current_value
            for period in PERIODS:
                self.data.setdefault("snapshots", {}).setdefault(period, {})[entity_id] = current_value

        await self.async_scan_sources()

    def register_listener(self, update_callback) -> callback:
        self._update_callbacks.append(update_callback)

        def _remove_listener() -> None:
            if update_callback in self._update_callbacks:
                self._update_callbacks.remove(update_callback)

        return _remove_listener

    def _fire_update_signal(self) -> None:
        for listener in self._update_callbacks:
            try:
                listener()
            except Exception:  # pragma: no cover - defensive
                _LOGGER.debug("Listener update failed", exc_info=True)

    async def _async_refresh_recent_csv_files(self) -> None:
        self.data["recent_csv_files"] = await self.hass.async_add_executor_job(
            self._list_recent_csv_files_sync
        )

    def _list_recent_csv_files_sync(self) -> list[dict[str, Any]]:
        directory = Path(self.config[CONF_CSV_DIRECTORY])
        if not directory.exists():
            return []

        files: list[dict[str, Any]] = []
        for path in sorted(directory.glob("reports_*.csv"), key=lambda item: item.stat().st_mtime, reverse=True)[:5]:
            stat = path.stat()
            files.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=dt_util.DEFAULT_TIME_ZONE).isoformat()
                    if dt_util.DEFAULT_TIME_ZONE
                    else datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
        return files

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
