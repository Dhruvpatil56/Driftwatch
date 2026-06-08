# DriftWatch — Claude Code Context

## What This Project Is

DriftWatch is a Terraform-aware cloud governance platform that reconciles three views of infrastructure:

1. Desired State — Terraform HCL (what should exist)
2. Recorded State — Terraform State File (what Terraform thinks exists)
3. Actual State — AWS APIs via boto3 (what actually exists)

It classifies drift into 5 types, scores impact across cost/risk/governance dimensions, and eventually generates GitOps remediation PRs.

AWS Region: ap-south-1 (Mumbai) — clean account, zero prior resources.

---

## Current Sprint: Sprint 1 — Core Engine Only

### Goal

Prove the three-way reconciliation works for EC2, S3, and Security Group.
Output of python main.py should look like:

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

### Scope — ONLY these, nothing else

- Parse HCL -> DesiredResource
- Parse .tfstate -> RecordedResource
- AWS boto3 scraper for EC2, S3, Security Group -> ActualResource
- NormalizedResource model (cloud-agnostic)
- Three-way diff engine -> DriftResult
- Drift classifier using the Drift Matrix

### Hard Rules for This Sprint

- No FastAPI
- No frontend
- No Redis
- No Docker Compose
- No Grafana
- No AI/Groq
- No OPA
- No database
- Just Python + boto3 + python-hcl2 + pydantic + pytest

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

## Drift Matrix (core classification logic)

| Desired | Recorded  | Actual    | Classification       |
| ------- | --------- | --------- | -------------------- |
| Same    | Same      | Different | Infrastructure Drift |
| Same    | Different | Different | State Drift          |
| Exists  | Exists    | Missing   | Configuration Drift  |
| Missing | Missing   | Exists    | Ownership Drift      |

---

## Repository Structure

driftwatch/
├── engine/
│ ├── parser/ HCL + tfstate parsers
│ ├── diff/ three-way diff engine
│ ├── classifier/ drift type classification
│ ├── scorer/ cost/risk/governance scoring
│ └── resolver/ tf address -> AWS resource ID (Sprint 4)
├── providers/
│ ├── aws/ AWSProvider (boto3)
│ └── gcp/ GCPProvider (stub only)
├── models/ all pydantic models
├── tests/
├── terraform-demo/ demo infra: EC2 + SG + S3 in ap-south-1
├── docker/
├── docs/
├── main.py
├── CLAUDE.md
└── requirements.txt

---

## Key Models

NormalizedResource:
resource_address: str e.g. "aws_instance.web"
resource_type: str e.g. "aws_instance"
cloud_id: str or None e.g. "i-12345" (None if from HCL)
attributes: dict e.g. {"instance_type": "t3.micro"}
source: str "desired" | "recorded" | "actual"

DriftResult:
resource_address: str
drift_type: str one of the 5 drift types
field: str which attribute drifted
desired: str
recorded: str
actual: str
cost_impact: str "Unknown" | "$X/month"
risk_impact: str "Low" | "Medium" | "High" | "Critical"
governance_impact: str "None" | description

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

## AWS Demo Infrastructure (terraform-demo/)

Three resources only:

- aws_instance (t3.micro)
- aws_security_group
- aws_s3_bucket
  Region: ap-south-1

---

## Tech Stack (Sprint 1)

- Python 3.11+
- python-hcl2
- boto3
- pydantic
- pytest

---

## Sprint Sequence

- Sprint 1 — Core engine: parse + scrape + diff + classify (CURRENT)
- Sprint 2 — NormalizedResource model, full normalization pipeline
- Sprint 3 — Three-way diff engine + Drift Matrix classification
- Sprint 4 — Resource Resolver (count, for_each)
- Sprint 5 — FastAPI wrapper, Postgres, Docker Compose
- Sprint 6 — React dashboard
- Sprint 7 — OPA policies, Groq explanation, alerting
- Sprint 8 — GitOps PR generation
