# DriftWatch — Claude Code Context

## What This Project Is

DriftWatch is a Terraform-aware cloud governance platform that reconciles three views of infrastructure:

1. Desired State — Terraform HCL (what should exist)
2. Recorded State — Terraform State File (what Terraform thinks exists)
3. Actual State — AWS APIs via boto3 (what actually exists)

It classifies drift into 5 types, scores impact across cost/risk/governance dimensions, and generates GitOps remediation PRs.

AWS Region: ap-south-1 (Mumbai) — clean account, zero prior resources.

---

## Sprint Status

- Sprint 1 DONE — three-way diff engine, drift classifier, AWS provider, 53 tests
- Sprint 2 DONE — FastAPI + Postgres + Docker Compose, 8 services
- Sprint 3 DONE — React dashboard, live reconciliation, Simulate/Restore buttons
- Sprint 4 CURRENT — Resource Resolver (count, for_each)
- Sprint 5 NEXT — OPA policies + Groq explanation + Slack alerts
- Sprint 6 — GitOps PR generation
- Sprint 7 — Polish + README + resume bullets

---

## What is Working Right Now

- python main.py — CLI three-way reconciliation against live AWS
- DRIFTWATCH_OFFLINE=1 python main.py — offline demo using tests/fixtures/demo.tfstate
- docker compose up — all 8 services start cleanly
- GET /api/drift — triggers fresh reconciliation via BackgroundTasks, returns stored results
- GET /api/drift/summary — drift counts by risk and type
- POST /api/drift/simulate — creates fake drift event in DB for demo
- POST /api/drift/restore — clears simulated drift
- Dashboard at :3000 — summary cards, drift table, bar chart, Simulate/Restore/Refresh buttons
- scripts/simulate_drift.sh — real AWS drift scenarios (EC2 resize, SG port 22, S3 tag)
- scripts/restore_state.sh — restores clean AWS state

---

## Current Sprint: Sprint 4 — Resource Resolver

### Problem

The engine currently only handles simple Terraform resources:
resource "aws_instance" "web" {}

It does NOT handle:
resource "aws_instance" "web" {
count = 3
} # produces aws_instance.web[0], aws_instance.web[1], aws_instance.web[2]

    resource "aws_instance" "web" {
      for_each = { prod = "t3.large", staging = "t3.micro" }
    }
    # produces aws_instance.web["prod"], aws_instance.web["staging"]

### Goal

Build engine/resolver/ as a dedicated service that maps:
Terraform resource_address → AWS resource ID

### Build Order

1. Handle simple resources (already works, verify)
2. Handle count — aws_instance.web[0], web[1], web[2]
3. Handle for_each with string keys — aws_instance.web["prod"]
4. Leave dynamic blocks for later

### Key Rules

- Resolver lives in engine/resolver/ only
- No changes to existing diff engine, classifier, or scorer
- Add tests in tests/test_resolver.py
- Use tests/fixtures/ for all test state files — never real AWS IDs

---

## Permanent Test Rules (enforced from Sprint 3)

- Tests must NEVER hardcode AWS resource IDs, instance IDs, AMI IDs, or SG IDs
- Assert shape and format only — cloud_id starts with "i-", sg starts with "sg-"
- All tests needing a state file use tests/fixtures/demo.tfstate
- Never depend on terraform-demo/terraform.tfstate which is gitignored
- All tests must pass on a clean checkout with zero AWS resources deployed

---

## Drift Taxonomy

| Type                 | Meaning                         |
| -------------------- | ------------------------------- |
| Configuration Drift  | Attribute modified out of band  |
| Infrastructure Drift | Resource type/size changed      |
| Ownership Drift      | Exists in AWS, not in Terraform |
| State Drift          | State file outdated vs actual   |
| Policy Drift         | Violates governance rules       |

---

## Drift Matrix

| Desired | Recorded  | Actual    | Classification       |
| ------- | --------- | --------- | -------------------- |
| Same    | Same      | Different | Infrastructure Drift |
| Same    | Different | Different | State Drift          |
| Exists  | Exists    | Missing   | Configuration Drift  |
| Missing | Missing   | Exists    | Ownership Drift      |

---

## Repository Structure

driftwatch/
├── api/
│ ├── main.py
│ ├── routes/drift.py
│ ├── models/db.py
│ ├── services.py
│ ├── config.py
│ └── database.py
├── scraper/
│ └── scheduler.py
├── frontend/
│ └── src/
├── engine/
│ ├── parser/
│ ├── diff/
│ ├── classifier/
│ ├── scorer/
│ └── resolver/ CURRENT SPRINT
├── providers/
│ ├── aws/
│ └── gcp/ stub only
├── models/
├── tests/
│ └── fixtures/ demo.tfstate — checked in, fake valid-format IDs
├── scripts/
│ ├── simulate_drift.sh
│ └── restore_state.sh
├── migrations/
├── terraform-demo/
├── docker/
│ ├── docker-compose.yml
│ ├── Dockerfile.api
│ └── Dockerfile.frontend
├── .env.example
├── main.py
├── requirements.txt
└── CLAUDE.md

---

## CloudProvider Interface

class CloudProvider(ABC):
@abstractmethod
def list_resources(self, resource_types: list[str]) -> list[NormalizedResource]:
pass

    @abstractmethod
    def get_resource(self, resource_id: str) -> NormalizedResource:
        pass

AWSProvider implements this fully.
GCPProvider is a stub with raise NotImplementedError.
NormalizedResource must have zero AWS-specific field names.

---

## Tech Stack

- Backend: FastAPI, APScheduler, SQLAlchemy, Alembic
- State store: Postgres + Redis
- HCL parsing: python-hcl2
- AWS SDK: boto3
- Policy engine: Python functions (MVP) -> OPA/Rego (Sprint 5)
- AI: Groq llama-3.3-70b — explanation only (Sprint 5)
- Frontend: React + TypeScript + Tailwind + Recharts
- Observability: Prometheus + Grafana
- Deployment: Docker Compose (current) -> Kind + Helm (Sprint 6+)
- CI/CD: GitHub Actions
- AWS region: ap-south-1 (Mumbai)

---

## Sprint Sequence

- Sprint 1 DONE
- Sprint 2 DONE
- Sprint 3 DONE
- Sprint 4 CURRENT — Resource Resolver (count, for_each)
- Sprint 5 — OPA/Rego policies + Groq drift explanation + Slack alerting
- Sprint 6 — GitOps PR generation (GitHub API + terraform import)
- Sprint 7 — Polish, README, architecture diagram, demo GIF, resume bullets
