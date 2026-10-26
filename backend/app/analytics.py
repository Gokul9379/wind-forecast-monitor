
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config

HALF_HOUR = pd.Timedelta(minutes=30)
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
QUANTILE_LEVELS = {
    "p01": 0.01, "p05": 0.05, "p10": 0.10, "p25": 0.25, "p50": 0.50,
    "p75": 0.75, "p90": 0.90, "p95": 0.95, "p99": 0.99,
}


# ------------------------------------------------------------ time helpers
def to_utc_ns(values):
    """Convert a Series / Index of datetimes to tz-aware UTC with ns resolution.

    pandas 2 and pandas 3 pick different default resolutions; forcing one
    avoids merge errors caused by mismatched dtypes.
    """
    return pd.to_datetime(values, utc=True).astype("datetime64[ns, UTC]")


def as_utc_timestamp(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def build_target_grid(start, end) -> pd.Series:
    """Every half hour in [start, end) as a UTC Series named startTime."""
    start, end = as_utc_timestamp(start), as_utc_timestamp(end)
    index = pd.date_range(start.ceil("30min"), end, freq="30min", inclusive="left")
    return pd.Series(to_utc_ns(index), name="startTime")


# ------------------------------------------------------- forecast selection
def attach_forecasts(frame: pd.DataFrame, forecasts: pd.DataFrame, cutoffs: pd.Series) -> pd.DataFrame:
    """Add ``publishTime`` and ``forecast_mw`` columns to ``frame``.

    For every row, pick the most recent forecast for the same startTime that was
    published at or before that row's cut-off. Rows with no such forecast get
    NaN / NaT (they show up as gaps in the chart and are skipped in metrics).
    """
    frame = frame.reset_index(drop=True)
    left = frame[["startTime"]].copy()
    left["cutoff"] = cutoffs.reset_index(drop=True)
    left["_key"] = left["startTime"].astype("int64")
    left = left[left["cutoff"].notna()].sort_values("cutoff")

    right = forecasts[["startTime", "publishTime", "forecast_mw"]].copy()
    right["_key"] = right["startTime"].astype("int64")
    right = right.drop(columns="startTime").sort_values("publishTime")

    matched = pd.merge_asof(
        left, right, left_on="cutoff", right_on="publishTime", by="_key", direction="backward"
    )[["startTime", "publishTime", "forecast_mw"]]
    return frame.merge(matched, on="startTime", how="left")


def _with_actuals(grid: pd.Series, actuals: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"startTime": grid}).merge(actuals, on="startTime", how="left")


def _add_error_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["error_mw"] = frame["actual_mw"] - frame["forecast_mw"]
    age = frame["startTime"] - frame["publishTime"]
    frame["forecast_horizon_hours"] = age.dt.total_seconds() / 3600
    return frame


def build_horizon_frame(actuals, forecasts, start, end, horizon_hours: float) -> pd.DataFrame:
    """Actual vs forecast for every half hour in [start, end), at a fixed lead time."""
    frame = _with_actuals(build_target_grid(start, end), actuals)
    cutoffs = frame["startTime"] - pd.Timedelta(hours=float(horizon_hours))
    return _add_error_columns(attach_forecasts(frame, forecasts, cutoffs))


def day_ahead_cutoffs(start_times: pd.Series, hour: int, minute: int, tz: str = config.LOCAL_TZ) -> pd.Series:
    """For each target time: 'HH:MM on the previous local calendar day', in UTC."""
    local_naive = start_times.dt.tz_convert(tz).dt.tz_localize(None)
    cutoff_naive = local_naive.dt.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=hour, minutes=minute)
    cutoff = cutoff_naive.dt.tz_localize(tz, ambiguous="NaT", nonexistent="NaT")
    return cutoff.dt.tz_convert("UTC").astype("datetime64[ns, UTC]")


# ------------------------------------------------------------------ metrics
def _round(value, digits: int = 2):
    return None if value is None or pd.isna(value) else round(float(value), digits)


