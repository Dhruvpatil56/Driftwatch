# DriftWatch — Build Status

**Current: Sprint 5 complete** — OPA policy engine + Groq drift explanations + Slack alerting.

## Latest changes (Sprint 5)
- **OPA policy engine** — `engine/scorer/score()` POSTs each drift to the OPA sidecar (`/v1/data/driftwatch/policies/decision`, port 8181) and applies `{risk, governance}`. `OPA_URL` unset → disabled (no network); unreachable → **Python scorer fallback** (original rules preserved). Verified end-to-end against real OPA 1.17.1.
- **Policies** (`policies/rules.rego`) — SG `0.0.0.0/0` :22→Critical · :3389→Critical · S3 missing required tag→Medium · EC2 type not approved→High · Ownership Drift→Medium. Highest severity wins.
- **Groq explainer** (`engine/explainer/`) — `GET /api/drift/{id}/explain` → plain-English what/why/cause via `llama-3.3-70b-versatile`. No `GROQ_API_KEY` → deterministic local fallback. Cached in Redis by drift identity; cache failure non-fatal. **AI = explanation only.**
- **Slack alerts** (`api/notifications.py`) — new Critical/High drift in `scan_and_persist` → webhook (resource, type, risk, one-line Groq explanation). `SLACK_WEBHOOK_URL` unset → skipped silently; send errors swallowed.
- Engine/notifier read config from `os.environ` (decoupled; tests default to **disabled**, never hit network). New env: `OPA_URL`, `REDIS_URL`, `GROQ_API_KEY`, `GROQ_MODEL`, `SLACK_WEBHOOK_URL`. Docker adds the `opa` sidecar (now 9 services).
- Tests: **91 pass + 7 skipped** (Rego cases need the `opa` binary; pass when present). Diff engine + classifier untouched.

## Earlier sprints (one-liners)
- **S1** — three-way diff engine, drift classifier, AWS provider, normalization.
- **S2** — FastAPI + Postgres + Docker Compose; `DriftEvent` persistence + scraper.
- **S3** — React/TS dashboard; live reconciliation; Simulate/Restore.
- **S4** — `engine/resolver/` expands `count`/`for_each` → indexed addresses (`web[0]`, `web["prod"]`), wired into the live pipeline via `resolve_hcl`.

## Pipeline
```
resolve_hcl ─┐  (expands count/for_each)
parse_tfstate ─┤→ normalize → reconcile → classify → score(OPA→Python) → drift_events (DB) → /api → dashboard
AWSProvider ─┘                                                            └→ Slack alert (new Critical/High)
                                                          GET /drift/{id}/explain → Groq (cached in Redis)
```

## API (`/api`)
`GET /health` · `GET /drift` · `GET /drift/summary` · `GET /drift/{id}/explain` · `POST /drift/simulate` · `POST /drift/restore` · `/metrics`

## Drift Matrix
| Desired | Recorded | Actual | → |
|---------|----------|--------|---|
| Same | Same | Different | Infrastructure Drift |
| Same | Different | Different | State Drift |
| Exists | Exists | Missing | Configuration Drift |
| Missing | Missing | Exists | Ownership Drift |

## Run
```bash
python -m pytest                        # 91 pass + 7 skipped (Rego tests need the opa binary)
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
- Next: **Sprint 6** — GitOps PR generation (GitHub API + terraform import).
