"""Tests for Slack alerting (Sprint 5).

Slack is optional and fail-safe: no webhook -> no work; send errors are
swallowed. No real network is used (httpx.post is mocked). With no GROQ_API_KEY
the one-line explanation uses the deterministic fallback, so these tests make no
external calls.
"""

import pytest

from api import notifications
from models.drift import INFRASTRUCTURE_DRIFT, DriftResult

WEBHOOK = "https://hooks.slack.test/services/xxx"


def _drift(risk="Critical"):
    return DriftResult(
        resource_address="aws_security_group.web_sg",
        drift_type=INFRASTRUCTURE_DRIFT,
        field="ingress",
        desired="closed",
        recorded="closed",
        actual="tcp:22-22:0.0.0.0/0",
        risk_impact=risk,
    )


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    yield


def test_skips_silently_when_no_webhook(monkeypatch):
    calls = []
    monkeypatch.setattr(notifications.httpx, "post", lambda *a, **k: calls.append(1))
    sent = notifications.notify_new_drift([_drift("Critical")])
    assert sent == 0
    assert calls == []  # not even an explanation/HTTP attempt


def test_alerts_only_critical_and_high(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK)
    posted = []

    class _Resp:
        def raise_for_status(self):
            pass

    def fake_post(url, json=None, **k):
        posted.append((url, json))
        return _Resp()

    monkeypatch.setattr(notifications.httpx, "post", fake_post)
    sent = notifications.notify_new_drift(
        [_drift("Critical"), _drift("High"), _drift("Medium"), _drift("Low")]
    )
    assert sent == 2
    assert len(posted) == 2
    assert all(url == WEBHOOK for url, _ in posted)


def test_message_contains_required_fields(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK)
    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

    def fake_post(url, json=None, **k):
        captured["payload"] = json
        return _Resp()

    monkeypatch.setattr(notifications.httpx, "post", fake_post)
    notifications.notify_new_drift([_drift("Critical")])
    text = captured["payload"]["text"]
    assert "aws_security_group.web_sg" in text  # resource address
    assert INFRASTRUCTURE_DRIFT in text          # drift type
    assert "Critical" in text                    # risk level
    assert "Why:" in text                        # one-line explanation present


def test_never_raises_on_post_failure(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK)

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(notifications.httpx, "post", boom)
    # Must not raise; failed send counts as not sent.
    assert notifications.notify_new_drift([_drift("Critical")]) == 0
