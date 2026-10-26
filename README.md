# Wind Forecast Monitor

A web app that helps a GB electricity buyer decide how much power to buy on the **day-ahead market**,
by showing (1) the wind forecasts that were available when the decision had to be made and
(2) how accurate those forecasts have been. Data: Elexon BMRS, national wind, **January 2026**.

* **Frontend:** React (Vite) + Recharts
* **Backend:** Python 3.12, FastAPI, pandas
* **Data:** Elexon `FUELHH` (actual wind, 30 min) and `WINDFOR` (wind forecasts with `publishTime`)
* **Containers:** Docker + docker-compose

> **Live demo:** `<paste your Vercel / Heroku URL here>`
>
> **AI disclosure:** this project was built with the assistance of an AI tool (Anthropic's Claude), which was
> used to generate the code, tests and documentation.

---

## 1. Quick start

### Option A: Docker (recommended)

```bash
docker compose up --build
```

* App: <http://localhost:3000>
* API docs (Swagger): <http://localhost:8000/docs>

On first start the backend downloads January 2026 from Elexon (about a minute) and stores it in
`backend/data/`. Later starts reuse it. No API key is needed.

### Option B: run locally without Docker

```bash
# terminal 1 - backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m scripts.fetch_data                            # real Elexon data (needs internet)
uvicorn app.main:app --reload                           # http://localhost:8000

# terminal 2 - frontend
cd frontend
npm install
npm run dev                                             # http://localhost:5173 (proxies /api to :8000)
```

No internet? Run `python -m scripts.fetch_data --demo` for **synthetic** data. The UI then shows a
yellow "Demo data" banner so it can never be confused with the real thing.

### Tests

```bash
cd backend && python -m pytest -q
```

---

## 2. What the app does

| Tab | Question it answers |
|---|---|
| **Day-ahead decision** | "For delivery day D, what did the newest forecast say at my decision time on D-1, how much wind energy is that, and how much can I safely count on?" |
| **Forecast accuracy explorer** | "How good are the forecasts at a given lead time?" Actual vs forecast chart, error metrics, error-by-horizon curve, error histogram, CSV download. |

### Method

* **Target time** = Elexon `startTime`, **publish time** = `publishTime`, **horizon** = target − publish.
* **Choosing a forecast.** For each target half-hour, take the **latest forecast published at or before a cut-off**
  (as-of join, `pandas.merge_asof`). This guarantees no forecast "from the future" is ever used.
  * *Horizon mode:* cut-off = target − H hours (H = 0…48, slider).
  * *Day-ahead mode:* cut-off = chosen time (default 09:00 UK time) on the previous day.
* **Error** = actual − forecast. Negative = less wind than forecast (extra thermal power must be bought).
* **Metrics:** MAE, RMSE, bias, normalised MAE (% of mean wind), median / P90 / P99 absolute error,
  share of half-hours with a shortfall, P95 shortfall, error quantiles.
* **Conservative wind.** The day-ahead tab backtests the same decision rule on all *other* January days and takes
  the error quantile (e.g. 10th percentile for 90% confidence). *Conservative wind = forecast + that quantile* (never below 0).
  It is a simple empirical band, not a probabilistic model.

### Assumptions and limitations (please read)

1. **"Decisions made in January 2026"** is interpreted as *target (delivery) half-hours in January 2026*
   (`2026-01-01 00:00` to `2026-02-01 00:00` UTC). Change `DATA_START` / `DATA_END` to alter it.
2. **Decision time defaults to 09:00 UK time** on the previous day. This is an assumption, not the exact
   gate closure of a specific exchange, so it is editable in the UI.
3. Times are UTC. In January UTC equals UK local time; the day-ahead cut-off logic still handles BST correctly (unit-tested).
4. Only wind data from Elexon is used, as required. **Demand is not available**, so the app
   cannot compute "MW still to buy"; it shows wind and its uncertainty, which is the input to that decision.
5. Forecasts older than `FORECAST_RETENTION_HOURS` (default 72) are dropped. The slider stops at 48 h.
6. If no forecast exists that is old enough for a time slot, the slot is left empty (a gap) and excluded from metrics.
   Each point reports the real age of the forecast used, so you can see this.
7. **Forecast resolution.** If forecasts exist only for some half-hours (e.g. hourly), daily energy totals use the average of the available forecast values times the full day length, so they stay comparable with actuals. The day-ahead tab shows how many half-hours had a forecast.
8. The error band is estimated in-sample on one month of data and is a constant MW offset; it is a guide, not a guarantee.

---

## 3. Files and directories

```
.
├── docker-compose.yml            Starts backend (8000) and frontend (3000)
├── .github/workflows/ci.yml      CI: backend tests + frontend build
├── backend/
│   ├── Dockerfile                Fetches data if missing, then starts uvicorn
│   ├── requirements.txt          Runtime dependencies
│   ├── requirements-dev.txt      + pytest, httpx
│   ├── pytest.ini
│   ├── vercel.json, api/index.py Vercel serverless entry point
│   ├── data/                     Data snapshot (actuals.csv.gz, forecasts.csv.gz, meta.json)
│   ├── app/
│   │   ├── config.py             Settings (env variables with defaults)
│   │   ├── elexon_client.py      Calls Elexon, parses and chunks responses
│   │   ├── data_store.py         Saves/loads the snapshot, caches it in memory
│   │   ├── analytics.py          ALL the maths: forecast selection, metrics, day-ahead
│   │   ├── routes.py             HTTP endpoints (thin wrappers over analytics.py)
│   │   └── main.py               FastAPI app, CORS
│   ├── scripts/
│   │   ├── fetch_data.py         CLI: build the snapshot from Elexon (or --demo)
│   │   └── generate_demo_data.py Synthetic data generator (offline use only)
│   └── tests/                    Unit tests (analytics, parsing, store) + API tests
└── frontend/
    ├── Dockerfile, nginx.conf    Build static files, serve them, proxy /api
    ├── package.json, vite.config.js, index.html
    └── src/
        ├── main.jsx, App.jsx     Entry point, tabs, banners
        ├── api.js, hooks.js, utils.js   Backend calls, data-loading hook, formatting
        ├── styles.css
        └── components/           ExplorePanel, DayAheadPanel, charts, MetricsGrid, StatCard, Glossary...
```

## 4. API

| Endpoint | Purpose |
|---|---|
| `GET /api/meta` | Data source, ranges, row counts, newest forecast time |
| `GET /api/analysis?start&end&horizon` | Points (actual, forecast, error, forecast age) + metrics + histogram. `start` inclusive, `end` exclusive (ISO 8601) |
| `GET /api/horizon-profile?start&end&step` | MAE / RMSE / bias / P95 shortfall for every horizon 0-48 h |
| `GET /api/day-ahead?delivery_date&cutoff&confidence` | Day-ahead view with conservative / optimistic band |
| `GET /api/export.csv?start&end&horizon` | CSV download |
| `GET /api/health` | Liveness check |

Interactive documentation: `/docs`.

## 5. Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `DATA_DIR` | `backend/data` | Where the snapshot lives |
| `DATA_START`, `DATA_END` | `2026-01-01`, `2026-02-01` | Target-time window `[start, end)` |
| `MAX_HORIZON_HOURS` | `48` | Largest horizon on the slider |
| `FORECAST_RETENTION_HOURS` | `72` | Oldest forecast kept |
| `LOCAL_TZ` | `Europe/London` | Time zone of the day-ahead decision time |
| `CORS_ORIGINS` | `*` | Allowed browser origins (comma separated) |
| `VITE_API_URL` (frontend) | empty | Backend URL when frontend and backend are on different hosts |

## 6. Deploying to Vercel

Create **two** Vercel projects from the same repo:

1. **Backend:** root directory `backend`. First run `python -m scripts.fetch_data` locally and **commit the files in
   `backend/data/`** (small files), so the serverless function never has to call Elexon. Set `CORS_ORIGINS` to the frontend URL.
2. **Frontend:** root directory `frontend`, framework *Vite*. Set `VITE_API_URL` to the backend project's URL.

Put the frontend URL at the top of this README. Open both URLs in an incognito window to check they are public.

## 7. Design decisions

* **Snapshot instead of live API calls.** January 2026 is historical, so a fixed snapshot is faster, offline-safe, and serverless-friendly.
* **Pure-function analytics.** `analytics.py` has no HTTP or file code, so it is unit-tested directly.
* **As-of join for forecast selection.** The cleanest way to guarantee we only use information available at the decision time.
* **Transparency.** Every chart point carries the publish time and age of the forecast behind it.
