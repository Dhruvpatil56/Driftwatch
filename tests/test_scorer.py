"""Tests for impact scoring."""

from engine.scorer.scorer import score, score_all
from models.drift import (
    CONFIGURATION_DRIFT,
    INFRASTRUCTURE_DRIFT,
    OWNERSHIP_DRIFT,
    DriftResult,
)


def _drift(drift_type, field="instance_type", actual="m5.large"):
    return DriftResult(
        resource_address="aws_x.y",
        drift_type=drift_type,
        field=field,
        desired="d",
        recorded="r",
        actual=actual,
    )


def test_instance_type_drift_is_low_risk_unknown_cost():
    d = score(_drift(INFRASTRUCTURE_DRIFT))
    assert d.risk_impact == "Low"
    assert d.cost_impact == "Unknown"
    assert d.governance_impact == "None"


def test_ownership_drift_is_medium_risk_with_governance_note():
    d = score(_drift(OWNERSHIP_DRIFT, field="(resource)", actual="i-123"))
    assert d.risk_impact == "Medium"
    assert "Untracked" in d.governance_impact


def test_configuration_drift_resource_deleted_is_high_risk():
    d = score(_drift(CONFIGURATION_DRIFT, field="(resource)", actual="missing"))
    assert d.risk_impact == "High"


def test_open_ingress_is_high_risk_governance_flag():
    d = score(_drift(INFRASTRUCTURE_DRIFT, field="ingress", actual="tcp:22-22:0.0.0.0/0"))
    assert d.risk_impact == "High"
    assert "0.0.0.0/0" in d.governance_impact


def test_closed_ingress_change_is_medium_risk():
    d = score(_drift(INFRASTRUCTURE_DRIFT, field="ingress", actual="tcp:22-22:10.0.0.0/8"))
    assert d.risk_impact == "Medium"
    assert d.governance_impact == "None"


def test_score_all_mutates_every_drift():
    drifts = [_drift(OWNERSHIP_DRIFT, field="(resource)"), _drift(INFRASTRUCTURE_DRIFT)]
    score_all(drifts)
    assert drifts[0].risk_impact == "Medium"
    assert drifts[1].risk_impact == "Low"
