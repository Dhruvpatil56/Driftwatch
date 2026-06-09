import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Summary } from "../api/client";
import { typeHexFor } from "../theme";

interface Props {
  summary: Summary | null;
}

export default function DriftChart({ summary }: Props) {
  const data = Object.entries(summary?.by_type ?? {}).map(([type, count]) => ({
    type,
    count,
  }));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-4 text-sm font-medium text-slate-300">Drift by type</div>
      <div style={{ width: "100%", height: 300 }}>
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            No drift to chart.
          </div>
        ) : (
          <ResponsiveContainer>
            <BarChart
              data={data}
              margin={{ top: 8, right: 16, bottom: 28, left: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="type"
                stroke="#64748b"
                tickLine={false}
                axisLine={{ stroke: "#1e293b" }}
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                label={{
                  value: "Drift type",
                  position: "insideBottom",
                  offset: -14,
                  fill: "#64748b",
                  fontSize: 12,
                }}
              />
              <YAxis
                stroke="#64748b"
                allowDecimals={false}
                tickLine={false}
                axisLine={false}
                width={44}
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                label={{
                  value: "Events",
                  angle: -90,
                  position: "insideLeft",
                  fill: "#64748b",
                  fontSize: 12,
                }}
              />
              <Tooltip
                cursor={{ fill: "#33415533" }}
                contentStyle={{
                  background: "#0f172a",
                  border: "1px solid #1e293b",
                  borderRadius: 8,
                  color: "#e2e8f0",
                }}
                labelStyle={{ color: "#94a3b8" }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                {data.map((d) => (
                  <Cell key={d.type} fill={typeHexFor(d.type)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
