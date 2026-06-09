import { useState } from "react";
import {
  explainDrift,
  remediateDrift,
  type DriftEvent,
  type RemediateResult,
} from "../api/client";
import {
  absoluteTime,
  relativeTime,
  riskClassFor,
  typeHexFor,
} from "../theme";

interface Props {
  events: DriftEvent[];
}

interface ExplainState {
  loading: boolean;
  text?: string;
  error?: boolean;
}

interface RemediateState {
  loading: boolean;
  result?: RemediateResult;
  error?: boolean;
}

// --- small inline icons (no icon library) ----------------------------------
function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={`h-4 w-4 shrink-0 text-slate-500 transition-transform duration-150 ${
        open ? "rotate-90" : ""
      }`}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6 4l4 4-4 4" />
    </svg>
  );
}

function Sparkle() {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="currentColor">
      <path d="M12 2l1.6 5.4L19 9l-5.4 1.6L12 16l-1.6-5.4L5 9l5.4-1.6L12 2zM19 14l.8 2.7L22 17.5l-2.2.8L19 21l-.8-2.7L16 17.5l2.2-.8L19 14z" />
    </svg>
  );
}

// --- pills ------------------------------------------------------------------
function TypePill({ type }: { type: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-700/60 bg-slate-800/60 px-2 py-0.5 text-xs font-medium text-slate-300">
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: typeHexFor(type) }}
      />
      {type}
    </span>
  );
}

function RiskPill({ risk }: { risk: string | null }) {
  return (
    <span
      className={`inline-flex w-[72px] justify-center rounded-full px-2 py-0.5 text-xs font-semibold ${riskClassFor(
        risk
      )}`}
    >
      {risk ?? "—"}
    </span>
  );
}

function ArrowValue({
  from,
  to,
}: {
  from: string | null;
  to: string | null;
}) {
  return (
    <span className="flex items-center gap-1.5 font-mono text-xs">
      <span className="text-slate-500">{from ?? "—"}</span>
      <span className="text-slate-600">→</span>
      <span className="text-slate-200">{to ?? "—"}</span>
    </span>
  );
}

// --- expanded detail panel --------------------------------------------------
function DetailField({ label, value, mono }: { label: string; value: string | null; mono?: boolean }) {
  return (
    <div>
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className={`mt-0.5 text-sm text-slate-200 ${mono ? "font-mono" : ""}`}>
        {value && value !== "" ? value : "—"}
      </div>
    </div>
  );
}

function Explanation({ state }: { state: ExplainState | undefined }) {
  return (
    <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950/40 p-3">
      <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-sky-400">
        <Sparkle />
        AI explanation
      </div>
      {!state || state.loading ? (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <span className="h-2 w-2 animate-pulse rounded-full bg-sky-400" />
          Generating explanation…
        </div>
      ) : state.error ? (
        <div className="text-sm text-slate-500">
          Could not generate an explanation right now.
        </div>
      ) : (
        <p className="text-sm leading-relaxed text-slate-300">{state.text}</p>
      )}
    </div>
  );
}

function Remediation({
  state,
  onFix,
}: {
  state: RemediateState | undefined;
  onFix: () => void;
}) {
  const result = state?.result;
  const patch = result?.patch;

  return (
    <div className="mt-4 border-t border-slate-800 pt-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onFix}
          disabled={state?.loading}
          className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-emerald-500 disabled:opacity-50"
        >
          {state?.loading ? "Generating fix…" : "Fix via PR"}
        </button>
        {result?.pr_url && (
          <a
            href={result.pr_url}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium text-sky-400 hover:text-sky-300"
          >
            View pull request →
          </a>
        )}
        {result && !result.pr_url && patch && (
          <span className="text-xs text-slate-500">
            Patch generated — set GITHUB_TOKEN to open a PR.
          </span>
        )}
      </div>

      {state?.error && (
        <div className="mt-2 text-sm text-slate-500">
          Could not generate a fix right now.
        </div>
      )}

      {result?.detail && !patch && (
        <div className="mt-2 text-sm text-slate-400">{result.detail}</div>
      )}

      {patch && (
        <div className="mt-3 space-y-2">
          <p className="text-sm text-slate-400">{patch.description}</p>
          <pre className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/60 p-3 font-mono text-xs leading-relaxed text-slate-300">
            {patch.patch_hcl}
          </pre>
          {patch.import_command && (
            <pre className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/60 p-3 font-mono text-xs text-slate-300">
              {patch.import_command}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export default function DriftTable({ events }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [explanations, setExplanations] = useState<Record<string, ExplainState>>(
    {}
  );
  const [remediations, setRemediations] = useState<
    Record<string, RemediateState>
  >({});

  const runFix = (id: string) => {
    if (remediations[id]?.loading) return;
    setRemediations((m) => ({ ...m, [id]: { loading: true } }));
    remediateDrift(id)
      .then((result) =>
        setRemediations((m) => ({ ...m, [id]: { loading: false, result } }))
      )
      .catch(() =>
        setRemediations((m) => ({ ...m, [id]: { loading: false, error: true } }))
      );
  };

  const toggle = (event: DriftEvent) => {
    const next = expandedId === event.id ? null : event.id;
    setExpandedId(next);

    // Lazily fetch the AI explanation the first time a row is opened.
    if (next && !explanations[event.id]) {
      setExplanations((m) => ({ ...m, [event.id]: { loading: true } }));
      explainDrift(event.id)
        .then((r) =>
          setExplanations((m) => ({
            ...m,
            [event.id]: { loading: false, text: r.explanation },
          }))
        )
        .catch(() =>
          setExplanations((m) => ({
            ...m,
            [event.id]: { loading: false, error: true },
          }))
        );
    }
  };

  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-14 text-center text-sm text-slate-500">
        No drift detected.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {events.map((event) => {
        const open = expandedId === event.id;
        return (
          <div
            key={event.id}
            className={`overflow-hidden rounded-xl border bg-slate-900/60 transition-colors ${
              open ? "border-slate-700" : "border-slate-800 hover:border-slate-700"
            }`}
          >
            <button
              type="button"
              onClick={() => toggle(event)}
              aria-expanded={open}
              className="flex w-full items-center gap-3 px-4 py-3 text-left"
            >
              <Chevron open={open} />

              <div className="min-w-0 flex-1">
                <div className="truncate font-mono text-sm font-semibold text-slate-100">
                  {event.resource_address}
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <TypePill type={event.drift_type} />
                  {event.field && (
                    <span className="font-mono text-xs text-slate-500">
                      {event.field}
                    </span>
                  )}
                </div>
              </div>

              <div className="hidden lg:block">
                <ArrowValue from={event.desired} to={event.actual} />
              </div>

              <RiskPill risk={event.risk_impact} />

              <span
                className="hidden w-24 shrink-0 text-right text-xs text-slate-500 sm:block"
                title={absoluteTime(event.detected_at)}
              >
                {relativeTime(event.detected_at)}
              </span>
            </button>

            {open && (
              <div className="border-t border-slate-800 px-4 py-4">
                <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
                  <DetailField label="Field" value={event.field} mono />
                  <DetailField label="Desired" value={event.desired} mono />
                  <DetailField label="Actual" value={event.actual} mono />
                  <DetailField label="Recorded (state)" value={event.recorded} mono />
                  <DetailField label="Cost impact" value={event.cost_impact} />
                  <DetailField label="Governance" value={event.governance_impact} />
                </div>

                <Explanation state={explanations[event.id]} />

                <Remediation
                  state={remediations[event.id]}
                  onFix={() => runFix(event.id)}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
