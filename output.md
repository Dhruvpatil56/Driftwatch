# DriftWatch — Build Status

**Current: Sprint 6 complete** — dashboard redesign (Goal 1) + GitOps PR generation (Goal 2).

## Latest changes (Sprint 6 — Goal 2: GitOps PR generation)
- **Remediator** (`engine/remediator/` → `RemediationPatch` in `models/remediation.py`): Infrastructure Drift → patch attribute to live value; Configuration Drift → restore attribute, or re-create note for a deleted resource; Ownership Drift → new resource block + `terraform import`; State/Policy/unknown → `None`. **Never emits a destroy.**
- **GitHub PR** (`api/github_pr.py`): branch `drift-fix/{addr}-{uuid}` off `drift-remediation`, appends patch to `terraform-demo/main.tf`, opens a PR (title `[DriftWatch] Fix drift on {addr}`, body = drift summary + HCL + import cmd + risk, footer "requires human review before merge"). `GITHUB_TOKEN`/`GITHUB_REPO` from env; unset or any error → `None` (no network).
- **Endpoint** `POST /api/drift/{id}/remediate` → `{pr_url, patch}`; patch-only with `pr_url: null` when GitHub is off/fails; `{patch: null, detail}` when no safe remediation (e.g. State Drift); 404 on unknown id.
- **Frontend**: "Fix via PR" button in the expanded drift card → shows description, patch HCL, import command, and a "View pull request →" link (or a "set GITHUB_TOKEN" hint).
- Hard rules honored: never auto-merge/apply/destroy; PR is the gate; endpoint returns patch even without a token. Tests: **111 pass + 7 skipped** (added `test_remediator.py`, `test_github_pr.py`, remediate endpoint tests); all prior 91 still green. Frontend builds clean.

## Sprint 6 — Goal 1: dashboard redesign
- Modern dark SaaS look (Datadog/Linear feel). **No new libraries** — still React + TS + Tailwind + Recharts + Axios. `tsc` strict + vite build clean.
- **Inter** loaded in `index.html` only; resource addresses/IDs in `font-mono`.
- **Header** (`App.tsx`): name left, right-aligned actions, "Updated Nm ago" with a pulse dot that animates while auto-refreshing; sticky/backdrop-blur top bar.
- **Summary cards**: label above a large number, colour only on the number, subtle left-border accent per risk; Total card neutral.
- **Drift table → expandable mini-cards** (`DriftTable.tsx`): mono-bold address, drift-type pill (colored dot), `desired → actual` arrow, fixed-width risk pill, relative time (absolute on hover). Click a row to expand → full details grid + **inline AI explanation** fetched lazily from `GET /api/drift/{id}/explain` with a loading state. (Fix button + PR link slot reserved for Goal 2.)
- **Bar chart**: taller (300px), per-drift-type bar colors via `Cell`, axis labels ("Drift type"/"Events"), rounded bars.
- `theme.ts` gained per-type hues, `relativeTime`/`absoluteTime`, and risk text/border helpers; `client.ts` gained `explainDrift(id)`. API proxy/wiring unchanged.

## Earlier sprints (one-liners)
- **S1** — three-way diff engine, drift classifier, AWS provider, normalization.
- **S2** — FastAPI + Postgres + Docker Compose; `DriftEvent` persistence + scraper.
- **S3** — React/TS dashboard; live reconciliation; Simulate/Restore.
- **S4** — `engine/resolver/` expands `count`/`for_each` → indexed addresses, wired into the pipeline via `resolve_hcl`.
- **S5** — OPA policy engine (`policies/rules.rego`, Python fallback) + Groq explainer (`GET /drift/{id}/explain`, Redis cache) + Slack alerts; all optional, default-disabled, read `os.environ`.

## Pipeline
```
resolve_hcl ─┐  (expands count/for_each)
parse_tfstate ─┤→ normalize → reconcile → classify → score(OPA→Python) → drift_events (DB) → /api → dashboard
AWSProvider ─┘                                                            └→ Slack alert (new Critical/High)
                                                          GET /drift/{id}/explain → Groq (cached in Redis)
```

## API (`/api`)
`GET /health` · `GET /drift` · `GET /drift/summary` · `GET /drift/{id}/explain` · `POST /drift/{id}/remediate` · `POST /drift/simulate` · `POST /drift/restore` · `/metrics`

## Drift Matrix
| Desired | Recorded | Actual | → |
|---------|----------|--------|---|
| Same | Same | Different | Infrastructure Drift |
| Same | Different | Different | State Drift |
| Exists | Exists | Missing | Configuration Drift |
| Missing | Missing | Exists | Ownership Drift |

## Run
```bash
python -m pytest                        # 111 pass + 7 skipped (Rego tests need the opa binary)
python main.py                          # CLI, live AWS (ap-south-1)
DRIFTWATCH_OFFLINE=1 python main.py     # CLI, demo fixture
cd docker && cp ../.env.example ../.env && docker compose up   # 9 services
# api :8000  frontend :3000  postgres :5432  redis :6379  opa :8181
# prometheus :9090  grafana :3001  pgadmin :5050  + scraper
```

## Status
- ✅ Optional/fail-safe: OPA/Groq/Slack default to disabled; tests/CLI never hit the network.
- ✅ Tests assert ID **shape/format only** (`i-`, `sg-`, `ami-`) — no real AWS IDs; clean-checkout safe.
- Stack: Python · FastAPI · SQLAlchemy/alembic · Postgres · Redis · OPA · APScheduler · React/TS/Tailwind/Recharts · Docker Compose.
- Not yet verified: `docker compose up` end-to-end (no Docker CLI in build env).
- Next: **Sprint 7** — polish, README, architecture diagram, demo GIF, resume bullets.
