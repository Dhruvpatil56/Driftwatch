"""Tests for the Groq drift explainer (Sprint 5).

No real network is used: the Groq HTTP call and the Redis client are mocked.
Covers: deterministic fallback when no key, Groq path when a key is set,
fallback on Groq failure, Redis cache hit/set, and error-swallowing.
"""

import pytest

from engine.explainer import explainer
from models.drift import INFRASTRUCTURE_DRIFT, OWNERSHIP_DRIFT, DriftResult


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


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    explainer._reset_redis()
    yield
    explainer._reset_redis()


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, k):
        return self.store.get(k)

    def setex(self, k, ttl, v):
        self.store[k] = v.encode("utf-8") if isinstance(v, str) else v


# --- fallback (no API key) -------------------------------------------------
def test_fallback_when_no_key_describes_drift():
    text = explainer.explain(_drift(), use_cache=False)
    assert "instance_type" in text
    assert "m5.large" in text
    assert "Probable cause" in text


def test_fallback_for_resource_level_drift():
    text = explainer.explain(
        _drift(drift_type=OWNERSHIP_DRIFT, field="(resource)", actual="i-1",
               governance_impact="Untracked resource"),
        use_cache=False,
    )
    assert "ownership drift" in text.lower()
    assert "Untracked resource" in text


# --- Groq path -------------------------------------------------------------
def test_groq_explanation_used_when_key_set(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "  The instance grew. It matters.  "}}]}

    monkeypatch.setattr(explainer.httpx, "post", lambda *a, **k: _Resp())
    text = explainer.explain(_drift(), use_cache=False)
    assert text == "The instance grew. It matters."


def test_groq_failure_falls_back(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    def boom(*a, **k):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(explainer.httpx, "post", boom)
    text = explainer.explain(_drift(), use_cache=False)
    assert "Probable cause" in text  # deterministic fallback


def test_one_line_has_no_newlines(monkeypatch):
    monkeypatch.setattr(explainer, "_from_groq", lambda d: "line one\nline two\nline three")
    out = explainer.explain_one_line(_drift(), use_cache=False)
    assert "\n" not in out
    assert "line one line two line three" == out


# --- Redis cache -----------------------------------------------------------
def test_cache_hit_skips_groq(monkeypatch):
    fake = _FakeRedis()
    d = _drift()
    fake.store[explainer._cache_key(d)] = b"cached explanation"
    monkeypatch.setattr(explainer, "_get_redis", lambda: fake)

    def must_not_call(*a, **k):
        raise AssertionError("Groq must not be called on a cache hit")

    monkeypatch.setattr(explainer, "_from_groq", must_not_call)
    assert explainer.explain(d) == "cached explanation"


def test_groq_result_is_cached(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(explainer, "_get_redis", lambda: fake)
    monkeypatch.setattr(explainer, "_from_groq", lambda d: "fresh ai text")
    d = _drift()
    assert explainer.explain(d) == "fresh ai text"
    # second call served from cache
    assert explainer._cache_get(explainer._cache_key(d)) == "fresh ai text"


def test_cache_get_swallows_redis_errors(monkeypatch):
    class _Boom:
        def get(self, k):
            raise RuntimeError("redis down")

    monkeypatch.setattr(explainer, "_get_redis", lambda: _Boom())
    assert explainer._cache_get("anykey") is None


def test_no_redis_url_means_no_client(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    explainer._reset_redis()
    assert explainer._get_redis() is None
