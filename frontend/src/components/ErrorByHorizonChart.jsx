import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtNumber } from "../utils.js";

export default function ErrorByHorizonChart({ rows, horizon }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="horizon_hours" type="number" domain={[0, "dataMax"]} label={{ value: "Forecast horizon (hours before target time)", position: "insideBottom", offset: -12 }} />
        <YAxis tickFormatter={(v) => fmtNumber(v)} label={{ value: "MW", angle: -90, position: "insideLeft" }} />
        <Tooltip formatter={(value) => `${fmtNumber(value)} MW`} labelFormatter={(h) => `${h} h ahead`} />
        <Legend verticalAlign="top" />
        <ReferenceLine x={horizon} stroke="#555" strokeDasharray="4 4" label={{ value: "selected", position: "top", fontSize: 11 }} />
        <Line dataKey="mae_mw" name="MAE" stroke="#0b6e4f" strokeWidth={2} dot={false} isAnimationActive={false} />
        <Line dataKey="rmse_mw" name="RMSE" stroke="#d1495b" strokeWidth={2} dot={false} isAnimationActive={false} />
        <Line dataKey="p95_shortfall_mw" name="95th pct shortfall" stroke="#edae49" strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
