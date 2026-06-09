"""Drift remediator — turns a ``DriftResult`` into a proposed Terraform patch.

Output is a ``RemediationPatch`` (advisory only). The remediator is strictly
*non-destructive*:

  * **Infrastructure Drift** (attribute changed out of band) -> patch the
    attribute in HCL back to the desired (Terraform) value, restoring the
    resource to its intended state.
  * **Configuration Drift**:
      - attribute-level -> patch the attribute back to the desired value;
      - resource-level (declared in Terraform, missing in the cloud) -> a
        re-create note (apply existing config). **Never** a destroy.
  * **Ownership Drift** (in the cloud, not in Terraform) -> a new resource block
    plus a ``terraform import`` command.
  * **State Drift** -> ``None`` (stale state is reconciled by refresh, not a
    code change; explicitly out of scope).
  * Anything else (Policy Drift, unknown) -> ``None``.

No code path emits a destroy/delete operation.
"""

from __future__ import annotations

import json
import re

from models.drift import (
    CONFIGURATION_DRIFT,
    INFRASTRUCTURE_DRIFT,
    OWNERSHIP_DRIFT,
    DriftResult,
)
from models.remediation import RemediationPatch

# Resource-level findings use this sentinel field (see the diff engine).
_RESOURCE_FIELD = "(resource)"
_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")


def remediate(drift: DriftResult) -> RemediationPatch | None:
    """Return a proposed patch for ``drift``, or ``None`` if none is safe."""
    if drift.drift_type == INFRASTRUCTURE_DRIFT:
        # Restore the resource to its desired (Terraform) value.
        return _attribute_patch(drift, target=drift.desired)
    if drift.drift_type == CONFIGURATION_DRIFT:
        return _configuration_patch(drift)
    if drift.drift_type == OWNERSHIP_DRIFT:
        return _ownership_patch(drift)
    # State Drift, Policy Drift, unknown -> no safe automatic code change.
    return None


# --- per-type builders ------------------------------------------------------
def _attribute_patch(drift: DriftResult, *, target: str | None) -> RemediationPatch | None:
    """Patch a single attribute to ``target``. Resource-level drift has no
    attribute to set, so it returns ``None`` here."""
    if not drift.field or drift.field == _RESOURCE_FIELD:
        return None

    rtype, rname = _split_address(drift.resource_address)
    rendered = _hcl_value(target)
    patch_hcl = (
        f"# DriftWatch remediation for {drift.resource_address}\n"
        f"# {drift.field}: restore to {target} (drifted to {drift.actual})\n"
        f'resource "{rtype}" "{rname}" {{\n'
        f"  {drift.field} = {rendered}\n"
        f"}}"
    )
    description = (
        f"Restore {drift.field} on {rtype}.{rname} to {target} "
        f"(drifted to {drift.actual})."
    )
    return RemediationPatch(
        resource_address=drift.resource_address,
        patch_hcl=patch_hcl,
        import_command=None,
        description=description,
    )


def _configuration_patch(drift: DriftResult) -> RemediationPatch | None:
    if drift.field and drift.field != _RESOURCE_FIELD:
        # Attribute drifted -> restore the intended (desired) value.
        return _attribute_patch(drift, target=drift.desired)

    # Resource-level: declared in Terraform but gone from the cloud. The fix is
    # to re-create it from the existing config — never a destroy.
    rtype, rname = _split_address(drift.resource_address)
    patch_hcl = (
        f"# DriftWatch: {rtype}.{rname} is declared in Terraform but missing in the cloud.\n"
        f"# Re-create it by applying the existing configuration (apply only; non-destructive).\n"
        f'# resource "{rtype}" "{rname}" {{ ... }}  # already defined in terraform-demo/main.tf'
    )
    description = (
        f"{rtype}.{rname} exists in Terraform but is missing in the cloud; "
        f"run `terraform apply` to recreate it (apply only; non-destructive)."
    )
    return RemediationPatch(
        resource_address=drift.resource_address,
        patch_hcl=patch_hcl,
        import_command=None,
        description=description,
    )


def _ownership_patch(drift: DriftResult) -> RemediationPatch:
    rtype, rname = _split_address(drift.resource_address)
    cloud_id = drift.actual  # the diff engine stores the cloud id here
    patch_hcl = (
        f"# DriftWatch: adopt unmanaged resource into Terraform.\n"
        f'resource "{rtype}" "{rname}" {{\n'
        f"  # TODO: define configuration to match the imported resource\n"
        f"}}"
    )
    import_command = f"terraform import {rtype}.{rname} {cloud_id}"
    description = (
        f"Import unmanaged {rtype} ({cloud_id}) into Terraform as {rtype}.{rname}, "
        f"then fill in its configuration."
    )
    return RemediationPatch(
        resource_address=drift.resource_address,
        patch_hcl=patch_hcl,
        import_command=import_command,
        description=description,
    )


# --- helpers ----------------------------------------------------------------
def _split_address(address: str) -> tuple[str, str]:
    """``aws_instance.web[0]`` -> ``("aws_instance", "web")``.

    The ``count``/``for_each`` index is dropped for the block declaration (a
    resource block is declared once, not per instance); the full address is kept
    elsewhere for the import command and PR title.
    """
    base = address.split("[", 1)[0]
    parts = base.split(".")
    rtype = parts[0] if parts else "resource"
    rname = ".".join(parts[1:]) if len(parts) > 1 else "resource"
    return rtype, rname


def _hcl_value(value: str | None) -> str:
    """Render a string value as HCL: numbers/bools bare, everything else quoted."""
    if value is None:
        return '""'
    v = value.strip()
    if v in ("true", "false"):
        return v
    if _INT_RE.match(v) or _FLOAT_RE.match(v):
        return v
    return json.dumps(value)  # proper quoting + escaping
