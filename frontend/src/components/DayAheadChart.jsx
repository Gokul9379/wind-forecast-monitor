import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ChartTooltip from "./ChartTooltip.jsx";
import { fmtHourMinute, fmtNumber } from "../utils.js";

export default function DayAheadChart({ points, confidence }) {
  const data = points.map((p) => ({
    ...p,
    band: p.conservative_mw === null || p.optimistic_mw === null ? null : [p.conservative_mw, p.optimistic_mw],
  }));
  const pct = Math.round(confidence * 100);
  return (
    <ResponsiveContainer width="100%" height={380}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="time" tickFormatter={fmtHourMinute} minTickGap={40} />
        <YAxis tickFormatter={(v) => fmtNumber(v)} label={{ value: "MW", angle: -90, position: "insideLeft" }} />
        <Tooltip content={<ChartTooltip />} />
        <Legend />
        <Area connectNulls dataKey="band" name={`Likely range (${pct}% / ${pct}%)`} stroke="none" fill="#3d5a80" fillOpacity={0.18} isAnimationActive={false} />
        <Line connectNulls dataKey="conservative_mw" name={`Conservative (≥ ${pct}% likely)`} stroke="#3d5a80" strokeDasharray="3 3" dot={false} isAnimationActive={false} />
        <Line connectNulls dataKey="forecast_mw" name="Forecast at decision time" stroke="#d1495b" strokeWidth={2} dot={false} isAnimationActive={false} />
        <Line dataKey="actual_mw" name="Actual (hindsight)" stroke="#0b6e4f" strokeWidth={2} dot={false} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
