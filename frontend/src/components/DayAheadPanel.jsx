import { useState } from "react";
import { getDayAhead } from "../api.js";
import { useApi } from "../hooks.js";
import { addDays, fmtMW, fmtMWh, fmtNumber, fmtTime } from "../utils.js";
import DayAheadChart from "./DayAheadChart.jsx";
import MetricsGrid from "./MetricsGrid.jsx";
import StatCard from "./StatCard.jsx";

export default function DayAheadPanel({ meta }) {
  const minDay = meta.data_start.slice(0, 10);
  const maxDay = addDays(meta.data_end.slice(0, 10), -1);

  const [deliveryDate, setDeliveryDate] = useState(addDays(minDay, 14));
  const [cutoff, setCutoff] = useState("09:00");
  const [confidence, setConfidence] = useState(0.9);

  const result = useApi(
    (signal) =>
      deliveryDate && /^\d{2}:\d{2}$/.test(cutoff)
        ? getDayAhead({ delivery_date: deliveryDate, cutoff, confidence }, signal)
        : Promise.reject(new Error("Choose a delivery date and a decision time.")),
    [deliveryDate, cutoff, confidence]
  );
  const s = result.data?.summary;

  return (
    <>
      <section className="card controls">
        <label>
          Delivery day
          <input type="date" value={deliveryDate} min={minDay} max={maxDay} onChange={(e) => setDeliveryDate(e.target.value)} />
        </label>
        <label>
          Decision time (day before, UK time)
          <input type="time" value={cutoff} onChange={(e) => setCutoff(e.target.value)} />
        </label>
        <label>
          Planning confidence
          <select value={confidence} onChange={(e) => setConfidence(Number(e.target.value))}>
            <option value={0.8}>80%</option>
            <option value={0.9}>90%</option>
            <option value={0.95}>95%</option>
          </select>
        </label>
        <p className="muted small grow">
          The forecast shown is the newest one published before the decision time on the day before delivery,
          exactly what a trader could see when bidding in the day-ahead market. The decision time is an assumption
          you can change to match your desk’s gate closure.
        </p>
      </section>

      {result.error && <div className="banner banner-error">{result.error}</div>}

      {s && (
        <>
          <section className="card">
            <h2>What was known at decision time</h2>
            <div className="stats">
              <StatCard label="Decision time" value={`${fmtTime(s.decision_cutoff_utc)} UTC`} hint="latest forecast before this moment is used" />
              <StatCard
                label="Forecast issued"
                value={s.forecast_publish_max ? `${fmtTime(s.forecast_publish_max)} UTC` : "–"}
                hint={s.forecast_publish_min !== s.forecast_publish_max ? `earliest used: ${fmtTime(s.forecast_publish_min)}` : "same issue for the whole day"}
              />
              <StatCard label="Forecast wind energy" value={fmtMWh(s.forecast_energy_mwh)} hint={s.n_with_forecast < s.n_periods ? `${s.n_with_forecast} of ${s.n_periods} half-hours have a forecast; scaled to the full day` : "whole delivery day"} />
              <StatCard
                label={`Plan for at least (${Math.round(s.confidence * 100)}%)`}
                value={fmtMWh(s.conservative_energy_mwh)}
                hint="forecast minus typical shortfall"
                tone="warn"
              />
              <StatCard label="Actual wind energy" value={fmtMWh(s.actual_energy_mwh)} hint="known only afterwards" />
            </div>
          </section>

          <section className="card">
            <h2>Delivery day {s.delivery_date}: forecast vs actual</h2>
            <DayAheadChart points={result.data.points} confidence={s.confidence} />
            <p className="muted small">
              The shaded band is based on {fmtNumber(s.backtest_points)} half-hours from the other days of January
              forecast with the same decision time: wind was at least {fmtMW(s.conservative_offset_mw)} relative to the forecast
              in {Math.round(s.confidence * 100)}% of cases, and at most {fmtMW(s.optimistic_offset_mw)} in {Math.round(s.confidence * 100)}%.
              (Past performance in one month is an indication, not a guarantee.)
            </p>
          </section>

          <section className="card">
            <h2>How accurate was this decision-time forecast?</h2>
            <h3>This delivery day</h3>
            <MetricsGrid metrics={s.day_metrics} />
            <h3>All other January days (same decision time)</h3>
            <div className="stats">
              <StatCard label="MAE" value={fmtMW(s.backtest_mae_mw)} />
              <StatCard label="RMSE" value={fmtMW(s.backtest_rmse_mw)} />
              <StatCard label="Bias" value={fmtMW(s.backtest_bias_mw)} />
            </div>
          </section>
        </>
      )}
      {result.loading && !s && <p className="muted">Loading…</p>}
    </>
  );
}
