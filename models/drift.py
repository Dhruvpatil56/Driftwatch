"""Drift result model and the drift taxonomy constants."""

from __future__ import annotations

from pydantic import BaseModel

# --- Drift taxonomy (the 5 types) ------------------------------------------
CONFIGURATION_DRIFT = "Configuration Drift"    # attribute modified / resource gone out of band
INFRASTRUCTURE_DRIFT = "Infrastructure Drift"  # resource type/size changed
OWNERSHIP_DRIFT = "Ownership Drift"            # exists in cloud, not in Terraform
STATE_DRIFT = "State Drift"                    # state file outdated vs actual
POLICY_DRIFT = "Policy Drift"                  # violates governance rules

# Sentinel used internally when three-way comparison finds no divergence.
NO_DRIFT = "No Drift"

DRIFT_TYPES = frozenset(
    {
        CONFIGURATION_DRIFT,
        INFRASTRUCTURE_DRIFT,
        OWNERSHIP_DRIFT,
        STATE_DRIFT,
        POLICY_DRIFT,
    }
)


class DriftResult(BaseModel):
    """A single drift finding for one field of one resource."""

    resource_address: str
    drift_type: str
    field: str
    desired: str
    recorded: str
    actual: str
    cost_impact: str = "Unknown"
    risk_impact: str = "Low"
    governance_impact: str = "None"
