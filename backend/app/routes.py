"""HTTP endpoints. Each one is a thin wrapper around a function in analytics.py."""
from __future__ import annotations

import re
from datetime import date, datetime

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Response

from . import analytics, config
from .data_store import DataNotAvailable, get_store

router = APIRouter()

CUTOFF_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


def _store():
    try:
        return get_store()
    except DataNotAvailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _window(start: datetime, end: datetime) -> tuple[pd.Timestamp, pd.Timestamp]:
    s, e = analytics.as_utc_timestamp(start), analytics.as_utc_timestamp(end)
    lo, hi = analytics.as_utc_timestamp(config.DATA_START), analytics.as_utc_timestamp(config.DATA_END)
    if s >= e:
        raise HTTPException(status_code=422, detail="`start` must be before `end`.")
    if s < lo or e > hi:
        raise HTTPException(status_code=422, detail=f"Dates must lie within {lo:%Y-%m-%d} and {hi:%Y-%m-%d}.")
    return s, e


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/meta")
def meta() -> dict:
    store = _store()
    return {
        "source": store.meta.get("source"),
        "description": store.meta.get("description"),
        "saved_at": store.meta.get("saved_at"),
        "data_start": config.DATA_START.isoformat(),
        "data_end": config.DATA_END.isoformat(),
        "max_horizon_hours": config.MAX_HORIZON_HOURS,
        "local_timezone": config.LOCAL_TZ,
        "actual_rows": int(len(store.actuals)),
        "forecast_rows": int(len(store.forecasts)),
        "first_publish_time": analytics._ts(store.forecasts["publishTime"].min()),
        "last_publish_time": analytics._ts(store.forecasts["publishTime"].max()),
    }


@router.get("/analysis")
def analysis(
    start: datetime = Query(..., description="Window start (inclusive), ISO 8601"),
    end: datetime = Query(..., description="Window end (exclusive), ISO 8601"),
    horizon: float = Query(24, ge=0, le=config.MAX_HORIZON_HOURS, description="Minimum forecast lead time in hours"),
) -> dict:
    store = _store()
    s, e = _window(start, end)
    return analytics.analysis(store.actuals, store.forecasts, s, e, horizon)


@router.get("/horizon-profile")
def horizon_profile(
    start: datetime = Query(...),
    end: datetime = Query(...),
    step: float = Query(1, gt=0, le=12),
) -> dict:
    store = _store()
    s, e = _window(start, end)
    rows = analytics.horizon_profile(store.actuals, store.forecasts, s, e, 0, config.MAX_HORIZON_HOURS, step)
    return {"rows": rows}


@router.get("/day-ahead")
def day_ahead(
    delivery_date: date = Query(..., description="The day the power is delivered (UK local date)"),
    cutoff: str = Query("09:00", pattern=CUTOFF_PATTERN, description="Decision time on the previous day, HH:MM UK time"),
    confidence: float = Query(0.90, ge=0.5, le=0.99),
) -> dict:
    store = _store()
    hour, minute = (int(part) for part in cutoff.split(":"))
    try:
        return analytics.day_ahead(
            store.actuals, store.forecasts, delivery_date, hour, minute,
            config.DATA_START, config.DATA_END, confidence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/export.csv")
def export_csv(
    start: datetime = Query(...),
    end: datetime = Query(...),
    horizon: float = Query(24, ge=0, le=config.MAX_HORIZON_HOURS),
) -> Response:
    store = _store()
    s, e = _window(start, end)
    frame = analytics.export_frame(store.actuals, store.forecasts, s, e, horizon)
    return Response(
        content=frame.to_csv(index=False),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="wind_actual_vs_forecast_{horizon:g}h.csv"'},
    )
