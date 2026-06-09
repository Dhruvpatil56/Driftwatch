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
import { absoluteTime, relativeTime } from "./theme";

const REFRESH_MS = 30_000;

export default function App() {
  const [events, setEvents] = useState<DriftEvent[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const [drift, sum] = await Promise.all([getDrift(), getSummary()]);
      setEvents(drift);
      setSummary(sum);
      setLastRefreshed(new Date().toISOString());
      setError(null);
    } catch {
      setError("Failed to reach the API. Is it running?");
    } finally {
      setRefreshing(false);
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
      <header className="sticky top-0 z-10 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-3.5">
          <div className="flex items-center gap-2.5">
            <span className="h-2.5 w-2.5 rounded-full bg-sky-500" />
            <h1 className="text-lg font-semibold tracking-tight text-slate-100">
              DriftWatch
            </h1>
          </div>

          <div className="flex items-center gap-4">
            <div
              className="flex items-center gap-2 text-xs text-slate-500"
              title={absoluteTime(lastRefreshed)}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  refreshing ? "animate-pulse bg-sky-400" : "bg-slate-600"
                }`}
              />
              {lastRefreshed
                ? `Updated ${relativeTime(lastRefreshed)}`
                : "Loading…"}
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => runAction(simulateDrift)}
                disabled={busy}
                className="rounded-md bg-sky-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-sky-500 disabled:opacity-50"
              >
                Simulate Drift
              </button>
              <button
                onClick={() => runAction(restoreState)}
                disabled={busy}
                className="rounded-md border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-800 disabled:opacity-50"
              >
                Restore State
              </button>
              <button
                onClick={() => runAction(async () => undefined)}
                disabled={busy}
                className="rounded-md border border-slate-700 px-3 py-1.5 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800 disabled:opacity-50"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        {error && (
          <div className="mb-5 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
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
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-white">
            Drift events
            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-400 tabular-nums">
              {events.length}
            </span>
          </h2>
          <DriftTable events={events} />
        </section>
      </main>
    </div>
  );
}
