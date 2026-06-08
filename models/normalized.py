"""Cloud-agnostic resource model.

A ``NormalizedResource`` is the single representation every source (Terraform
HCL, Terraform state, live cloud API) is funnelled into before the diff engine
ever looks at it. The model fields are deliberately cloud-neutral — there are no
AWS-specific field names here. Provider quirks live only inside the free-form
``attributes`` dict, populated by the normalization layer.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# The three views DriftWatch reconciles.
DESIRED = "desired"   # Terraform HCL — what should exist
RECORDED = "recorded"  # Terraform state — what Terraform thinks exists
ACTUAL = "actual"     # Cloud API — what actually exists

Source = Literal["desired", "recorded", "actual"]


class NormalizedResource(BaseModel):
    """One resource as seen from a single source.

    The same logical resource (e.g. ``aws_instance.web``) typically appears as
    three ``NormalizedResource`` instances — one per source — which the diff
    engine then reconciles.
    """

    resource_address: str
    """Terraform address, e.g. ``aws_instance.web``.

    Empty for ``actual`` resources scraped from the cloud, since the cloud has
    no notion of a Terraform address. The diff engine back-fills it by matching
    on ``cloud_id``.
    """

    resource_type: str
    """Terraform resource type, e.g. ``aws_instance``."""

    cloud_id: str | None = None
    """Provider resource id, e.g. ``i-0abc...``. ``None`` for HCL-derived
    resources, which have not been created yet."""

    attributes: dict[str, Any] = Field(default_factory=dict)
    """Normalized, canonical attributes, e.g. ``{"instance_type": "t3.micro"}``.
    Keys are identical across sources so the diff engine can compare directly."""

    source: Source
    """Which of the three views this resource came from."""

    def get(self, field: str, default: Any = None) -> Any:
        """Convenience accessor for a single normalized attribute."""
        return self.attributes.get(field, default)
