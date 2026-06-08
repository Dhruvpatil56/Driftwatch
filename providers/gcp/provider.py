"""GCPProvider — stub only.

DriftWatch is cloud-agnostic by design (everything funnels through
``NormalizedResource``), but only AWS is implemented in Sprint 1. This stub
exists to prove the interface is provider-neutral; every method raises
``NotImplementedError``.
"""

from __future__ import annotations

from models.normalized import NormalizedResource
from providers.base import CloudProvider


class GCPProvider(CloudProvider):
    def list_resources(self, resource_types: list[str]) -> list[NormalizedResource]:
        raise NotImplementedError("GCPProvider is not implemented yet")

    def get_resource(self, resource_id: str) -> NormalizedResource:
        raise NotImplementedError("GCPProvider is not implemented yet")
