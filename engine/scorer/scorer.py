"""Impact scoring.

Assigns cost / risk / governance impact to a ``DriftResult``.

As of Sprint 5 the **policy decision** is delegated to an OPA (Open Policy Agent)
sidecar evaluating ``policies/rules.rego``. The flow per finding is:

  1. Build an OPA input doc from the drift and ask OPA for a decision.
  2. If OPA returns one, apply its ``risk`` + ``governance``.
  3. If OPA is unreachable / disabled, fall back to the built-in Python rules
     (``_score_python``) — identical to the pre-Sprint-5 behaviour.

Cost impact stays ``Unknown`` (a real pricing model lands later). The diff
engine still calls ``score(drift)`` with the same signature, so nothing upstream
changed.
"""

from __future__ import annotations

from engine.scorer import opa_client
from models.drift import (
    CONFIGURATION_DRIFT,
    OWNERSHIP_DRIFT,
    DriftResult,
)

_OPEN_CIDR = "0.0.0.0/0"


def score(drift: DriftResult) -> DriftResult:
    """Populate cost/risk/governance impact on ``drift`` in place and return it."""
    drift.cost_impact = "Unknown"  # pricing model arrives in a later sprint

    decision = opa_client.evaluate(_opa_input(drift))
    if decision is not None:
        drift.risk_impact = decision.get("risk", "Low")
        drift.governance_impact = decision.get("governance", "None")
        return drift

    # OPA disabled or unreachable -> built-in Python policy rules.
    return _score_python(drift)


def score_all(drifts: list[DriftResult]) -> list[DriftResult]:
    """Score a list of drift results in place."""
    for d in drifts:
        score(d)
    return drifts


def _opa_input(drift: DriftResult) -> dict:
    """Project a ``DriftResult`` into the document the Rego policies expect."""
    return {
        "resource_address": drift.resource_address,
        "resource_type": _resource_type(drift.resource_address),
        "drift_type": drift.drift_type,
        "field": drift.field,
        "desired": drift.desired,
        "recorded": drift.recorded,
        "actual": drift.actual,
    }


def _resource_type(address: str) -> str:
    """``aws_security_group.web_sg[0]`` -> ``aws_security_group``."""
    return address.split(".", 1)[0] if address else ""


# --- built-in fallback rules (used when OPA is unavailable) -----------------
def _score_python(drift: DriftResult) -> DriftResult:
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
