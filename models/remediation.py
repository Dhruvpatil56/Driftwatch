"""Remediation model — a proposed, human-reviewable Terraform fix for drift.

A ``RemediationPatch`` is *advisory*: it describes a minimal change a human can
review and merge. DriftWatch never applies, merges, or destroys anything — the
GitHub PR is the approval gate.
"""

from __future__ import annotations

from pydantic import BaseModel


class RemediationPatch(BaseModel):
    """A proposed fix for a single drift finding."""

    resource_address: str
    """Terraform address the patch targets, e.g. ``aws_instance.web``."""

    patch_hcl: str
    """Proposed HCL snippet (a review artifact, appended to the demo config)."""

    import_command: str | None = None
    """``terraform import ...`` to adopt an unmanaged resource, if applicable."""

    description: str
    """One-line, human-readable summary of what the patch does."""
