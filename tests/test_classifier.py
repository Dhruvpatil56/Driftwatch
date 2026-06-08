"""Tests for the Drift Matrix classifier."""

from engine.classifier.classifier import classify_presence, classify_value
from models.drift import (
    CONFIGURATION_DRIFT,
    INFRASTRUCTURE_DRIFT,
    OWNERSHIP_DRIFT,
    STATE_DRIFT,
)


# --- presence-based rows ---------------------------------------------------
def test_ownership_drift_when_only_actual_exists():
    assert classify_presence(False, False, True) == OWNERSHIP_DRIFT


def test_configuration_drift_when_actual_missing():
    assert classify_presence(True, True, False) == CONFIGURATION_DRIFT


def test_no_presence_drift_when_all_exist():
    assert classify_presence(True, True, True) is None


def test_no_presence_drift_for_planned_but_unapplied():
    # desired only (not yet created) is not drift in Sprint 1
    assert classify_presence(True, False, False) is None


# --- value-based rows ------------------------------------------------------
def test_no_value_drift_when_all_equal():
    assert classify_value("t3.micro", "t3.micro", "t3.micro") is None


def test_infrastructure_drift_when_actual_diverges_from_agreed_state():
    # desired == recorded, actual changed out of band
    assert classify_value("t3.micro", "t3.micro", "m5.large") == INFRASTRUCTURE_DRIFT


def test_state_drift_when_state_file_is_stale():
    # desired != recorded and recorded != actual -> state lags reality
    assert classify_value("t3.micro", "t3.small", "m5.large") == STATE_DRIFT


def test_state_drift_when_actual_matches_desired_but_not_recorded():
    assert classify_value("t3.micro", "t3.small", "t3.micro") == STATE_DRIFT


def test_no_drift_when_change_only_in_hcl():
    # desired changed but recorded == actual -> not yet applied, not drift
    assert classify_value("t3.large", "t3.micro", "t3.micro") is None
