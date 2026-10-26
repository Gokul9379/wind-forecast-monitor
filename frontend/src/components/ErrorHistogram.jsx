import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtNumber } from "../utils.js";

export default function ErrorHistogram({ bins }) {
  const data = bins.map((b) => ({ ...b, mid: (b.bin_start + b.bin_end) / 2 }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 8 }} barCategoryGap={1}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="mid" tickFormatter={(v) => fmtNumber(v)} interval="preserveStartEnd" minTickGap={40}
               label={{ value: "Error = actual − forecast (MW)", position: "insideBottom", offset: -12 }} />
        <YAxis label={{ value: "Half-hours", angle: -90, position: "insideLeft" }} />
        <Tooltip
          labelFormatter={(mid) => `Error around ${fmtNumber(mid)} MW`}
          formatter={(value) => [fmtNumber(value), "half-hours"]}
        />
        <ReferenceLine x={data.length ? data.reduce((best, d) => (Math.abs(d.mid) < Math.abs(best.mid) ? d : best)).mid : 0} stroke="#555" />
        <Bar dataKey="count" fill="#3d5a80" isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}
