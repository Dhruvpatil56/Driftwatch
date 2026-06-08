# DriftWatch — Build Status

Sprint 1 (Core Engine) complete. Three-way reconciliation works for EC2, S3, SG.

## What it does
Compares 3 views of infra and classifies drift:
- **Desired** (HCL) + **Recorded** (tfstate) + **Actual** (AWS) → `DriftResult`

## Pipeline
```
parse_hcl ─┐
parse_tfstate ─┤→ normalize → reconcile (diff) → classify → score → report
AWSProvider ─┘
```

## Modules
| Path | Role |
|------|------|
| `models/` | `NormalizedResource`, `DriftResult` |
| `engine/parser/` | HCL + tfstate parsers, normalization layer |
| `engine/classifier/` | Drift Matrix (`classify_presence`, `classify_value`) |
| `engine/diff/` | three-way reconcile + cloud_id matching |
| `engine/scorer/` | cost/risk/governance impact |
| `providers/aws/` | boto3 scraper (EC2/S3/SG) |
| `providers/gcp/` | stub |
| `main.py` | orchestrates + prints report |

## Run
```bash
python main.py                 # live AWS (ap-south-1), falls back to demo on failure
DRIFTWATCH_OFFLINE=1 python main.py   # offline demo fixture
python -m pytest               # 43 tests
```

## Sample output
```
================================
aws_instance.web
Desired: t3.micro
Recorded: t3.micro
Actual: m5.large
Classification: Infrastructure Drift
Cost Impact: Unknown
Risk Impact: Low
Governance: None
================================
```

## Drift Matrix
| Desired | Recorded | Actual | → |
|---------|----------|--------|---|
| Same | Same | Different | Infrastructure Drift |
| Same | Different | Different | State Drift |
| Exists | Exists | Missing | Configuration Drift |
| Missing | Missing | Exists | Ownership Drift |

## Status
- ✅ 43 tests passing, all modules compile
- Stack: Python + boto3 + python-hcl2 + pydantic + pytest (no API/DB/frontend yet)
- Next: Sprint 4 resolver (`engine/resolver/` empty), then FastAPI/Postgres
