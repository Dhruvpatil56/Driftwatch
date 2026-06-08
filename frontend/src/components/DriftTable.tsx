import type { DriftEvent } from "../api/client";
import { riskClassFor } from "../theme";

interface Props {
  events: DriftEvent[];
}

function formatTime(ts: string | null): string {
  if (!ts) return "—";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

const COLUMNS = ["Resource", "Type", "Field", "Desired", "Actual", "Risk", "Detected At"];

export default function DriftTable({ events }: Props) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-800 bg-slate-900/80 text-slate-400">
          <tr>
            {COLUMNS.map((c) => (
              <th key={c} className="px-4 py-3 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {events.length === 0 ? (
            <tr>
              <td colSpan={COLUMNS.length} className="px-4 py-10 text-center text-slate-500">
                No drift detected.
              </td>
            </tr>
          ) : (
            events.map((e) => (
              <tr key={e.id} className="border-b border-slate-800/60 hover:bg-slate-800/30">
                <td className="px-4 py-3 font-mono text-slate-200">{e.resource_address}</td>
                <td className="px-4 py-3 text-slate-300">{e.drift_type}</td>
                <td className="px-4 py-3 text-slate-400">{e.field ?? "—"}</td>
                <td className="px-4 py-3 font-mono text-slate-400">{e.desired ?? "—"}</td>
                <td className="px-4 py-3 font-mono text-slate-200">{e.actual ?? "—"}</td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskClassFor(
                      e.risk_impact
                    )}`}
                  >
                    {e.risk_impact ?? "—"}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-400">{formatTime(e.detected_at)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
