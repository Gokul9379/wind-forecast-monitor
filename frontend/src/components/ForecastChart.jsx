import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ChartTooltip from "./ChartTooltip.jsx";
import { fmtNumber, fmtTime } from "../utils.js";

export default function ForecastChart({ points }) {
  return (
    <ResponsiveContainer width="100%" height={360}>
      <LineChart data={points} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="time" tickFormatter={fmtTime} minTickGap={60} />
        <YAxis tickFormatter={(v) => fmtNumber(v)} label={{ value: "MW", angle: -90, position: "insideLeft" }} />
        <Tooltip content={<ChartTooltip />} />
        <Legend />
        <Line type="monotone" dataKey="actual_mw" name="Actual" stroke="#0b6e4f" strokeWidth={2} dot={false} isAnimationActive={false} />
        <Line connectNulls type="monotone" dataKey="forecast_mw" name="Forecast" stroke="#d1495b" strokeWidth={2} strokeDasharray="6 3" dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
