"""Impact scoring.

Assigns cost / risk / governance impact to a ``DriftResult`` using a small,
explicit rule set. Sprint 1 keeps cost at ``Unknown`` (real pricing lands
later) and focuses on risk + governance signal, especially for security groups.
"""

from __future__ import annotations

from models.drift import (
    CONFIGURATION_DRIFT,
    OWNERSHIP_DRIFT,
    DriftResult,
)

_OPEN_CIDR = "0.0.0.0/0"


def score(drift: DriftResult) -> DriftResult:
    """Populate cost/risk/governance impact on ``drift`` in place and return it."""
    drift.cost_impact = "Unknown"  # pricing model arrives in a later sprint
    drift.risk_impact = "Low"
    drift.governance_impact = "None"

    if drift.drift_type == OWNERSHIP_DRIFT:
        drift.risk_impact = "Medium"
        drift.governance_impact = (
            "Untracked resource - exists in cloud but absent from Terraform"
        )
    elif drift.drift_type == CONFIGURATION_DRIFT:
        # Terraform-managed resource deleted out of band.
        drift.risk_impact = "High"
    elif drift.field in ("ingress", "egress"):
        if _OPEN_CIDR in str(drift.actual):
            drift.risk_impact = "High"
            drift.governance_impact = (
                f"Security group {drift.field} open to {_OPEN_CIDR}"
            )
        else:
            drift.risk_impact = "Medium"

    return drift


def score_all(drifts: list[DriftResult]) -> list[DriftResult]:
    """Score a list of drift results in place."""
    for d in drifts:
        score(d)
    return drifts
