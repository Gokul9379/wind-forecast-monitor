"""Thin client for the two Elexon (BMRS) datasets we need.

* FUELHH  - actual generation per fuel type, 30 minute resolution
* WINDFOR - wind generation forecasts, each tagged with a ``publishTime``

The parse_* functions are separate from the HTTP code so they can be unit
tested without internet access.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Iterator

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config

log = logging.getLogger(__name__)


# ----------------------------------------------------------------- parsing
def parse_actuals(rows: list[dict]) -> pd.DataFrame:
    """FUELHH rows -> DataFrame[startTime, actual_mw] for WIND only."""
    columns = ["startTime", "actual_mw"]
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    if "fuelType" in df.columns:  # the API filter should do this, but be safe
        df = df[df["fuelType"] == "WIND"]
    if "publishTime" in df.columns:  # keep the latest revision of each period
        df = df.assign(publishTime=pd.to_datetime(df["publishTime"], utc=True))
        df = df.sort_values("publishTime")
    df = df.assign(
        startTime=pd.to_datetime(df["startTime"], utc=True),
        actual_mw=pd.to_numeric(df["generation"], errors="coerce"),
    )
    df = df.drop_duplicates("startTime", keep="last")
    return df[columns].sort_values("startTime").reset_index(drop=True)


def parse_forecasts(rows: list[dict]) -> pd.DataFrame:
    """WINDFOR rows -> DataFrame[startTime, publishTime, forecast_mw]."""
    columns = ["startTime", "publishTime", "forecast_mw"]
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    df = df.assign(
        startTime=pd.to_datetime(df["startTime"], utc=True),
        publishTime=pd.to_datetime(df["publishTime"], utc=True),
        forecast_mw=pd.to_numeric(df["generation"], errors="coerce"),
    )
    df = df.drop_duplicates(["startTime", "publishTime"], keep="last")
    return df[columns].sort_values(["publishTime", "startTime"]).reset_index(drop=True)


# ----------------------------------------------------------------- chunking
def date_chunks(start: date, end: date, days: int) -> Iterator[tuple[date, date]]:
    """Split the inclusive date range [start, end] into inclusive chunks."""
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=days - 1), end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def time_chunks(start: datetime, end: datetime, step: timedelta) -> Iterator[tuple[datetime, datetime]]:
    """Split [start, end) into consecutive windows of length ``step``."""
    current = start
    while current < end:
        yield current, min(current + step, end)
        current += step


# ----------------------------------------------------------------- HTTP
class ElexonClient:
    def __init__(self, base_url: str = config.ELEXON_BASE_URL, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

    def _get_json(self, path: str, params: dict) -> list[dict]:
        url = f"{self.base_url}{path}"
        response = self.session.get(
            url, params=params, timeout=self.timeout, headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):  # non-stream endpoints wrap rows in {"data": [...]}
            payload = payload.get("data", [])
        return payload

    def fetch_wind_actuals(self, first_day: date, last_day: date) -> pd.DataFrame:
        """Actual wind generation for settlement dates first_day..last_day (inclusive)."""
        rows: list[dict] = []
        for chunk_start, chunk_end in date_chunks(first_day, last_day, days=7):
            log.info("FUELHH %s -> %s", chunk_start, chunk_end)
            rows += self._get_json(
                "/datasets/FUELHH/stream",
                {
                    "settlementDateFrom": chunk_start.isoformat(),
                    "settlementDateTo": chunk_end.isoformat(),
                    "fuelType": "WIND",
                    "format": "json",
                },
            )
        return parse_actuals(rows)

    def fetch_wind_forecasts(self, publish_from: datetime, publish_to: datetime) -> pd.DataFrame:
        """All WINDFOR forecasts published in [publish_from, publish_to)."""
        rows: list[dict] = []
        for chunk_start, chunk_end in time_chunks(publish_from, publish_to, timedelta(days=1)):
            log.info("WINDFOR published %s -> %s", chunk_start, chunk_end)
            rows += self._get_json(
                "/datasets/WINDFOR/stream",
                {
                    "publishDateTimeFrom": chunk_start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "publishDateTimeTo": chunk_end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "format": "json",
                },
            )
        return parse_forecasts(rows)
