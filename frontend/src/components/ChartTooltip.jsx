import { fmtMW, fmtNumber, fmtTime } from "../utils.js";

/** Tooltip shared by the time-series charts. */
export default function ChartTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  return (
    <div className="tooltip">
      <strong>{fmtTime(p.time)} UTC</strong>
      <div>Actual: {fmtMW(p.actual_mw)}</div>
      <div>Forecast: {fmtMW(p.forecast_mw)}</div>
      {p.conservative_mw !== undefined && <div>Conservative: {fmtMW(p.conservative_mw)}</div>}
      {p.error_mw !== undefined && <div>Error: {fmtMW(p.error_mw)}</div>}
      {p.publish_time && (
        <div className="muted">
          Forecast published {fmtTime(p.publish_time)} ({fmtNumber(p.forecast_horizon_hours, 1)} h ahead)
        </div>
      )}
    </div>
  );
}
