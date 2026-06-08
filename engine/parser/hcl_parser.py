"""Terraform HCL parser -> desired ``NormalizedResource`` list.

Reads ``.tf`` files (the *desired* state — what should exist) and emits one
``NormalizedResource`` per ``resource`` block, with attributes run through the
normalization layer so they line up with the other two sources.
"""

from __future__ import annotations

import os
from typing import Any

import hcl2
from hcl2.utils import SerializationOptions

from engine.parser.normalize import normalize
from models.normalized import DESIRED, NormalizedResource

# hcl2 8.x preserves literal quotes and block markers by default; these options
# give us clean, backwards-compatible Python values.
_OPTS = SerializationOptions(
    strip_string_quotes=True,
    explicit_blocks=False,
    with_comments=False,
)


def parse_hcl_file(path: str) -> list[NormalizedResource]:
    """Parse a single ``.tf`` file into desired resources."""
    with open(path, "r", encoding="utf-8") as fh:
        data = hcl2.load(fh, serialization_options=_OPTS)
    return _resources_from_hcl(data)


def parse_hcl_dir(path: str) -> list[NormalizedResource]:
    """Parse every ``.tf`` file in a directory (non-recursive) into desired
    resources."""
    resources: list[NormalizedResource] = []
    for name in sorted(os.listdir(path)):
        if name.endswith(".tf"):
            resources.extend(parse_hcl_file(os.path.join(path, name)))
    return resources


def parse_hcl(path: str) -> list[NormalizedResource]:
    """Parse a file or directory of HCL into desired resources."""
    if os.path.isdir(path):
        return parse_hcl_dir(path)
    return parse_hcl_file(path)


def _resources_from_hcl(data: dict[str, Any]) -> list[NormalizedResource]:
    resources: list[NormalizedResource] = []
    # hcl2 shape: {"resource": [ {type: {name: {<attrs>}}}, ... ]}
    for block in data.get("resource", []):
        for resource_type, named in block.items():
            for name, body in named.items():
                address = f"{resource_type}.{name}"
                resources.append(
                    NormalizedResource(
                        resource_address=address,
                        resource_type=resource_type,
                        cloud_id=None,  # not created yet, from HCL's point of view
                        attributes=normalize(resource_type, DESIRED, body),
                        source=DESIRED,
                    )
                )
    return resources