def compute_metrics(frame: pd.DataFrame) -> dict:
    """Accuracy statistics over rows that have BOTH an actual and a forecast."""
    valid = frame.dropna(subset=["actual_mw", "forecast_mw"])
    n = int(len(valid))
    empty = {
        "n_points": 0, "mean_actual_mw": None, "mean_forecast_mw": None, "bias_mw": None,
        "mae_mw": None, "rmse_mw": None, "nmae_pct": None, "median_abs_error_mw": None,
        "p90_abs_error_mw": None, "p99_abs_error_mw": None, "shortfall_share_pct": None,
        "mean_shortfall_mw": None, "p95_shortfall_mw": None, "error_quantiles": {},
        "mean_forecast_age_hours": None,
    }
    if n == 0:
        return empty

    err = valid["actual_mw"] - valid["forecast_mw"]
    abs_err = err.abs()
    mean_actual = valid["actual_mw"].mean()
    quantiles = err.quantile(list(QUANTILE_LEVELS.values()))
    shortfalls = (-err[err < 0])

    return {
        "n_points": n,
        "mean_actual_mw": _round(mean_actual),
        "mean_forecast_mw": _round(valid["forecast_mw"].mean()),
        "bias_mw": _round(err.mean()),
        "mae_mw": _round(abs_err.mean()),
        "rmse_mw": _round(np.sqrt((err ** 2).mean())),
        "nmae_pct": _round(abs_err.mean() / mean_actual * 100) if mean_actual > 0 else None,
        "median_abs_error_mw": _round(abs_err.median()),
        "p90_abs_error_mw": _round(abs_err.quantile(0.90)),
        "p99_abs_error_mw": _round(abs_err.quantile(0.99)),
        "shortfall_share_pct": _round((err < 0).mean() * 100, 1),
        "mean_shortfall_mw": _round(shortfalls.mean()) if len(shortfalls) else 0.0,
        "p95_shortfall_mw": _round(max(0.0, -quantiles.loc[0.05])),
        "error_quantiles": {name: _round(quantiles.loc[level]) for name, level in QUANTILE_LEVELS.items()},
        "mean_forecast_age_hours": _round(valid["forecast_horizon_hours"].mean())
        if "forecast_horizon_hours" in valid else None,
    }


def error_histogram(frame: pd.DataFrame, bins: int = 30) -> list[dict]:
    err = frame["error_mw"].dropna()
    if err.empty:
        return []
    limit = float(max(abs(err.min()), abs(err.max()), 1.0))  # symmetric around 0
    counts, edges = np.histogram(err, bins=bins, range=(-limit, limit))
    return [
        {"bin_start": round(float(edges[i]), 1), "bin_end": round(float(edges[i + 1]), 1), "count": int(counts[i])}
        for i in range(len(counts))
    ]


def horizon_profile(actuals, forecasts, start, end, min_h: float = 0, max_h: float = 48, step: float = 1) -> list[dict]:
    """Accuracy as a function of forecast lead time (the 'error by horizon' curve)."""
    base = _with_actuals(build_target_grid(start, end), actuals)
    rows = []
    for h in np.arange(min_h, max_h + 1e-9, step):
        cutoffs = base["startTime"] - pd.Timedelta(hours=float(h))
        frame = _add_error_columns(attach_forecasts(base, forecasts, cutoffs))
        m = compute_metrics(frame)
        rows.append({
            "horizon_hours": float(h), "n_points": m["n_points"], "mae_mw": m["mae_mw"],
            "rmse_mw": m["rmse_mw"], "bias_mw": m["bias_mw"], "p95_shortfall_mw": m["p95_shortfall_mw"],
        })
    return rows


# ---------------------------------------------------------------- serialising
def frame_to_records(df: pd.DataFrame, time_cols=(), digits: int = 1) -> list[dict]:
    """DataFrame -> list of JSON-safe dicts (NaN/NaT become None, times become ISO strings)."""
    out = df.copy()
    for col in time_cols:
        out[col] = out[col].dt.strftime(TS_FORMAT)
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].round(digits)
    out = out.astype(object)
    out = out.where(out.notna(), None)
    return out.to_dict(orient="records")


def _ts(value) -> str | None:
    return None if pd.isna(value) else value.strftime(TS_FORMAT)


# -------------------------------------------------------------- API-level views
def analysis(actuals, forecasts, start, end, horizon_hours: float) -> dict:
    frame = build_horizon_frame(actuals, forecasts, start, end, horizon_hours)
    points = frame.rename(columns={"startTime": "time", "publishTime": "publish_time"})
    return {
        "horizon_hours": float(horizon_hours),
        "points": frame_to_records(points, time_cols=("time", "publish_time")),
        "metrics": compute_metrics(frame),
        "histogram": error_histogram(frame),
    }


