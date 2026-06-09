"""Offline smoke tests for the Sprint 2 API.

Runs the real FastAPI app against an in-memory SQLite DB with
``DRIFTWATCH_OFFLINE=1`` so detection uses the committed demo fixture (no AWS,
no Postgres needed). Env vars are set before importing the app so settings pick
them up.
"""

import os

_HERE = os.path.dirname(os.path.abspath(__file__))

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["DRIFTWATCH_OFFLINE"] = "1"
# Detection reads a state file; point it at the checked-in fixture so the suite
# passes on a clean checkout with zero real AWS resources.
os.environ["TFSTATE_PATH"] = os.path.join(_HERE, "fixtures", "demo.tfstate")
# Neutralize Sprint 5 external integrations so the startup scan never reaches
# OPA / Groq / Slack / Redis — even if a developer has them exported.
for _var in (
    "OPA_URL",
    "GROQ_API_KEY",
    "REDIS_URL",
    "SLACK_WEBHOOK_URL",
    "GITHUB_TOKEN",
    "GITHUB_REPO",
):
    os.environ[_var] = ""

import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import SIM_ADDRESS


@pytest.fixture
def client():
    # `with` triggers FastAPI startup: create tables + initial offline scan.
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_drift_returns_demo_drifts(client):
    resp = client.get("/api/drift")
    assert resp.status_code == 200
    events = resp.json()
    # demo fixture yields instance-type, S3 tag, and ownership drift
    assert len(events) >= 3
    addresses = {e["resource_address"] for e in events}
    assert "aws_instance.web" in addresses
    assert all("detected_at" in e and "id" in e for e in events)


def test_summary_shape_matches_active(client):
    total = len(client.get("/api/drift").json())
    summary = client.get("/api/drift/summary").json()
    assert summary["total"] == total
    assert set(summary["by_risk"]) == {"Critical", "High", "Medium", "Low"}
    assert isinstance(summary["by_type"], dict)


def test_simulate_then_restore(client):
    before = len(client.get("/api/drift").json())

    created = client.post("/api/drift/simulate").json()["created"]
    assert created["resource_address"] == SIM_ADDRESS
    assert created["risk_impact"] == "High"

    after = client.get("/api/drift").json()
    assert len(after) == before + 1
    assert any(e["resource_address"] == SIM_ADDRESS for e in after)

    resolved = client.post("/api/drift/restore").json()["resolved"]
    assert resolved == 1

    restored = client.get("/api/drift").json()
    assert not any(e["resource_address"] == SIM_ADDRESS for e in restored)
    assert len(restored) == before


def test_metrics_endpoint_exposed(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200


def test_explain_endpoint_returns_explanation(client):
    events = client.get("/api/drift").json()
    assert events
    eid = events[0]["id"]
    resp = client.get(f"/api/drift/{eid}/explain")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == eid
    # No GROQ_API_KEY in tests -> deterministic fallback explanation (non-empty).
    assert isinstance(body["explanation"], str) and body["explanation"]


def test_explain_unknown_id_returns_404(client):
    assert client.get("/api/drift/not-a-uuid/explain").status_code == 404
    assert client.get(f"/api/drift/{uuid.uuid4()}/explain").status_code == 404


def test_remediate_returns_patch_without_github(client):
    # Simulated drift is an Infrastructure Drift (instance_type t3.micro->m5.large).
    created = client.post("/api/drift/simulate").json()["created"]
    resp = client.post(f"/api/drift/{created['id']}/remediate")
    assert resp.status_code == 200
    body = resp.json()
    # No GITHUB_TOKEN in tests -> patch returned, no PR opened.
    assert body["pr_url"] is None
    assert body["patch"] is not None
    assert body["patch"]["resource_address"] == created["resource_address"]
    assert "instance_type" in body["patch"]["patch_hcl"]
    client.post("/api/drift/restore")


def test_remediate_unknown_id_returns_404(client):
    assert client.post("/api/drift/not-a-uuid/remediate").status_code == 404
    assert client.post(f"/api/drift/{uuid.uuid4()}/remediate").status_code == 404
