# DriftWatch

Terraform-aware infrastructure drift detection for AWS.

[![CI](https://github.com/Dhruvpatil56/Driftwatch/actions/workflows/ci.yml/badge.svg)](https://github.com/Dhruvpatil56/Driftwatch/actions/workflows/ci.yml)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

## What it does

DriftWatch reconciles three views of AWS infrastructure: the desired state in Terraform HCL, the recorded state in the Terraform state file, and the actual state from the AWS APIs. It classifies every divergence into one of five drift types and scores risk through an OPA/Rego policy engine with a Python fallback. DriftWatch explains each finding in plain English with a Groq LLM and can open a GitOps remediation pull request for human review.

## Architecture

```
 Terraform HCL ──► resolve_hcl ─┐
 Terraform state ─► parse ──────┤
 AWS API ─────────► scrape ─────┘
                                ▼
                            normalize
                                ▼
                          reconcile (three-way)
                                ▼
                            classify
                                ▼
                       score (OPA ──► Python fallback)
                                ▼
                       drift_events (Postgres)
                                ▼
                               API ───────────────► React dashboard
                                ├──► Groq explanation (cached in Redis)   GET  /drift/{id}/explain
                                ├──► Slack alert (Critical / High)
                                └──► GitOps PR (GitHub API)               POST /drift/{id}/remediate
```

## Features

- Three-way drift reconciliation (HCL vs state vs AWS)
- Five drift types: Configuration, Infrastructure, Ownership, State, Policy
- OPA/Rego policy engine with Python fallback
- Groq LLM drift explanation (2 sentences, cached in Redis)
- Slack alerts for Critical/High drift
- GitOps PR generation via GitHub API
- React dashboard with expandable drift cards
- Resource Resolver for `count` and `for_each` Terraform meta-arguments
- 114 tests, CI via GitHub Actions

## Tech stack

| Backend | Frontend |
| --- | --- |
| FastAPI, SQLAlchemy, Alembic, APScheduler, boto3, python-hcl2, Pydantic | React, TypeScript, Tailwind, Recharts, Axios, Vite |

| Infrastructure | Observability |
| --- | --- |
| Docker Compose, Postgres, Redis, OPA/Rego, Groq | Prometheus, Grafana, GitHub Actions |

## Quick start

```bash
git clone https://github.com/Dhruvpatil56/Driftwatch.git
cd Driftwatch
cd docker && cp ../.env.example ../.env
docker compose up
```

Then open http://localhost:3000. The default `.env` runs offline against the committed demo fixture, so no AWS credentials are required.

## Demo scenarios

- EC2 instance type changed out of band (t3.micro to t3.small) — Infrastructure Drift
- Security group opened to 0.0.0.0/0 on port 22 — scored Critical by the policy engine
- S3 bucket given a rogue `Environment` tag — tag drift
- EC2 instance live in AWS but absent from Terraform — Ownership Drift

## Project structure

```
api/            FastAPI app: routes, services, persistence, GitHub PR + Slack
engine/         parser, resolver, diff, classifier, scorer, explainer, remediator
providers/      AWS provider (boto3); GCP stub
models/         NormalizedResource, DriftResult, RemediationPatch
policies/       OPA/Rego governance rules
frontend/       React + TypeScript dashboard
scraper/        APScheduler background drift scans
tests/          pytest suite and fixtures
docker/         Docker Compose stack and Dockerfiles
terraform-demo/ sample Terraform and demo state
scripts/        drift simulate/restore helpers
migrations/     Alembic database migrations
```

## License

DriftWatch is released under the MIT License.
