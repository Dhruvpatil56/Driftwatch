"""Terraform state parser -> recorded ``NormalizedResource`` list.

Reads a ``.tfstate`` JSON file (the *recorded* state — what Terraform believes
exists) and emits one ``NormalizedResource`` per state instance. The instance's
``id`` becomes ``cloud_id``, which the diff engine later uses to match against
live cloud resources.
"""

from __future__ import annotations

import json
from typing import Any

from engine.parser.normalize import normalize
from models.normalized import RECORDED, NormalizedResource


def parse_tfstate(path: str) -> list[NormalizedResource]:
    """Parse a Terraform state file into recorded resources."""
    with open(path, "r", encoding="utf-8") as fh:
        state = json.load(fh)
    return _resources_from_state(state)


def parse_tfstate_dict(state: dict[str, Any]) -> list[NormalizedResource]:
    """Parse an already-loaded state dict (handy for tests)."""
    return _resources_from_state(state)


def _resources_from_state(state: dict[str, Any]) -> list[NormalizedResource]:
    resources: list[NormalizedResource] = []
    for res in state.get("resources", []):
        # Only Terraform-managed resources have desired/recorded meaning;
        # data sources are read-only lookups.
        if res.get("mode") != "managed":
            continue
        resource_type = res["type"]
        name = res["name"]
        for instance in res.get("instances", []):
            attributes = instance.get("attributes", {})
            address = _address(resource_type, name, instance.get("index_key"))
            resources.append(
                NormalizedResource(
                    resource_address=address,
                    resource_type=resource_type,
                    cloud_id=attributes.get("id"),
                    attributes=normalize(resource_type, RECORDED, attributes),
                    source=RECORDED,
                )
            )
    return resources


def _address(resource_type: str, name: str, index_key: Any) -> str:
    base = f"{resource_type}.{name}"
    if index_key is None:
        return base
    # count -> integer index_key -> [0]; for_each -> string key -> ["key"]
    if isinstance(index_key, int):
        return f'{base}[{index_key}]'
    return f'{base}["{index_key}"]'
