import json
from datetime import date

import numpy as np
import pandas as pd

from app import analytics
from scripts.generate_demo_data import generate


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def make_forecasts():
    # four forecasts, published at different times, all for the target 2026-01-02 12:00
    target = ts("2026-01-02 12:00")
    rows = [
        (target, ts("2026-01-01 06:00"), 100.0),
        (target, ts("2026-01-01 12:00"), 200.0),
        (target, ts("2026-01-02 06:00"), 300.0),
        (target, ts("2026-01-02 11:00"), 400.0),
    ]
    df = pd.DataFrame(rows, columns=["startTime", "publishTime", "forecast_mw"])
    df["startTime"] = analytics.to_utc_ns(df["startTime"])
    df["publishTime"] = analytics.to_utc_ns(df["publishTime"])
    return df


def make_actuals():
    df = pd.DataFrame({"startTime": [ts("2026-01-02 12:00")], "actual_mw": [250.0]})
    df["startTime"] = analytics.to_utc_ns(df["startTime"])
    return df


def pick(horizon):
    frame = analytics.build_horizon_frame(
        make_actuals(), make_forecasts(), ts("2026-01-02 12:00"), ts("2026-01-02 12:30"), horizon
    )
    assert len(frame) == 1
    return frame.iloc[0]


def test_latest_forecast_before_cutoff_is_chosen():
    assert pick(0)["forecast_mw"] == 400.0      # newest forecast
    assert pick(6)["forecast_mw"] == 300.0      # cut-off 06:00 -> boundary is inclusive
    assert pick(24)["forecast_mw"] == 200.0
    assert pick(30)["forecast_mw"] == 100.0


def test_no_forecast_old_enough_gives_gap_not_error():
    row = pick(48)
    assert pd.isna(row["forecast_mw"]) and pd.isna(row["publishTime"])


def test_forecast_age_is_reported():
    assert pick(24)["forecast_horizon_hours"] == 24.0


def test_metrics_values():
    frame = pd.DataFrame({"actual_mw": [100.0, 200.0, 300.0], "forecast_mw": [110.0, 180.0, 330.0]})
    frame["error_mw"] = frame["actual_mw"] - frame["forecast_mw"]  # -10, +20, -30
    m = analytics.compute_metrics(frame)
    assert m["n_points"] == 3
    assert m["mae_mw"] == 20.0
    assert m["bias_mw"] == round(-20 / 3, 2)
    assert m["rmse_mw"] == round(float(np.sqrt(1400 / 3)), 2)
    assert m["shortfall_share_pct"] == 66.7
    assert m["nmae_pct"] == 10.0


def test_metrics_ignore_missing_values_and_handle_empty():
    frame = pd.DataFrame({"actual_mw": [100.0, np.nan], "forecast_mw": [90.0, 50.0]})
    assert analytics.compute_metrics(frame)["n_points"] == 1
    assert analytics.compute_metrics(frame.iloc[0:0])["n_points"] == 0


def test_day_ahead_cutoff_winter_and_summer():
    winter = pd.Series(analytics.to_utc_ns(["2026-01-05 12:00"]))
    summer = pd.Series(analytics.to_utc_ns(["2026-07-05 12:00"]))
    assert analytics.day_ahead_cutoffs(winter, 9, 0).iloc[0] == ts("2026-01-04 09:00")
    # UK summer time is UTC+1, so 09:00 local is 08:00 UTC
    assert analytics.day_ahead_cutoffs(summer, 9, 0).iloc[0] == ts("2026-07-04 08:00")


def demo_store():
    actuals, forecasts, _ = generate()
    actuals["startTime"] = analytics.to_utc_ns(actuals["startTime"])
    forecasts["startTime"] = analytics.to_utc_ns(forecasts["startTime"])
    forecasts["publishTime"] = analytics.to_utc_ns(forecasts["publishTime"])
    return actuals, forecasts


START, END = ts("2026-01-01"), ts("2026-02-01")


def test_error_grows_with_horizon():
    actuals, forecasts = demo_store()
    rows = analytics.horizon_profile(actuals, forecasts, START, END, 0, 48, 12)
    maes = [r["mae_mw"] for r in rows]
    assert maes == sorted(maes), maes  # 0h < 12h < 24h < 36h < 48h
    assert all(r["n_points"] > 1000 for r in rows)


def test_analysis_output_is_json_safe():
    actuals, forecasts = demo_store()
    result = analytics.analysis(actuals, forecasts, ts("2026-01-01"), ts("2026-01-08"), 24)
    assert len(result["points"]) == 7 * 48
    json.dumps(result, allow_nan=False)  # raises if NaN / NaT slipped through
    assert result["metrics"]["n_points"] > 0
    assert sum(b["count"] for b in result["histogram"]) == result["metrics"]["n_points"]


def test_day_ahead_view():
    actuals, forecasts = demo_store()
    result = analytics.day_ahead(actuals, forecasts, date(2026, 1, 10), 9, 0, START, END, 0.9)
    s, pts = result["summary"], result["points"]
    assert len(pts) == 48 and s["n_with_forecast"] == 48
    assert s["decision_cutoff_utc"] == "2026-01-09T09:00:00Z"
    assert s["forecast_publish_max"] <= s["decision_cutoff_utc"]   # no peeking at the future
    assert s["conservative_offset_mw"] < 0 < s["optimistic_offset_mw"]
    assert all(p["conservative_mw"] <= p["forecast_mw"] <= p["optimistic_mw"] for p in pts)
    assert s["backtest_points"] > 1000
    json.dumps(result, allow_nan=False)


def test_day_ahead_outside_window_raises():
    actuals, forecasts = demo_store()
    try:
        analytics.day_ahead(actuals, forecasts, date(2026, 3, 1), 9, 0, START, END)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_export_frame_columns():
    actuals, forecasts = demo_store()
    df = analytics.export_frame(actuals, forecasts, ts("2026-01-01"), ts("2026-01-02"), 12)
    assert list(df.columns) == ["target_time_utc", "actual_mw", "forecast_mw", "error_mw",
                                "forecast_publish_time_utc", "forecast_horizon_hours"]
    assert len(df) == 48


def test_energy_is_comparable_when_forecasts_are_only_hourly():
    actuals, forecasts = demo_store()
    full = analytics.day_ahead(actuals, forecasts, date(2026, 1, 10), 9, 0, START, END, 0.9)["summary"]
    hourly_only = forecasts[forecasts["startTime"].dt.minute == 0]
    half = analytics.day_ahead(actuals, hourly_only, date(2026, 1, 10), 9, 0, START, END, 0.9)["summary"]
    assert half["n_with_forecast"] == 24 and half["n_periods"] == 48
    # without the coverage correction this ratio would be about 0.5
    assert 0.9 < half["forecast_energy_mwh"] / full["forecast_energy_mwh"] < 1.1
