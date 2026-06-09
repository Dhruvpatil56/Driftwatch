import type { Summary } from "../api/client";
import { RISK_LEVELS, riskHex, riskTextClass } from "../theme";

interface Props {
  summary: Summary | null;
}

function Card({
  label,
  value,
  valueClass,
  accentHex,
}: {
  label: string;
  value: number;
  valueClass: string;
  accentHex: string;
}) {
  return (
    <div
      className="rounded-xl border border-l-2 border-slate-800 bg-slate-900/60 px-4 py-3.5"
      style={{ borderLeftColor: accentHex }}
    >
      <div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-slate-500">
        {label}
      </div>
      <div
        className={`mt-2 text-[42px] font-bold leading-none tabular-nums ${valueClass}`}
      >
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
      {/* Total is neutral; colour lives only on the number for the others. */}
      <Card
        label="Total Drift"
        value={total}
        valueClass="text-slate-100"
        accentHex="#475569"
      />
      {RISK_LEVELS.map((level) => (
        <Card
          key={level}
          label={level}
          value={byRisk?.[level] ?? 0}
          valueClass={riskTextClass[level]}
          accentHex={riskHex[level]}
        />
      ))}
    </div>
  );
}
