"""End-to-end tests of the HTTP layer (skipped automatically if FastAPI is not installed)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app import analytics, routes  # noqa: E402
from app.data_store import DataStore  # noqa: E402
from app.main import app  # noqa: E402
from scripts.generate_demo_data import generate  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    actuals, forecasts, meta = generate()
    actuals["startTime"] = analytics.to_utc_ns(actuals["startTime"])
    forecasts["startTime"] = analytics.to_utc_ns(forecasts["startTime"])
    forecasts["publishTime"] = analytics.to_utc_ns(forecasts["publishTime"])
    store = DataStore(actuals=actuals, forecasts=forecasts, meta=meta)
    monkeypatch.setattr(routes, "get_store", lambda: store)
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_meta(client):
    body = client.get("/api/meta").json()
    assert body["max_horizon_hours"] == 48 and body["actual_rows"] == 1488


def test_analysis(client):
    r = client.get("/api/analysis", params={"start": "2026-01-01T00:00:00Z", "end": "2026-01-03T00:00:00Z", "horizon": 12})
    assert r.status_code == 200
    body = r.json()
    assert len(body["points"]) == 96 and body["metrics"]["n_points"] > 0


def test_analysis_rejects_dates_outside_january(client):
    r = client.get("/api/analysis", params={"start": "2025-12-01T00:00:00Z", "end": "2026-01-03T00:00:00Z"})
    assert r.status_code == 422


def test_horizon_above_limit_is_rejected(client):
    r = client.get("/api/analysis", params={"start": "2026-01-01T00:00:00Z", "end": "2026-01-02T00:00:00Z", "horizon": 49})
    assert r.status_code == 422


def test_day_ahead(client):
    r = client.get("/api/day-ahead", params={"delivery_date": "2026-01-10", "cutoff": "09:00"})
    assert r.status_code == 200 and len(r.json()["points"]) == 48


def test_day_ahead_bad_cutoff(client):
    r = client.get("/api/day-ahead", params={"delivery_date": "2026-01-10", "cutoff": "9am"})
    assert r.status_code == 422


def test_csv_export(client):
    r = client.get("/api/export.csv", params={"start": "2026-01-01T00:00:00Z", "end": "2026-01-02T00:00:00Z"})
    assert r.status_code == 200 and r.text.startswith("target_time_utc,")
