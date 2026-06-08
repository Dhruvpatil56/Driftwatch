"""The cloud provider interface.

Every provider returns ``NormalizedResource`` objects (source = ``actual``) so
the rest of the engine never sees a cloud-specific shape. AWSProvider
implements this fully; GCPProvider is a stub.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from models.normalized import NormalizedResource


class CloudProvider(ABC):
    @abstractmethod
    def list_resources(self, resource_types: list[str]) -> list[NormalizedResource]:
        """Return the live (actual) resources for the given Terraform types."""
        raise NotImplementedError

    @abstractmethod
    def get_resource(self, resource_id: str) -> NormalizedResource:
        """Return a single live resource by its cloud id."""
        raise NotImplementedError
