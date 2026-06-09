"""Slack alerting for newly-detected high-severity drift (Sprint 5).

When a scan finds *new* Critical or High drift, post a concise message to a
Slack incoming webhook. Entirely optional and fail-safe:

  * ``SLACK_WEBHOOK_URL`` unset  -> skip silently, no work done.
  * Any send error               -> swallowed and logged at WARNING; a scan is
                                     never broken by a notification problem.

The webhook URL is read from ``os.environ`` (not pydantic settings) so a value
present only in a local ``.env`` does not leak into the test process and
accidentally post real messages.
"""

from __future__ import annotations

import logging
import os

import httpx

from engine.explainer import explain_one_line
from models.drift import DriftResult

logger = logging.getLogger("driftwatch.notifications")

# Severities that warrant an immediate alert.
_ALERT_LEVELS = {"Critical", "High"}
_TIMEOUT = 10.0


def notify_new_drift(results: list[DriftResult]) -> int:
    """Send a Slack alert for each new Critical/High drift in ``results``.

    Returns the number of alerts sent (0 if Slack is disabled). Never raises.
    """
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        # Disabled — do no work at all (also avoids any explainer/Groq calls).
        return 0

    sent = 0
    for drift in results:
        if drift.risk_impact not in _ALERT_LEVELS:
            continue
        if _post(webhook, _format(drift)):
            sent += 1
    return sent


def _format(drift: DriftResult) -> dict:
    explanation = explain_one_line(drift)
    emoji = "🔴" if drift.risk_impact == "Critical" else "🟠"
    text = (
        f"{emoji} *DriftWatch {drift.risk_impact} drift detected*\n"
        f"• *Resource:* `{drift.resource_address}`\n"
        f"• *Type:* {drift.drift_type}\n"
        f"• *Risk:* {drift.risk_impact}\n"
        f"• *Why:* {explanation}"
    )
    return {"text": text}


def _post(webhook: str, payload: dict) -> bool:
    try:
        resp = httpx.post(webhook, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("slack notification failed: %s", exc)
        return False
