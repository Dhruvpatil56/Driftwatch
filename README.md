# 🌊 DriftWatch

**Terraform-aware cloud governance that catches infrastructure drift before it bites.**

DriftWatch reconciles three views of your infrastructure and tells you exactly where — and why — they disagree:

| View | Source | Question it answers |
|------|--------|---------------------|
| 🎯 **Desired** | Terraform HCL | What *should* exist |
| 📒 **Recorded** | Terraform state | What Terraform *thinks* exists |
| ☁️ **Actual** | AWS API (boto3) | What *actually* exists |

---

## ✨ What it does

Three-way diff → classify drift → score impact.

```
parse HCL ─┐
parse state ┤→ normalize → diff → classify → score → report
scrape AWS ─┘
```

Every resource is funnelled into a cloud-agnostic `NormalizedResource`, so the engine never sees a provider-specific shape.

## 🧭 Drift Matrix

| Desired | Recorded | Actual | Classification |
|---------|----------|--------|----------------|
| Same | Same | Different | **Infrastructure Drift** |
| Same | Different | Different | **State Drift** |
| Exists | Exists | Missing | **Configuration Drift** |
| Missing | Missing | Exists | **Ownership Drift** |

## 🚀 Quick start

```bash
pip install -r requirements.txt

python main.py                       # live AWS (ap-south-1)
DRIFTWATCH_OFFLINE=1 python main.py  # offline demo, no creds needed
python -m pytest                     # run the suite
```

## 🔎 Sample output

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

## 🧱 Stack

Python 3.11+ · boto3 · python-hcl2 · pydantic · pytest

> **Status:** Sprint 1 — core engine (EC2 / S3 / Security Group). FastAPI, dashboard, OPA policies, and GitOps remediation are on the roadmap.
