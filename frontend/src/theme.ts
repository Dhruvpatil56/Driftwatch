import type { Risk } from "./api/client";

// Risk colors: Critical=red, High=orange, Medium=yellow, Low=green.
export const RISK_LEVELS: Risk[] = ["Critical", "High", "Medium", "Low"];

// Colored pill (badge) per risk — subtle fill + matching border/text.
export const riskBadgeClass: Record<Risk, string> = {
  Critical: "bg-red-500/15 text-red-400 border border-red-500/30",
  High: "bg-orange-500/15 text-orange-400 border border-orange-500/30",
  Medium: "bg-yellow-500/15 text-yellow-300 border border-yellow-500/30",
  Low: "bg-green-500/15 text-green-400 border border-green-500/30",
};

// Text-only color per risk (used for summary-card numbers).
export const riskTextClass: Record<Risk, string> = {
  Critical: "text-red-400",
  High: "text-orange-400",
  Medium: "text-yellow-300",
  Low: "text-green-400",
};

// Raw hex per risk — for the chart and inline border accents.
export const riskHex: Record<Risk, string> = {
  Critical: "#ef4444",
  High: "#f97316",
  Medium: "#eab308",
  Low: "#22c55e",
};

export function riskClassFor(risk: string | null): string {
  if (risk && risk in riskBadgeClass) {
    return riskBadgeClass[risk as Risk];
  }
  return "bg-slate-700/40 text-slate-300 border border-slate-600/40";
}

// --- drift-type colors ------------------------------------------------------
// Distinct hue per drift type so the chart and type pills are readable at a
// glance (not all the same blue). Unknown types fall back to slate.
export const typeHex: Record<string, string> = {
  "Infrastructure Drift": "#38bdf8", // sky
  "Configuration Drift": "#a78bfa", // violet
  "Ownership Drift": "#f59e0b", // amber
  "State Drift": "#2dd4bf", // teal
  "Policy Drift": "#fb7185", // rose
};

const TYPE_FALLBACK = "#64748b"; // slate-500

export function typeHexFor(type: string | null): string {
  if (!type) return TYPE_FALLBACK;
  return typeHex[type] ?? TYPE_FALLBACK;
}

// --- time formatting --------------------------------------------------------
/** Compact relative time, e.g. "just now", "5m ago", "2h ago", "3d ago". */
export function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;

  const sec = Math.round((Date.now() - then) / 1000);
  if (sec < 45) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 30) return `${day}d ago`;
  const mo = Math.round(day / 30);
  if (mo < 12) return `${mo}mo ago`;
  return `${Math.round(mo / 12)}y ago`;
}

/** Full local timestamp, used as a hover title alongside relative time. */
export function absoluteTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}
