"""Thin client for the Open Policy Agent (OPA) sidecar.

The scorer asks OPA to evaluate a single drift finding against the Rego policies
in ``policies/rules.rego``. OPA runs as a sidecar (docker-compose service ``opa``
on port 8181). This client is deliberately fail-open: any problem reaching OPA
returns ``None`` so the caller can fall back to the built-in Python rules.

Configuration is read straight from ``os.environ`` (not the pydantic settings)
so the engine stays decoupled from the API package and so the default behaviour
is *disabled*:

  * ``OPA_URL`` unset / empty  -> OPA disabled, no network call, returns ``None``.
  * ``OPA_URL`` set            -> POST the decision query; fall back on any error.

In docker the ``env_file`` injects ``OPA_URL=http://opa:8181`` as a real
environment variable; local test runs leave it unset and never touch the
network.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

# Query the single consolidated decision rule.
_DECISION_PATH = "/v1/data/driftwatch/policies/decision"
_DEFAULT_TIMEOUT = 2.0

# Process-level memo: once we learn OPA is unreachable we stop retrying for the
# rest of the run so a missing sidecar never slows a whole scan to a crawl.
_unreachable = False


def reset() -> None:
    """Clear the unreachable memo (used by tests)."""
    global _unreachable
    _unreachable = False


def is_enabled() -> bool:
    """True if an OPA endpoint is configured."""
    return bool(os.environ.get("OPA_URL", "").strip())


def evaluate(input_doc: dict[str, Any]) -> dict[str, Any] | None:
    """Return OPA's decision for ``input_doc``, or ``None`` if unavailable.

    Never raises: connection errors, timeouts, bad status codes and malformed
    responses all collapse to ``None`` so the caller falls back to Python.
    """
    global _unreachable
    base = os.environ.get("OPA_URL", "").strip()
    if not base or _unreachable:
        return None

    url = base.rstrip("/") + _DECISION_PATH
    timeout = _timeout()
    try:
        resp = httpx.post(url, json={"input": input_doc}, timeout=timeout)
        resp.raise_for_status()
        result = resp.json().get("result")
    except (httpx.ConnectError, httpx.ConnectTimeout):
        # Sidecar absent — stop retrying for the rest of the process.
        _unreachable = True
        return None
    except Exception:
        # Transient/other error: skip this one but keep trying next time.
        return None

    if isinstance(result, dict) and "risk" in result:
        return result
    return None


def _timeout() -> float:
    raw = os.environ.get("OPA_TIMEOUT", "").strip()
    try:
        return float(raw) if raw else _DEFAULT_TIMEOUT
    except ValueError:
        return _DEFAULT_TIMEOUT
