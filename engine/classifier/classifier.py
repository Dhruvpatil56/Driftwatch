"""Drift classification — the Drift Matrix.

Two kinds of comparison feed the matrix:

1. **Presence** — does the resource exist in each of the three views?
2. **Value** — for a resource present everywhere, does a given attribute agree?

Drift Matrix (from CLAUDE.md):

    | Desired | Recorded  | Actual    | Classification       |
    | ------- | --------- | --------- | -------------------- |
    | Same    | Same      | Different | Infrastructure Drift |
    | Same    | Different | Different | State Drift          |
    | Exists  | Exists    | Missing   | Configuration Drift  |
    | Missing | Missing   | Exists    | Ownership Drift      |

``None`` means "no drift on this dimension".
"""

from __future__ import annotations

from typing import Any

from models.drift import (
    CONFIGURATION_DRIFT,
    INFRASTRUCTURE_DRIFT,
    OWNERSHIP_DRIFT,
    STATE_DRIFT,
)


def classify_presence(
    desired_exists: bool, recorded_exists: bool, actual_exists: bool
) -> str | None:
    """Classify drift from the presence pattern across the three views."""
    # Lives in the cloud but Terraform has never heard of it.
    if not desired_exists and not recorded_exists and actual_exists:
        return OWNERSHIP_DRIFT
    # Terraform wants & records it, but it's gone from the cloud (deleted
    # out of band).
    if desired_exists and recorded_exists and not actual_exists:
        return CONFIGURATION_DRIFT
    return None


def classify_value(desired: Any, recorded: Any, actual: Any) -> str | None:
    """Classify drift for one attribute whose value is known in all three
    views."""
    if desired == recorded == actual:
        return None
    # Terraform's intent and record agree, but reality diverged -> the resource
    # was changed out of band.
    if desired == recorded and actual != recorded:
        return INFRASTRUCTURE_DRIFT
    # The state file disagrees with reality -> Terraform's record is stale.
    if recorded != actual and desired != recorded:
        return STATE_DRIFT
    # Remaining case: desired != recorded but recorded == actual. The change
    # exists only in HCL and hasn't been applied yet -> not drift.
    return None
