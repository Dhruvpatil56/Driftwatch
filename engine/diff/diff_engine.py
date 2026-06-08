"""Three-way diff engine.

Reconciles desired (HCL), recorded (state) and actual (cloud) views of the
same infrastructure and produces ``DriftResult`` findings.

Matching strategy:
  * desired <-> recorded are matched by ``resource_address``.
  * actual has no Terraform address, so it is matched to an address via the
    ``cloud_id`` recorded in state. Actual resources whose id is not in state
    are *orphans* -> Ownership Drift.

Each finding is then scored for cost / risk / governance impact.
"""

from __future__ import annotations

from typing import Any, Iterable

from engine.classifier.classifier import classify_presence, classify_value
from engine.scorer.scorer import score
from models.drift import OWNERSHIP_DRIFT, DriftResult
from models.normalized import NormalizedResource


def reconcile(
    desired: Iterable[NormalizedResource],
    recorded: Iterable[NormalizedResource],
    actual: Iterable[NormalizedResource],
) -> list[DriftResult]:
    """Reconcile the three views and return scored drift results."""
    desired_by_addr = {r.resource_address: r for r in desired}
    recorded_by_addr = {r.resource_address: r for r in recorded}
    id_to_addr = {r.cloud_id: r.resource_address for r in recorded_by_addr.values() if r.cloud_id}

    actual_by_addr: dict[str, NormalizedResource] = {}
    orphans: list[NormalizedResource] = []
    for r in actual:
        addr = id_to_addr.get(r.cloud_id)
        if addr is not None:
            actual_by_addr[addr] = r
        else:
            orphans.append(r)

    results: list[DriftResult] = []
    addresses = set(desired_by_addr) | set(recorded_by_addr) | set(actual_by_addr)
    for addr in sorted(addresses):
        results.extend(
            _reconcile_one(
                addr,
                desired_by_addr.get(addr),
                recorded_by_addr.get(addr),
                actual_by_addr.get(addr),
            )
        )

    for r in orphans:
        results.append(_ownership_result(r))

    for drift in results:
        score(drift)
    return results


def _reconcile_one(
    address: str,
    desired: NormalizedResource | None,
    recorded: NormalizedResource | None,
    actual: NormalizedResource | None,
) -> list[DriftResult]:
    presence = classify_presence(
        desired is not None, recorded is not None, actual is not None
    )
    if presence is not None:
        return [
            DriftResult(
                resource_address=address,
                drift_type=presence,
                field="(resource)",
                desired=_presence_label(desired),
                recorded=_presence_label(recorded),
                actual=_presence_label(actual),
            )
        ]

    # Only resources present in all three views get field-level comparison.
    # Other partial patterns (e.g. planned-but-unapplied) are out of scope for
    # Sprint 1.
    if not (desired and recorded and actual):
        return []

    results: list[DriftResult] = []
    fields = sorted(set(desired.attributes) | set(recorded.attributes))
    for field in fields:
        dval = desired.attributes.get(field)
        rval = recorded.attributes.get(field)
        aval = actual.attributes.get(field)
        drift_type = classify_value(dval, rval, aval)
        if drift_type is None:
            continue
        results.append(
            DriftResult(
                resource_address=address,
                drift_type=drift_type,
                field=field,
                desired=_fmt(dval),
                recorded=_fmt(rval),
                actual=_fmt(aval),
            )
        )
    return results


def _ownership_result(actual: NormalizedResource) -> DriftResult:
    address = actual.resource_address or f"{actual.resource_type}.unmanaged"
    return DriftResult(
        resource_address=address,
        drift_type=OWNERSHIP_DRIFT,
        field="(resource)",
        desired="absent",
        recorded="absent",
        actual=actual.cloud_id or "present",
    )


def _presence_label(resource: NormalizedResource | None) -> str:
    return "present" if resource is not None else "missing"


def _fmt(value: Any) -> str:
    if value is None:
        return "absent"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "[]"
    return str(value)
