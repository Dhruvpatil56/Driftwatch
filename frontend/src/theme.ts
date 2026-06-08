import type { Risk } from "./api/client";

// Risk colors: Critical=red, High=orange, Medium=yellow, Low=green.
export const RISK_LEVELS: Risk[] = ["Critical", "High", "Medium", "Low"];

export const riskBadgeClass: Record<Risk, string> = {
  Critical: "bg-red-500/20 text-red-400 border border-red-500/40",
  High: "bg-orange-500/20 text-orange-400 border border-orange-500/40",
  Medium: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/40",
  Low: "bg-green-500/20 text-green-400 border border-green-500/40",
};

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
