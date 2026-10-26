"""Loads / saves the data snapshot (two gzipped CSV files + a small JSON file).

Why a snapshot instead of calling Elexon on every request?
  * the question only concerns January 2026, i.e. historical, unchanging data
  * the app starts instantly and keeps working if Elexon is slow or down
  * it deploys cleanly to serverless hosting such as Vercel
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import config
from .analytics import to_utc_ns

ACTUALS_FILE = "actuals.csv.gz"
FORECASTS_FILE = "forecasts.csv.gz"
META_FILE = "meta.json"


class DataNotAvailable(RuntimeError):
    """Raised when the snapshot has not been created yet."""


@dataclass
class DataStore:
    actuals: pd.DataFrame     # startTime, actual_mw
    forecasts: pd.DataFrame   # startTime, publishTime, forecast_mw
    meta: dict


def snapshot_exists(data_dir: Path = config.DATA_DIR) -> bool:
    return all((Path(data_dir) / name).exists() for name in (ACTUALS_FILE, FORECASTS_FILE, META_FILE))


def save_snapshot(data_dir: Path, actuals: pd.DataFrame, forecasts: pd.DataFrame, meta: dict) -> None:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    actuals.to_csv(data_dir / ACTUALS_FILE, index=False)
    forecasts.to_csv(data_dir / FORECASTS_FILE, index=False)
    meta = {**meta, "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    (data_dir / META_FILE).write_text(json.dumps(meta, indent=2))


def load_snapshot(data_dir: Path = config.DATA_DIR) -> DataStore:
    data_dir = Path(data_dir)
    if not snapshot_exists(data_dir):
        raise DataNotAvailable(
            "No data snapshot found. Build one with `python -m scripts.fetch_data` "
            "(real Elexon data) or `python -m scripts.fetch_data --demo` (synthetic data)."
        )
    actuals = pd.read_csv(data_dir / ACTUALS_FILE)
    forecasts = pd.read_csv(data_dir / FORECASTS_FILE)
    actuals["startTime"] = to_utc_ns(actuals["startTime"])
    forecasts["startTime"] = to_utc_ns(forecasts["startTime"])
    forecasts["publishTime"] = to_utc_ns(forecasts["publishTime"])

    # Only keep genuine forecasts: published before the target time and not absurdly old.
    age = forecasts["startTime"] - forecasts["publishTime"]
    keep = (age >= pd.Timedelta(0)) & (age <= pd.Timedelta(hours=config.FORECAST_RETENTION_HOURS))
    forecasts = forecasts[keep].drop_duplicates(["startTime", "publishTime"], keep="last")

    meta = json.loads((data_dir / META_FILE).read_text())
    return DataStore(
        actuals=actuals.sort_values("startTime").reset_index(drop=True),
        forecasts=forecasts.sort_values("publishTime").reset_index(drop=True),
        meta=meta,
    )


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    """Load once per process; later requests reuse the same in-memory data."""
    return load_snapshot()
