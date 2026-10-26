import { useState } from "react";
import { exportUrl, getAnalysis, getHorizonProfile } from "../api.js";
import { useApi, useDebounced } from "../hooks.js";
import { addDays, toApiRange } from "../utils.js";
import ErrorByHorizonChart from "./ErrorByHorizonChart.jsx";
import ErrorHistogram from "./ErrorHistogram.jsx";
import ForecastChart from "./ForecastChart.jsx";
import MetricsGrid from "./MetricsGrid.jsx";

export default function ExplorePanel({ meta }) {
  const minDay = meta.data_start.slice(0, 10);
  const maxDay = addDays(meta.data_end.slice(0, 10), -1);

  const [startDate, setStartDate] = useState(minDay);
  const [endDate, setEndDate] = useState(addDays(minDay, 6));
  const [horizonInput, setHorizonInput] = useState(24);
  const horizon = useDebounced(horizonInput, 300); // don't hit the API on every slider pixel

  const rangeIsValid = startDate && endDate && startDate <= endDate;
  const range = rangeIsValid ? toApiRange(startDate, endDate) : null;

  const analysis = useApi(
    (signal) => (range ? getAnalysis({ ...range, horizon }, signal) : Promise.reject(new Error("Start date must not be after end date."))),
    [range?.start, range?.end, horizon]
  );
  const profile = useApi(
    (signal) => (range ? getHorizonProfile(range, signal) : Promise.reject(new Error("Invalid date range."))),
    [range?.start, range?.end]
  );

  return (
    <>
      <section className="card controls">
        <label>
          From
          <input type="date" value={startDate} min={minDay} max={maxDay} onChange={(e) => setStartDate(e.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={endDate} min={minDay} max={maxDay} onChange={(e) => setEndDate(e.target.value)} />
        </label>
        <label className="grow">
          Forecast horizon: <strong>{horizonInput} h</strong>
          <input type="range" min="0" max={meta.max_horizon_hours} step="1" value={horizonInput}
                 onChange={(e) => setHorizonInput(Number(e.target.value))} />
          <span className="muted small">
            Each half-hour uses the newest forecast that was published at least {horizonInput} h earlier.
          </span>
        </label>
        {range && (
          <a className="button" href={exportUrl({ ...range, horizon })}>Download CSV</a>
        )}
      </section>

      {analysis.error && <div className="banner banner-error">{analysis.error}</div>}

      <section className="card">
        <h2>Actual vs forecast wind generation</h2>
        {analysis.data ? <ForecastChart points={analysis.data.points} /> : <p className="muted">Loading…</p>}
        <p className="muted small">If forecasts exist only for some half-hours (e.g. hourly forecasts), the line joins the points that exist. Slots with no forecast that old are skipped in the statistics.</p>
      </section>

      <section className="card">
        <h2>Forecast accuracy at a {horizon} h horizon</h2>
        {analysis.data ? <MetricsGrid metrics={analysis.data.metrics} /> : <p className="muted">Loading…</p>}
      </section>

      <div className="two-col">
        <section className="card">
          <h2>Error by forecast horizon</h2>
          <p className="muted small">How accuracy gets worse the further ahead the forecast was made.</p>
          {profile.data ? <ErrorByHorizonChart rows={profile.data.rows} horizon={horizon} /> : <p className="muted">{profile.error || "Loading…"}</p>}
        </section>
        <section className="card">
          <h2>Error distribution</h2>
          <p className="muted small">Left of zero: less wind than forecast. Right of zero: more wind than forecast.</p>
          {analysis.data ? <ErrorHistogram bins={analysis.data.histogram} /> : <p className="muted">Loading…</p>}
        </section>
      </div>
    </>
  );
}
