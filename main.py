"""DriftWatch Sprint 1 entry point.

Runs the three-way reconciliation over the demo infrastructure:

    desired (HCL)  +  recorded (tfstate)  +  actual (AWS)  ->  drift report

Actual state comes from live AWS via ``AWSProvider``. When AWS is unreachable
(no credentials, offline, or ``DRIFTWATCH_OFFLINE=1``), it falls back to the
committed ``actual-state.demo.json`` fixture so the pipeline always produces
output you can eyeball.
"""

from __future__ import annotations

import json
import os
import sys

from engine.diff import reconcile
from engine.parser import parse_hcl, parse_tfstate
from models.drift import DriftResult
from models.normalized import NormalizedResource
from providers.aws import AWSProvider, build_actual

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_DIR = os.path.join(HERE, "terraform-demo")
HCL_PATH = DEMO_DIR
STATE_PATH = os.path.join(DEMO_DIR, "terraform.tfstate")
DEMO_ACTUAL_PATH = os.path.join(DEMO_DIR, "actual-state.demo.json")

RESOURCE_TYPES = ["aws_instance", "aws_s3_bucket", "aws_security_group"]
REGION = "ap-south-1"

SEP = "=" * 32


def load_actual_from_demo(path: str) -> list[NormalizedResource]:
    """Build actual resources from the offline AWS-shaped fixture."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    resources: list[NormalizedResource] = []
    for resource_type in RESOURCE_TYPES:
        for raw in data.get(resource_type, []):
            resources.append(build_actual(resource_type, raw))
    return resources


def get_actual() -> tuple[list[NormalizedResource], str]:
    """Return (actual resources, mode) — live AWS if possible, else demo."""
    if os.environ.get("DRIFTWATCH_OFFLINE") == "1":
        return load_actual_from_demo(DEMO_ACTUAL_PATH), "offline (DRIFTWATCH_OFFLINE=1)"
    try:
        provider = AWSProvider(region=REGION)
        actual = provider.list_resources(RESOURCE_TYPES)
        return actual, f"live AWS ({REGION})"
    except Exception as exc:  # noqa: BLE001 — any AWS failure falls back to demo
        print(f"[warn] live AWS scrape failed ({type(exc).__name__}: {exc});"
              " falling back to offline demo fixture.\n")
        return load_actual_from_demo(DEMO_ACTUAL_PATH), "offline demo fixture"


def print_drift(d: DriftResult) -> None:
    print(SEP)
    print(d.resource_address)
    print(f"Desired: {d.desired}")
    print(f"Recorded: {d.recorded}")
    print(f"Actual: {d.actual}")
    print(f"Classification: {d.drift_type}")
    print(f"Cost Impact: {d.cost_impact}")
    print(f"Risk Impact: {d.risk_impact}")
    print(f"Governance: {d.governance_impact}")
    print(SEP)


def main() -> int:
    desired = parse_hcl(HCL_PATH)
    recorded = parse_tfstate(STATE_PATH)
    actual, mode = get_actual()

    print(f"DriftWatch - three-way reconciliation (actual source: {mode})")
    print(f"desired={len(desired)} recorded={len(recorded)} actual={len(actual)}\n")

    drifts = reconcile(desired, recorded, actual)

    if not drifts:
        print("No drift detected. Infrastructure is in sync.")
        return 0

    for d in drifts:
        print_drift(d)

    print(f"\n{len(drifts)} drift(s) detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
