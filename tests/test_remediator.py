"""Tests for the drift remediator (Sprint 6, Goal 2).

Verifies the non-destructive patch generation per drift type. No network — the
remediator is pure. The cardinal rule: never emit a destroy operation.
"""

import pytest

from engine.remediator import remediate
from engine.remediator.remediator import _hcl_value, _split_address
from models.drift import (
    CONFIGURATION_DRIFT,
    INFRASTRUCTURE_DRIFT,
    OWNERSHIP_DRIFT,
    POLICY_DRIFT,
    STATE_DRIFT,
    DriftResult,
)


def _drift(**kw):
    base = dict(
        resource_address="aws_instance.web",
        drift_type=INFRASTRUCTURE_DRIFT,
        field="instance_type",
        desired="t3.micro",
        recorded="t3.micro",
        actual="m5.large",
        risk_impact="High",
    )
    base.update(kw)
    return DriftResult(**base)


# --- Infrastructure Drift ---------------------------------------------------
def test_infrastructure_drift_patches_attribute_to_desired():
    # Restore to the desired (Terraform) value, NOT the drifted live value.
    patch = remediate(_drift())  # desired t3.micro, actual m5.large
    assert patch is not None
    assert patch.resource_address == "aws_instance.web"
    assert 'resource "aws_instance" "web"' in patch.patch_hcl
    assert 'instance_type = "t3.micro"' in patch.patch_hcl  # desired value
    assert 'instance_type = "m5.large"' not in patch.patch_hcl  # never the drift
    assert patch.import_command is None
    assert "t3.micro" in patch.description


def test_infrastructure_drift_indexed_address_strips_index_in_block():
    patch = remediate(_drift(resource_address="aws_instance.web[0]"))
    assert patch is not None
    # Block is declared once (no index); address preserved on the patch.
    assert 'resource "aws_instance" "web"' in patch.patch_hcl
    assert patch.resource_address == "aws_instance.web[0]"


# --- Ownership Drift --------------------------------------------------------
def test_ownership_drift_emits_import_command_and_new_block():
    patch = remediate(
        _drift(
            resource_address="aws_instance.unmanaged",
            drift_type=OWNERSHIP_DRIFT,
            field="(resource)",
            desired="absent",
            recorded="absent",
            actual="i-0orphan99999999",
        )
    )
    assert patch is not None
    assert patch.import_command == (
        "terraform import aws_instance.unmanaged i-0orphan99999999"
    )
    assert 'resource "aws_instance" "unmanaged"' in patch.patch_hcl


# --- Configuration Drift ----------------------------------------------------
def test_configuration_drift_resource_level_never_destroys():
    patch = remediate(
        _drift(
            drift_type=CONFIGURATION_DRIFT,
            field="(resource)",
            desired="present",
            recorded="present",
            actual="missing",
        )
    )
    assert patch is not None
    assert patch.import_command is None
    assert "apply" in patch.description.lower()


def test_configuration_drift_attribute_level_restores_desired():
    patch = remediate(
        _drift(
            drift_type=CONFIGURATION_DRIFT,
            field="instance_type",
            desired="t3.micro",
            actual="t3.small",
        )
    )
    assert patch is not None
    assert 'instance_type = "t3.micro"' in patch.patch_hcl  # restores desired


# --- out of scope -----------------------------------------------------------
def test_state_drift_returns_none():
    assert remediate(_drift(drift_type=STATE_DRIFT)) is None


def test_policy_drift_returns_none():
    assert remediate(_drift(drift_type=POLICY_DRIFT)) is None


# --- the cardinal rule ------------------------------------------------------
@pytest.mark.parametrize(
    "drift",
    [
        _drift(),
        _drift(drift_type=OWNERSHIP_DRIFT, field="(resource)", actual="i-1"),
        _drift(drift_type=CONFIGURATION_DRIFT, field="(resource)", actual="missing"),
        _drift(drift_type=CONFIGURATION_DRIFT, field="instance_type"),
    ],
)
def test_no_patch_ever_destroys(drift):
    patch = remediate(drift)
    assert patch is not None
    blob = f"{patch.patch_hcl}\n{patch.import_command}\n{patch.description}".lower()
    # No destructive *operation* is ever emitted (reassuring prose is fine).
    assert "terraform destroy" not in blob
    assert "destroy = true" not in blob
    assert "-destroy" not in blob
    assert "terraform delete" not in blob


# --- helpers ----------------------------------------------------------------
def test_split_address():
    assert _split_address("aws_instance.web") == ("aws_instance", "web")
    assert _split_address("aws_instance.web[0]") == ("aws_instance", "web")
    assert _split_address('aws_instance.env["prod"]') == ("aws_instance", "env")


def test_hcl_value_quoting():
    assert _hcl_value("m5.large") == '"m5.large"'
    assert _hcl_value("3") == "3"
    assert _hcl_value("true") == "true"
    assert _hcl_value(None) == '""'
