"""Tests for the OPA policy engine and the Python fallback (Sprint 5).

Two layers are covered:
  * The scorer/opa_client integration — without a live OPA, scoring must fall
    back to the built-in Python rules; with a (mocked) OPA decision it must be
    applied verbatim. No real network is used.
  * The Rego policies themselves — run against the real ``opa`` binary when it
    is installed (skipped otherwise, e.g. local dev without OPA; runs in CI).
"""

import json
import os
import shutil
import subprocess

import httpx
import pytest

from engine.scorer import opa_client, scorer
from engine.scorer.scorer import score
from models.drift import INFRASTRUCTURE_DRIFT, OWNERSHIP_DRIFT, DriftResult

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "policies", "rules.rego")
OPA_BIN = shutil.which("opa")


def _drift(**kw):
    base = dict(
        resource_address="aws_instance.web",
        drift_type=INFRASTRUCTURE_DRIFT,
        field="instance_type",
        desired="t3.micro",
        recorded="t3.micro",
        actual="m5.large",
    )
    base.update(kw)
    return DriftResult(**base)


@pytest.fixture(autouse=True)
def _opa_disabled(monkeypatch):
    # Default state for every test: OPA off + memo cleared, so behaviour is
    # deterministic and no socket is opened unless a test opts in.
    monkeypatch.delenv("OPA_URL", raising=False)
    opa_client.reset()
    yield
    opa_client.reset()


# --- scorer integration ----------------------------------------------------
def test_python_fallback_when_opa_disabled():
    d = score(_drift(drift_type=OWNERSHIP_DRIFT, field="(resource)", actual="i-1"))
    assert d.risk_impact == "Medium"
    assert "Untracked" in d.governance_impact


def test_opa_decision_is_applied(monkeypatch):
    monkeypatch.setattr(
        opa_client,
        "evaluate",
        lambda doc: {"risk": "Critical", "governance": "SSH (port 22) open"},
    )
    d = score(_drift(field="ingress", actual="tcp:22-22:0.0.0.0/0"))
    assert d.risk_impact == "Critical"
    assert "SSH" in d.governance_impact
    assert d.cost_impact == "Unknown"  # cost is never OPA's job


def test_unreachable_opa_falls_back_to_python(monkeypatch):
    monkeypatch.setenv("OPA_URL", "http://opa:8181")
    opa_client.reset()

    def boom(*a, **k):
        raise httpx.ConnectError("sidecar down")

    monkeypatch.setattr(httpx, "post", boom)
    # SSH open to the world -> Python fallback rule = Critical
    d = score(_drift(field="ingress", actual="tcp:22-22:0.0.0.0/0"))
    assert d.risk_impact == "Critical"
    assert "0.0.0.0/0" in d.governance_impact


def test_opa_input_derives_resource_type_from_address():
    doc = scorer._opa_input(
        _drift(resource_address="aws_security_group.web_sg[0]", field="ingress")
    )
    assert doc["resource_type"] == "aws_security_group"
    assert doc["field"] == "ingress"
    assert doc["drift_type"] == INFRASTRUCTURE_DRIFT


# --- opa_client behaviour ---------------------------------------------------
class _FakeResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_evaluate_disabled_makes_no_request(monkeypatch):
    monkeypatch.delenv("OPA_URL", raising=False)
    opa_client.reset()

    def fail(*a, **k):
        raise AssertionError("must not call OPA when OPA_URL is unset")

    monkeypatch.setattr(httpx, "post", fail)
    assert opa_client.evaluate({"field": "instance_type"}) is None


def test_evaluate_returns_decision(monkeypatch):
    monkeypatch.setenv("OPA_URL", "http://opa:8181")
    opa_client.reset()
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: _FakeResp({"result": {"risk": "High", "governance": "x"}}),
    )
    assert opa_client.evaluate({"field": "instance_type"}) == {
        "risk": "High",
        "governance": "x",
    }


def test_evaluate_none_when_result_malformed(monkeypatch):
    monkeypatch.setenv("OPA_URL", "http://opa:8181")
    opa_client.reset()
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResp({}))
    assert opa_client.evaluate({}) is None


def test_connection_error_memoized(monkeypatch):
    monkeypatch.setenv("OPA_URL", "http://opa:8181")
    opa_client.reset()
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", boom)
    assert opa_client.evaluate({}) is None
    assert opa_client.evaluate({}) is None  # second call short-circuits
    assert calls["n"] == 1


# --- real Rego policies (requires the opa binary) ---------------------------
def _opa_decision(input_doc: dict) -> dict:
    proc = subprocess.run(
        [OPA_BIN, "eval", "-f", "json", "-d", RULES, "-I", "data.driftwatch.policies.decision"],
        input=json.dumps(input_doc),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["result"][0]["expressions"][0]["value"]


_REGO_CASES = [
    # SSH open to the world -> Critical
    (
        {"resource_type": "aws_security_group", "drift_type": "Infrastructure Drift",
         "field": "ingress", "actual": "tcp:22-22:0.0.0.0/0", "resource_address": "aws_security_group.web"},
        "Critical",
    ),
    # RDP open to the world -> Critical
    (
        {"resource_type": "aws_security_group", "drift_type": "Infrastructure Drift",
         "field": "ingress", "actual": "tcp:3389-3389:0.0.0.0/0", "resource_address": "aws_security_group.win"},
        "Critical",
    ),
    # SG change that is NOT open to the world -> Low
    (
        {"resource_type": "aws_security_group", "drift_type": "Infrastructure Drift",
         "field": "ingress", "actual": "tcp:22-22:10.0.0.0/8", "resource_address": "aws_security_group.web"},
        "Low",
    ),
    # S3 bucket missing a required tag -> Medium
    (
        {"resource_type": "aws_s3_bucket", "drift_type": "Configuration Drift",
         "field": "tags", "actual": "{'Name': 'data'}", "resource_address": "aws_s3_bucket.data"},
        "Medium",
    ),
    # EC2 type not in the approved list -> Medium
    (
        {"resource_type": "aws_instance", "drift_type": "Infrastructure Drift",
         "field": "instance_type", "actual": "m5.large", "resource_address": "aws_instance.web"},
        "Medium",
    ),
    # EC2 type that IS approved -> Low
    (
        {"resource_type": "aws_instance", "drift_type": "Infrastructure Drift",
         "field": "instance_type", "actual": "t3.micro", "resource_address": "aws_instance.web"},
        "Low",
    ),
    # Ownership drift -> Medium
    (
        {"resource_type": "aws_instance", "drift_type": "Ownership Drift",
         "field": "(resource)", "actual": "i-123", "resource_address": "aws_instance.unmanaged"},
        "Medium",
    ),
]


@pytest.mark.skipif(not OPA_BIN, reason="opa binary not installed")
@pytest.mark.parametrize("input_doc,expected_risk", _REGO_CASES)
def test_rego_policies(input_doc, expected_risk):
    decision = _opa_decision(input_doc)
    assert decision["risk"] == expected_risk