def export_frame(actuals, forecasts, start, end, horizon_hours: float) -> pd.DataFrame:
    frame = build_horizon_frame(actuals, forecasts, start, end, horizon_hours)
    frame = frame.rename(columns={"startTime": "target_time_utc", "publishTime": "forecast_publish_time_utc"})
    for col in ("target_time_utc", "forecast_publish_time_utc"):
        frame[col] = frame[col].dt.strftime(TS_FORMAT)
    columns = ["target_time_utc", "actual_mw", "forecast_mw", "error_mw",
               "forecast_publish_time_utc", "forecast_horizon_hours"]
    return frame[columns].round({"actual_mw": 1, "forecast_mw": 1, "error_mw": 1, "forecast_horizon_hours": 2})


def day_ahead(
    actuals, forecasts, delivery_date: date, cutoff_hour: int, cutoff_minute: int,
    window_start, window_end, confidence: float = 0.90, tz: str = config.LOCAL_TZ,
) -> dict:
    """What did the forecast say when the day-ahead decision had to be made?

    * Uses the latest forecast published before the cut-off on the day before.
    * Backtests the same rule on the OTHER days of the window to measure the
      typical error, then turns that into a conservative / optimistic range:
      'with `confidence` probability, wind will be at least the conservative value'.
    """
    day_start = pd.Timestamp(delivery_date, tz=tz).tz_convert("UTC")
    day_end = pd.Timestamp(delivery_date + timedelta(days=1), tz=tz).tz_convert("UTC")

    base = _with_actuals(build_target_grid(window_start, window_end), actuals)
    cutoffs = day_ahead_cutoffs(base["startTime"], cutoff_hour, cutoff_minute, tz)
    full = attach_forecasts(base, forecasts, cutoffs)
    full["cutoff"] = cutoffs.reset_index(drop=True)
    full = _add_error_columns(full)

    in_day = (full["startTime"] >= day_start) & (full["startTime"] < day_end)
    day = full[in_day].copy()
    if day.empty:
        raise ValueError("The delivery day is outside the data window.")
    backtest = full[~in_day]

    err = backtest["error_mw"].dropna()
    low_q = high_q = None
    if len(err):
        low_q = float(err.quantile(1 - confidence))   # typically negative
        high_q = float(err.quantile(confidence))      # typically positive
        day["conservative_mw"] = (day["forecast_mw"] + low_q).clip(lower=0)
        day["optimistic_mw"] = day["forecast_mw"] + high_q
    else:
        day["conservative_mw"] = np.nan
        day["optimistic_mw"] = np.nan

    def energy(series):
        """Energy over the whole delivery day in MWh.

        If some half-hours have no value (e.g. the forecast is only published hourly),
        we use the average of the available values times the full day length, so that
        forecast and actual totals are always comparable. With full coverage this is
        exactly sum(MW) x 0.5 h.
        """
        if not series.notna().any():
            return None
        return _round(series.mean() * len(series) * 0.5, 0)

    published = day["publishTime"].dropna()
    backtest_metrics = compute_metrics(backtest)
    summary = {
        "delivery_date": delivery_date.isoformat(),
        "decision_cutoff_utc": _ts(day["cutoff"].iloc[0]),
        "forecast_publish_min": _ts(published.min()) if len(published) else None,
        "forecast_publish_max": _ts(published.max()) if len(published) else None,
        "n_periods": int(len(day)),
        "n_with_forecast": int(day["forecast_mw"].notna().sum()),
        "n_with_actual": int(day["actual_mw"].notna().sum()),
        "forecast_energy_mwh": energy(day["forecast_mw"]),
        "conservative_energy_mwh": energy(day["conservative_mw"]),
        "optimistic_energy_mwh": energy(day["optimistic_mw"]),
        "actual_energy_mwh": energy(day["actual_mw"]),
        "confidence": confidence,
        "conservative_offset_mw": _round(low_q),
        "optimistic_offset_mw": _round(high_q),
        "backtest_points": int(len(err)),
        "backtest_mae_mw": backtest_metrics["mae_mw"],
        "backtest_rmse_mw": backtest_metrics["rmse_mw"],
        "backtest_bias_mw": backtest_metrics["bias_mw"],
        "day_metrics": compute_metrics(day),
    }
    points = day[["startTime", "actual_mw", "forecast_mw", "publishTime", "forecast_horizon_hours",
                  "conservative_mw", "optimistic_mw"]].rename(
        columns={"startTime": "time", "publishTime": "publish_time"})
    return {"summary": summary, "points": frame_to_records(points, time_cols=("time", "publish_time"))}
