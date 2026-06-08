"""Tests for the pydantic models."""

from models.drift import DriftResult, INFRASTRUCTURE_DRIFT
from models.normalized import DESIRED, NormalizedResource


def test_normalized_resource_defaults():
    r = NormalizedResource(
        resource_address="aws_instance.web",
        resource_type="aws_instance",
        source=DESIRED,
    )
    assert r.cloud_id is None
    assert r.attributes == {}
    assert r.get("instance_type") is None
    assert r.get("instance_type", "t3.micro") == "t3.micro"


def test_normalized_resource_get_reads_attributes():
    r = NormalizedResource(
        resource_address="aws_instance.web",
        resource_type="aws_instance",
        attributes={"instance_type": "t3.micro"},
        source=DESIRED,
    )
    assert r.get("instance_type") == "t3.micro"


def test_drift_result_defaults():
    d = DriftResult(
        resource_address="aws_instance.web",
        drift_type=INFRASTRUCTURE_DRIFT,
        field="instance_type",
        desired="t3.micro",
        recorded="t3.micro",
        actual="m5.large",
    )
    assert d.cost_impact == "Unknown"
    assert d.risk_impact == "Low"
    assert d.governance_impact == "None"
