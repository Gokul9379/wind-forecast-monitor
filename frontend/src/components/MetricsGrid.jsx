import StatCard from "./StatCard.jsx";
import { fmtMW, fmtNumber } from "../utils.js";

export default function MetricsGrid({ metrics }) {
  if (!metrics || metrics.n_points === 0) {
    return <p className="muted">No overlapping actual and forecast data for this selection.</p>;
  }
  const bias = metrics.bias_mw;
  return (
    <div className="stats">
      <StatCard label="MAE" value={fmtMW(metrics.mae_mw)} hint={`${fmtNumber(metrics.nmae_pct, 1)}% of average wind`} />
      <StatCard label="RMSE" value={fmtMW(metrics.rmse_mw)} hint="penalises big misses" />
      <StatCard
        label="Bias"
        value={fmtMW(bias)}
        hint={bias < 0 ? "forecast too high on average" : "forecast too low on average"}
      />
      <StatCard label="Median abs. error" value={fmtMW(metrics.median_abs_error_mw)} hint="half of the errors are smaller" />
      <StatCard label="90th pct abs. error" value={fmtMW(metrics.p90_abs_error_mw)} hint="9 in 10 errors are smaller" />
      <StatCard label="99th pct abs. error" value={fmtMW(metrics.p99_abs_error_mw)} hint="worst 1% of misses" />
      <StatCard
        label="Shortfall frequency"
        value={`${fmtNumber(metrics.shortfall_share_pct, 1)}%`}
        hint="half-hours with less wind than forecast"
        tone="warn"
      />
      <StatCard
        label="95th pct shortfall"
        value={fmtMW(metrics.p95_shortfall_mw)}
        hint="extra power needed in 1 of 20 half-hours"
        tone="warn"
      />
      <StatCard
        label="Data points"
        value={fmtNumber(metrics.n_points)}
        hint={`forecast age ≈ ${fmtNumber(metrics.mean_forecast_age_hours, 1)} h`}
      />
    </div>
  );
}
