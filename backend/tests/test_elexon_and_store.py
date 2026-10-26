from datetime import date, datetime, timedelta, timezone

import pandas as pd

from app import analytics
from app.data_store import DataNotAvailable, load_snapshot, save_snapshot
from app.elexon_client import date_chunks, parse_actuals, parse_forecasts, time_chunks
from scripts.generate_demo_data import generate


def test_parse_actuals_keeps_only_wind_and_latest_revision():
    rows = [
        {"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-01T00:05:00Z", "generation": 100},
        {"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-01T01:05:00Z", "generation": 110},
        {"fuelType": "CCGT", "startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-01T00:05:00Z", "generation": 9999},
        {"fuelType": "WIND", "startTime": "2026-01-01T00:30:00Z", "publishTime": "2026-01-01T00:35:00Z", "generation": 120},
    ]
    df = parse_actuals(rows)
    assert list(df["actual_mw"]) == [110, 120]
    assert str(df["startTime"].dt.tz) == "UTC"


def test_parse_forecasts_dedupes_and_renames():
    rows = [
        {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-01T06:00:00Z", "generation": 5.0},
        {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-01T06:00:00Z", "generation": 5.0},
        {"startTime": "2026-01-02T00:30:00Z", "publishTime": "2026-01-01T06:00:00Z", "generation": "7.5"},
    ]
    df = parse_forecasts(rows)
    assert len(df) == 2 and list(df["forecast_mw"]) == [5.0, 7.5]


def test_parsers_handle_empty_input():
    assert parse_actuals([]).empty and parse_forecasts([]).empty


def test_chunking_covers_range_without_gaps():
    chunks = list(date_chunks(date(2026, 1, 1), date(2026, 1, 31), days=7))
    assert chunks[0] == (date(2026, 1, 1), date(2026, 1, 7))
    assert chunks[-1][1] == date(2026, 1, 31)
    for (_, prev_end), (next_start, _) in zip(chunks, chunks[1:]):
        assert next_start == prev_end + timedelta(days=1)

    start = datetime(2025, 12, 29, tzinfo=timezone.utc)
    end = datetime(2026, 2, 1, tzinfo=timezone.utc)
    windows = list(time_chunks(start, end, timedelta(days=1)))
    assert windows[0][0] == start and windows[-1][1] == end and len(windows) == 34


def test_snapshot_round_trip(tmp_path):
    actuals, forecasts, meta = generate()
    save_snapshot(tmp_path, actuals, forecasts, meta)
    store = load_snapshot(tmp_path)
    assert store.meta["source"] == "synthetic"
    assert len(store.actuals) == len(actuals)
    assert str(store.forecasts["publishTime"].dt.tz) == "UTC"
    age = store.forecasts["startTime"] - store.forecasts["publishTime"]
    assert age.min() >= pd.Timedelta(0) and age.max() <= pd.Timedelta(hours=72)


def test_missing_snapshot_gives_helpful_error(tmp_path):
    try:
        load_snapshot(tmp_path)
    except DataNotAvailable as exc:
        assert "fetch_data" in str(exc)
        return
    raise AssertionError("expected DataNotAvailable")
