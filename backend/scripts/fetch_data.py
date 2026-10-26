"""Build the data snapshot used by the API.

Usage (run from the backend/ folder):
    python -m scripts.fetch_data               # download real data from Elexon
    python -m scripts.fetch_data --demo        # synthetic data, no internet needed
    python -m scripts.fetch_data --if-missing  # do nothing if a snapshot exists (used by Docker)
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import timedelta, timezone
from pathlib import Path

import pandas as pd

from app import config
from app.analytics import to_utc_ns
from app.data_store import save_snapshot, snapshot_exists
from app.elexon_client import ElexonClient

log = logging.getLogger("fetch_data")


def fetch_real(data_dir: Path) -> None:
    start = config.DATA_START.astimezone(timezone.utc)
    end = config.DATA_END.astimezone(timezone.utc)
    client = ElexonClient()

    actuals = client.fetch_wind_actuals(start.date(), (end - timedelta(seconds=1)).date())
    actuals = actuals[(actuals["startTime"] >= pd.Timestamp(start)) & (actuals["startTime"] < pd.Timestamp(end))]

    # A forecast for the first target time may have been published up to FORECAST_RETENTION_HOURS earlier.
    publish_from = start - timedelta(hours=config.FORECAST_RETENTION_HOURS)
    forecasts = client.fetch_wind_forecasts(publish_from, end)
    forecasts["startTime"] = to_utc_ns(forecasts["startTime"])
    forecasts["publishTime"] = to_utc_ns(forecasts["publishTime"])
    forecasts = forecasts[(forecasts["startTime"] >= pd.Timestamp(start)) & (forecasts["startTime"] < pd.Timestamp(end))]
    age = forecasts["startTime"] - forecasts["publishTime"]
    forecasts = forecasts[(age >= pd.Timedelta(0)) & (age <= pd.Timedelta(hours=config.FORECAST_RETENTION_HOURS))]

    if actuals.empty or forecasts.empty:
        raise RuntimeError("Elexon returned no data for the requested window - check the dates / API.")

    meta = {
        "source": "elexon",
        "description": "Elexon BMRS datasets FUELHH (fuelType=WIND) and WINDFOR.",
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "max_horizon_hours": config.MAX_HORIZON_HOURS,
        "forecast_retention_hours": config.FORECAST_RETENTION_HOURS,
        "actual_rows": int(len(actuals)),
        "forecast_rows": int(len(forecasts)),
    }
    save_snapshot(data_dir, actuals, forecasts, meta)


def fetch_demo(data_dir: Path) -> None:
    from scripts.generate_demo_data import generate

    actuals, forecasts, meta = generate()
    save_snapshot(data_dir, actuals, forecasts, meta)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo", action="store_true", help="generate synthetic data instead of calling Elexon")
    parser.add_argument("--if-missing", action="store_true", help="skip if a snapshot already exists")
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.if_missing and snapshot_exists(args.data_dir):
        log.info("Snapshot already present in %s - nothing to do.", args.data_dir)
        return 0
    try:
        (fetch_demo if args.demo else fetch_real)(args.data_dir)
    except Exception as exc:  # noqa: BLE001
        log.error("Could not build the snapshot: %s", exc)
        # With --if-missing (Docker start-up) we still let the server boot; the API
        # will answer 503 with instructions instead of crashing the container.
        return 0 if args.if_missing else 1
    log.info("Snapshot written to %s", args.data_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
