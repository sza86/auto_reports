"""Constants for the auto reports integration."""
from __future__ import annotations

DOMAIN = "auto_reports"
PLATFORMS = ["sensor"]

CONF_NAME = "name"
CONF_CSV_DIRECTORY = "csv_directory"
CONF_RETENTION_MONTHS = "retention_months"
CONF_DAILY_TIME = "daily_time"
CONF_WEEKLY_TIME = "weekly_time"
CONF_MONTHLY_TIME = "monthly_time"
CONF_YEARLY_TIME = "yearly_time"
CONF_ENABLE_DAILY = "enable_daily"
CONF_ENABLE_WEEKLY = "enable_weekly"
CONF_ENABLE_MONTHLY = "enable_monthly"
CONF_ENABLE_YEARLY = "enable_yearly"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
CONF_SOURCES = "sources"
CONF_NOTIFY_TARGETS = "notify_targets"

CONF_ENTITY_ID = "entity_id"
CONF_MEDIUM = "medium"
CONF_ROLE = "role"
CONF_UNIT = "unit"
CONF_PRICE = "price"
CONF_INCLUDE_IN_SUMMARY = "include_in_summary"
CONF_ACTIVE = "active"
CONF_ANOMALY_THRESHOLD = "anomaly_threshold"

ATTR_PERIOD = "period"
ATTR_GENERATED_AT = "generated_at"
ATTR_STATUS = "status"
ATTR_MESSAGE = "message"
ATTR_TOTAL_COST = "total_cost"
ATTR_ISSUES_COUNT = "issues_count"
ATTR_SUMMARY = "summary"
ATTR_DETAILS = "details"
ATTR_COMPARISON = "comparison"
ATTR_CSV_FILE = "csv_file"
ATTR_ENTRY_ID = "entry_id"

DEFAULT_NAME = "Automatyzacja raportów sza86"
DEFAULT_CSV_DIRECTORY = "/config/auto_reports"
DEFAULT_RETENTION_MONTHS = 36
DEFAULT_DAILY_TIME = "00:05:00"
DEFAULT_WEEKLY_TIME = "00:10:00"
DEFAULT_MONTHLY_TIME = "00:15:00"
DEFAULT_YEARLY_TIME = "00:20:00"
DEFAULT_SCAN_INTERVAL_MINUTES = 10

PERIOD_DAY = "day"
PERIOD_WEEK = "week"
PERIOD_MONTH = "month"
PERIOD_YEAR = "year"
PERIODS = [PERIOD_DAY, PERIOD_WEEK, PERIOD_MONTH, PERIOD_YEAR]

STATUS_OK = "OK"
STATUS_WARNING = "Uwaga"
STATUS_PROBLEM = "Problem"

ROLE_CONSUMPTION = "zuzycie"
ROLE_PRODUCTION = "produkcja"
ROLE_IMPORT = "import"
ROLE_EXPORT = "eksport"
ROLE_INFORMATIONAL = "informacyjne"
ROLES = [
    ROLE_CONSUMPTION,
    ROLE_PRODUCTION,
    ROLE_IMPORT,
    ROLE_EXPORT,
    ROLE_INFORMATIONAL,
]

MEDIUM_ENERGY = "energia"
MEDIUM_WATER = "woda"
MEDIUM_GAS = "gaz"
MEDIUM_OTHER = "inne"
MEDIA = [MEDIUM_ENERGY, MEDIUM_WATER, MEDIUM_GAS, MEDIUM_OTHER]

STORAGE_VERSION = 1
SERVICE_GENERATE_REPORT = "generate_report"
SERVICE_RESET_SNAPSHOTS = "reset_snapshots"
SERVICE_RESET_SOURCE_HISTORY = "reset_source_history"

ENTITY_KEYS = {
    PERIOD_DAY: "daily_report",
    PERIOD_WEEK: "weekly_report",
    PERIOD_MONTH: "monthly_report",
    PERIOD_YEAR: "yearly_report",
    "status": "status",
    "database_overview": "database_overview",
}

DEFAULT_OPTIONS = {
    CONF_CSV_DIRECTORY: DEFAULT_CSV_DIRECTORY,
    CONF_RETENTION_MONTHS: DEFAULT_RETENTION_MONTHS,
    CONF_DAILY_TIME: DEFAULT_DAILY_TIME,
    CONF_WEEKLY_TIME: DEFAULT_WEEKLY_TIME,
    CONF_MONTHLY_TIME: DEFAULT_MONTHLY_TIME,
    CONF_YEARLY_TIME: DEFAULT_YEARLY_TIME,
    CONF_ENABLE_DAILY: True,
    CONF_ENABLE_WEEKLY: True,
    CONF_ENABLE_MONTHLY: True,
    CONF_ENABLE_YEARLY: True,
    CONF_SCAN_INTERVAL_MINUTES: DEFAULT_SCAN_INTERVAL_MINUTES,
    CONF_SOURCES: [],
    CONF_NOTIFY_TARGETS: [],
}

PERIOD_LABELS_PL = {
    PERIOD_DAY: "dzienny",
    PERIOD_WEEK: "tygodniowy",
    PERIOD_MONTH: "miesięczny",
    PERIOD_YEAR: "roczny",
}
