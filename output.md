# DriftWatch — Build Status

**Current: Sprint 6 complete** — dashboard redesign + GitOps PR generation, plus a typography/scoring polish pass.

## Latest changes (remediator restore-to-desired fix)
- **Bug fix** (`engine/remediator/remediator.py`): Infrastructure Drift patches now restore the attribute to **`drift.desired`** (the Terraform value), not `drift.actual` (the drifted live value). E.g. `instance_type` desired `t3.micro` / actual `t3.large` → patch emits `instance_type = "t3.micro"`. Patch comment/description reworded to "restore to … (drifted to …)". Config/Ownership/State/Policy paths unchanged; still never destructive.
- Updated the test that encoded the old behavior; synced one Rego test case to the (intentional) `rules.rego` change of EC2-type-not-approved → Medium. Full suite **121 pass**.

## Earlier changes (typography + scoring fixes)
- **Typography**: Inter now applied globally (`:root`/`body` in `index.css`, not just preflight). Larger/bolder resource address (15px/600 mono white); bigger drift-type pill; `desired → actual` value white with a bold `→`; larger/bolder risk badge; expanded labels uppercase 11px/0.05em muted with 14px mono/white values; AI text 14px/1.6 muted-white; summary numbers 42px/700, labels 11px uppercase muted; section headers 16px/600 white. Build clean, no new libs.
- **Risk scoring** (`engine/scorer/scorer.py` Python fallback, now matching the Rego): SG port 22/3389 open to `0.0.0.0/0` → **Critical** (was High); Infrastructure Drift on `instance_type` → **Medium** (was Low); tag drift → **Medium** (was Low). OPA decision application confirmed correct end-to-end; both paths now agree.
- Tests updated to the new levels; full suite **121 pass** (incl. the 7 live-Rego cases). Note: `scan_and_persist` matches events by `(address, field, type, desired, actual)` — not risk — so already-stored rows keep their old `risk_impact` until re-detected.

## Sprint 6 (dashboard redesign + GitOps PRs)
- **Goal 1 — redesign**: dark SaaS look (Datadog/Linear), Inter, mono addresses, sticky header w/ "updated Nm ago" + auto-refresh pulse, summary cards (colored number + risk accent), drift table as **expandable mini-cards** with inline AI explanation (`GET /drift/{id}/explain`), taller per-type bar chart. No new libraries.
- **Goal 2 — remediation**: `engine/remediator/` → `RemediationPatch` (Infra→patch to live value, Config→restore/recreate note, Ownership→block + `terraform import`, State/Policy→None, **never destroys**); `api/github_pr.py` opens a PR off `drift-remediation` (token from env, `None` if unset/failed); `POST /drift/{id}/remediate` → `{pr_url, patch}`; "Fix via PR" button in the expanded card.

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
python -m pytest                        # 121 pass (114 + 7 Rego cases that need the opa binary)
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
