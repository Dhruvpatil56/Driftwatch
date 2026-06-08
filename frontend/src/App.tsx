import { useCallback, useEffect, useState } from "react";
import {
  getDrift,
  getSummary,
  restoreState,
  simulateDrift,
  type DriftEvent,
  type Summary,
} from "./api/client";
import DriftChart from "./components/DriftChart";
import DriftTable from "./components/DriftTable";
import SummaryCards from "./components/SummaryCards";

const REFRESH_MS = 30_000;

export default function App() {
  const [events, setEvents] = useState<DriftEvent[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [drift, sum] = await Promise.all([getDrift(), getSummary()]);
      setEvents(drift);
      setSummary(sum);
      setError(null);
    } catch (e) {
      setError("Failed to reach the API. Is it running?");
    }
  }, []);

  // Initial load + 30s auto-refresh.
  useEffect(() => {
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  const runAction = async (action: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await action();
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-full">
      <div className="mx-auto max-w-7xl px-6 py-6">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-100">DriftWatch</h1>
            <p className="text-sm text-slate-400">
              Terraform-aware cloud drift dashboard
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => runAction(simulateDrift)}
              disabled={busy}
              className="rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
            >
              Simulate Drift
            </button>
            <button
              onClick={() => runAction(restoreState)}
              disabled={busy}
              className="rounded-md bg-slate-700 px-3 py-2 text-sm font-medium text-white hover:bg-slate-600 disabled:opacity-50"
            >
              Restore State
            </button>
            <button
              onClick={() => runAction(async () => undefined)}
              disabled={busy}
              className="rounded-md border border-slate-700 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-50"
            >
              Refresh
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-4 rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <section className="mb-6">
          <SummaryCards summary={summary} />
        </section>

        <section className="mb-6">
          <DriftChart summary={summary} />
        </section>

        <section>
          <h2 className="mb-3 text-sm font-medium text-slate-400">
            Drift events ({events.length})
          </h2>
          <DriftTable events={events} />
        </section>
      </div>
    </div>
  );
}
