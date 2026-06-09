"""Groq-backed drift explanation (Sprint 5).

Turns a single ``DriftResult`` into a short, plain-English explanation covering
*what* drifted, *why it matters*, and the *probable cause*.

Strict scope: **AI touches explanation only** — never detection, scoring, or
remediation. This module is read-only with respect to drift; it produces text.

Design:
  * Model: Groq ``llama-3.3-70b-versatile`` via the OpenAI-compatible REST API.
  * Optional: if ``GROQ_API_KEY`` is unset (or the call fails), a deterministic
    local fallback explanation is returned instead — the caller always gets
    usable text and never an error.
  * Cache: explanations are cached in Redis keyed by drift *identity* (not DB
    id) so the same drift never costs two API calls. If Redis is unreachable,
    caching is silently skipped.

Configuration is read from ``os.environ`` (``GROQ_API_KEY``, ``GROQ_MODEL``,
``REDIS_URL``) so the engine stays decoupled from the API package.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

import httpx

from models.drift import DriftResult

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_GROQ_TIMEOUT = 20.0
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 1 day
_CACHE_PREFIX = "driftwatch:explain:"

_SYSTEM_PROMPT = (
    "You are a cloud infrastructure governance assistant. Given one Terraform "
    "drift finding, explain in 2-3 short sentences: what drifted, why it "
    "matters, and the most probable cause. Be concrete and concise. Do not "
    "suggest remediation commands."
)

# Lazily-created Redis client; None until first use, False if unavailable.
_redis_client: Any = None


def explain(drift: DriftResult, *, use_cache: bool = True) -> str:
    """Return a plain-English explanation of ``drift``.

    Never raises. Falls back to a deterministic local explanation when Groq is
    not configured or the API call fails.
    """
    key = _cache_key(drift)
    if use_cache:
        cached = _cache_get(key)
        if cached:
            return cached

    text = _from_groq(drift)
    if text:
        if use_cache:
            _cache_set(key, text)
        return text

    # No key / API failure -> deterministic local fallback (not cached, so a
    # later real explanation can replace it).
    return _fallback(drift)


def explain_one_line(drift: DriftResult, *, use_cache: bool = True) -> str:
    """A single-line explanation, suitable for a Slack message."""
    return _one_line(explain(drift, use_cache=use_cache))


# --- Groq ------------------------------------------------------------------
def _from_groq(drift: DriftResult) -> str | None:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.environ.get("GROQ_MODEL", "").strip() or _DEFAULT_MODEL
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(drift)},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = httpx.post(_GROQ_URL, json=payload, headers=headers, timeout=_GROQ_TIMEOUT)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return content.strip() or None
    except Exception:
        # Any failure (no network, bad key, rate limit, schema change) -> fall
        # back. Explanation is never allowed to break the caller.
        return None


def _user_prompt(drift: DriftResult) -> str:
    return (
        f"Resource: {drift.resource_address}\n"
        f"Drift type: {drift.drift_type}\n"
        f"Field: {drift.field}\n"
        f"Desired (Terraform HCL): {drift.desired}\n"
        f"Recorded (Terraform state): {drift.recorded}\n"
        f"Actual (cloud): {drift.actual}\n"
        f"Risk: {drift.risk_impact}\n"
        f"Governance note: {drift.governance_impact}"
    )


def _fallback(drift: DriftResult) -> str:
    """Deterministic, no-API explanation used when Groq is unavailable."""
    if drift.field in ("(resource)", "", None):
        what = f"{drift.resource_address} shows {drift.drift_type.lower()}"
    else:
        what = (
            f"{drift.resource_address}: '{drift.field}' changed from desired "
            f"'{drift.desired}' to actual '{drift.actual}'"
        )
    why = drift.governance_impact if drift.governance_impact not in ("None", None, "") else (
        f"this is a {drift.risk_impact.lower()}-risk {drift.drift_type.lower()}"
    )
    cause = "Likely an out-of-band change made directly in the cloud console or via another tool, outside Terraform."
    return f"{what}. Why it matters: {why}. Probable cause: {cause}"


# --- cache -----------------------------------------------------------------
def _cache_key(drift: DriftResult) -> str:
    raw = "|".join(
        str(x)
        for x in (
            drift.resource_address,
            drift.drift_type,
            drift.field,
            drift.desired,
            drift.recorded,
            drift.actual,
            drift.risk_impact,
        )
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return _CACHE_PREFIX + digest


def _get_redis() -> Any:
    """Return a Redis client, or ``None`` if Redis is unconfigured/unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client or None
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        _redis_client = False
        return None
    try:
        import redis  # imported lazily so the package is optional

        client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        _redis_client = client
        return client
    except Exception:
        _redis_client = False
        return None


def _cache_get(key: str) -> str | None:
    client = _get_redis()
    if client is None:
        return None
    try:
        val = client.get(key)
        if val is None:
            return None
        return val.decode("utf-8") if isinstance(val, bytes) else str(val)
    except Exception:
        return None


def _cache_set(key: str, value: str) -> None:
    client = _get_redis()
    if client is None:
        return
    try:
        client.setex(key, _CACHE_TTL_SECONDS, value)
    except Exception:
        pass


def _reset_redis() -> None:
    """Test hook: drop the memoized client so REDIS_URL changes take effect."""
    global _redis_client
    _redis_client = None


def _one_line(text: str) -> str:
    return " ".join(text.split())
