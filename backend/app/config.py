"""Central configuration.

Everything can be overridden with environment variables, but the defaults are
set for the challenge: national wind generation for January 2026.
"""
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Where the data snapshot (CSV files) lives.
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))

# Elexon BMRS "Insights Solution" open-data API (no API key needed).
ELEXON_BASE_URL = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")

# Target-time window we analyse: [DATA_START, DATA_END). Half-open on purpose.
DATA_START = datetime.fromisoformat(os.getenv("DATA_START", "2026-01-01T00:00:00+00:00"))
DATA_END = datetime.fromisoformat(os.getenv("DATA_END", "2026-02-01T00:00:00+00:00"))

# The longest forecast lead time (hours) a user can select in the UI.
MAX_HORIZON_HOURS = int(os.getenv("MAX_HORIZON_HOURS", "48"))

# Forecasts older than this (hours before the target time) are discarded when loading.
# It is larger than MAX_HORIZON_HOURS on purpose: to answer "what was the latest forecast
# published at least 48h ahead?" we need forecasts that are somewhat older than 48h.
FORECAST_RETENTION_HOURS = int(os.getenv("FORECAST_RETENTION_HOURS", str(MAX_HORIZON_HOURS + 24)))

# The day-ahead market is a GB market, so "yesterday at 09:00" means UK local time.
LOCAL_TZ = os.getenv("LOCAL_TZ", "Europe/London")

# Comma separated list of allowed browser origins ("*" = any).
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
