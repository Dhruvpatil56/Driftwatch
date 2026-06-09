import axios from "axios";

// API base comes from VITE_API_URL (set via env / docker), with a local default.
const baseURL = "/api";

const api = axios.create({ baseURL });

export type Risk = "Critical" | "High" | "Medium" | "Low";

export interface DriftEvent {
  id: string;
  resource_address: string;
  drift_type: string;
  field: string | null;
  desired: string | null;
  recorded: string | null;
  actual: string | null;
  cost_impact: string | null;
  risk_impact: string | null;
  governance_impact: string | null;
  detected_at: string | null;
  resolved_at: string | null;
}

export interface Summary {
  total: number;
  by_risk: Record<Risk, number>;
  by_type: Record<string, number>;
}

export interface Explanation {
  id: string;
  resource_address: string;
  drift_type: string;
  explanation: string;
}

export const getDrift = () =>
  api.get<DriftEvent[]>("/drift").then((r) => r.data);

export const getSummary = () =>
  api.get<Summary>("/drift/summary").then((r) => r.data);

export const explainDrift = (id: string) =>
  api.get<Explanation>(`/drift/${id}/explain`).then((r) => r.data);

export interface RemediationPatch {
  resource_address: string;
  patch_hcl: string;
  import_command: string | null;
  description: string;
}

export interface RemediateResult {
  pr_url: string | null;
  patch: RemediationPatch | null;
  detail?: string;
}

export const remediateDrift = (id: string) =>
  api.post<RemediateResult>(`/drift/${id}/remediate`).then((r) => r.data);

export const simulateDrift = () =>
  api.post("/drift/simulate").then((r) => r.data);

export const restoreState = () =>
  api.post("/drift/restore").then((r) => r.data);
