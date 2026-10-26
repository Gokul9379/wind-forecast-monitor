"""Create SYNTHETIC wind data with the same shape as the real Elexon data.

Only for running the app without internet access. The app shows a banner
whenever it is using this data, so it can never be mistaken for the real thing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CAPACITY_MW = 21000


def generate(seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    times = pd.date_range("2025-12-28", "2026-02-04", freq="30min", tz="UTC", inclusive="left")

    # "Actual" wind: a slowly wandering (AR(1)) signal scaled to a plausible GB range.
    x = np.zeros(len(times))
    for i in range(1, len(x)):
        x[i] = 0.995 * x[i - 1] + rng.normal(0, 0.08)
    actual = np.clip(8500 + 6500 * x / x.std(), 300, CAPACITY_MW - 1500)
    truth = pd.Series(actual, index=times)

    # Forecasts: one run every 3 hours, each covering the next 72h, with an error
    # that is smooth in time and grows with the lead time.
    rows = []
    publish_times = pd.date_range("2025-12-27", "2026-02-01", freq="3h", tz="UTC", inclusive="left")
    for published in publish_times:
        targets = pd.date_range(published, published + pd.Timedelta(hours=72), freq="30min", tz="UTC")
        z = np.zeros(len(targets))
        z[0] = rng.normal()
        for i in range(1, len(z)):
            z[i] = 0.92 * z[i - 1] + np.sqrt(1 - 0.92 ** 2) * rng.normal()
        lead_hours = np.arange(len(targets)) * 0.5
        sigma = 500 + 60 * lead_hours
        forecast = np.clip(truth.reindex(targets).to_numpy() + sigma * z, 0, CAPACITY_MW)
        rows.append(pd.DataFrame({"startTime": targets, "publishTime": published, "forecast_mw": forecast}))
    forecasts = pd.concat(rows, ignore_index=True)

    jan = (times >= "2026-01-01") & (times < "2026-02-01")
    actuals = pd.DataFrame({"startTime": times[jan], "actual_mw": actual[jan]})
    forecasts = forecasts[(forecasts["startTime"] >= "2026-01-01") & (forecasts["startTime"] < "2026-02-01")]
    meta = {
        "source": "synthetic",
        "description": "Randomly generated demo data - NOT real Elexon data.",
        "actual_rows": int(len(actuals)),
        "forecast_rows": int(len(forecasts)),
    }
    actuals = actuals.assign(actual_mw=actuals["actual_mw"].round(1))
    forecasts = forecasts.assign(forecast_mw=forecasts["forecast_mw"].round(1))
    return actuals, forecasts, meta
