# DriftWatch — Build Status

Sprints 1–3 complete. Core engine + FastAPI/Postgres API + React dashboard.

## What it does
Reconciles 3 views of infra and classifies drift, then serves + visualizes it:
- **Desired** (HCL) + **Recorded** (tfstate) + **Actual** (AWS) → `DriftResult` → DB → dashboard

## Pipeline
```
parse_hcl ─┐
parse_tfstate ─┤→ normalize → reconcile → classify → score → drift_events (DB) → /api → dashboard
AWSProvider ─┘
```

## Modules
| Path | Role |
|------|------|
| `models/` | `NormalizedResource`, `DriftResult` |
| `engine/parser/` | HCL + tfstate parsers, normalization (incl. S3 tags) |
| `engine/classifier/` | Drift Matrix (`classify_presence`, `classify_value`) |
| `engine/diff/` | three-way reconcile + cloud_id matching |
| `engine/scorer/` | cost/risk/governance impact |
| `providers/aws/` | boto3 scraper (EC2/S3/SG) · `providers/gcp/` stub |
| `api/` | FastAPI app, SQLAlchemy `DriftEvent`, detection+persistence service |
| `scraper/` | APScheduler, scans every 15 min |
| `migrations/` | alembic (`0001_create_drift_events`) |
| `frontend/` | React+TS+Tailwind+Recharts dashboard |
| `docker/` | compose (8 services) + Dockerfiles |
| `scripts/` | `wait_for_db.py`, `simulate_drift.sh`, `restore_state.sh` |
| `main.py` | Sprint 1 CLI report |

## API (`/api`)
`GET /health` · `GET /drift` · `GET /drift/summary` · `POST /drift/simulate` · `POST /drift/restore` · `/metrics`

## Dashboard (localhost:3000)
Single dark page: summary cards (Total/Critical/High/Medium/Low), drift table (main element), bar chart by type, Simulate/Restore/Refresh buttons, 30s auto-refresh. Risk colors: Critical=red, High=orange, Medium=yellow, Low=green.

## State (real-AWS workflow)
`terraform-demo/terraform.tfstate` is **gitignored** — it holds real AWS state. The parsers + detection always read it, so a local state file is required:
```bash
cd terraform-demo && terraform init && terraform apply   # creates real infra + local state
```
`main.tf` and the parser tests pin the **real** resource IDs/AMI from that apply.

## Run
```bash
# CLI (Sprint 1)
python main.py                          # live AWS (ap-south-1)
DRIFTWATCH_OFFLINE=1 python main.py     # actual-state from demo fixture (still needs local tfstate)
python -m pytest                        # 53 tests (needs local real tfstate for ID assertions)

# Full stack
cd docker && cp ../.env.example ../.env && docker compose up   # 8 services
# api :8000  frontend :3000  postgres :5432  redis :6379
# prometheus :9090  grafana :3001  pgadmin :5050  + scraper
```

## Drift Matrix
| Desired | Recorded | Actual | → |
|---------|----------|--------|---|
| Same | Same | Different | Infrastructure Drift |
| Same | Different | Different | State Drift |
| Exists | Exists | Missing | Configuration Drift |
| Missing | Missing | Exists | Ownership Drift |

## Status
- ✅ 53 Python tests passing **with local real tfstate**; frontend builds clean (tsc strict + vite)
- Config via `.env`; AWS creds from env (never hardcoded)
- Stack: Python · FastAPI · SQLAlchemy/alembic · Postgres · APScheduler · React/TS/Tailwind/Recharts · Docker Compose
- ⚠️ No committed state fixture: clean checkout w/o local tfstate can't run parsers/detection (`test_cloud_id_comes_from_state_id` and the offline demo need it). CI would need a sanitized fixture.
- Not yet verified: `docker compose up` end-to-end (no Docker CLI in build env)
- Next: Sprint 4 resolver (count/for_each) → OPA/Groq → GitOps PRs
