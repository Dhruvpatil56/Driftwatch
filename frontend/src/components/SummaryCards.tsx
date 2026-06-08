import type { Summary } from "../api/client";
import { RISK_LEVELS, riskBadgeClass } from "../theme";

interface Props {
  summary: Summary | null;
}

function Card({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="text-sm text-slate-400">{label}</div>
      <div className={`mt-1 text-3xl font-semibold ${accent ?? "text-slate-100"}`}>
        {value}
      </div>
    </div>
  );
}

export default function SummaryCards({ summary }: Props) {
  const total = summary?.total ?? 0;
  const byRisk = summary?.by_risk;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      <Card label="Total Drift" value={total} />
      {RISK_LEVELS.map((level) => (
        <Card
          key={level}
          label={level}
          value={byRisk?.[level] ?? 0}
          accent={riskBadgeClass[level].split(" ")[1]}
        />
      ))}
    </div>
  );
}
