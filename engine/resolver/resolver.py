"""Resource resolver — expands Terraform meta-arguments into instances.

The HCL parser emits one ``NormalizedResource`` per ``resource`` block, keyed by
its base address (``aws_instance.web``). But Terraform's ``count`` and
``for_each`` meta-arguments expand a single block into *many* concrete
instances, each with its own indexed address:

    resource "aws_instance" "web" { count = 3 }
        -> aws_instance.web[0], aws_instance.web[1], aws_instance.web[2]

    resource "aws_instance" "web" { for_each = { prod = ..., staging = ... } }
        -> aws_instance.web["prod"], aws_instance.web["staging"]

The Terraform *state* file already records these indexed addresses (see
``engine.parser.tfstate_parser``). Without expansion, the desired (HCL) side
would carry only the bare ``aws_instance.web`` address and would never line up
with the recorded instances, producing spurious presence drift. This resolver
closes that gap: it maps each Terraform resource address to the concrete set of
instances Terraform would actually manage.

Scope (Sprint 4):
  * simple resources (no meta-arg) — pass through unchanged
  * ``count`` with an integer
  * ``for_each`` with a map (string keys) or a set/list of strings

Dynamic blocks and computed/unknown meta-argument values are out of scope and
left for a later sprint.

This module lives entirely in ``engine/resolver/`` and does not modify the
parser, diff engine, classifier, or scorer. It reuses their public helpers
(``normalize``, ``NormalizedResource``) only.
"""

from __future__ import annotations

import os
from typing import Any

import hcl2
from hcl2.utils import SerializationOptions

from engine.parser.normalize import normalize
from models.normalized import DESIRED, NormalizedResource

# Same serialization options the HCL parser uses, so attribute shapes match.
_OPTS = SerializationOptions(
    strip_string_quotes=True,
    explicit_blocks=False,
    with_comments=False,
)

# Meta-arguments are expansion directives, not resource attributes; they must be
# stripped from the body before normalization so they never leak into a diff.
_META_ARGS = ("count", "for_each", "depends_on", "provider", "lifecycle")


# --- public entry points ---------------------------------------------------
def resolve_hcl_data(data: dict[str, Any]) -> list[NormalizedResource]:
    """Expand every ``resource`` block in a parsed hcl2 dict into instances."""
    resources: list[NormalizedResource] = []
    # hcl2 shape: {"resource": [ {type: {name: {<body>}}}, ... ]}
    for block in data.get("resource", []):
        for resource_type, named in block.items():
            for name, body in named.items():
                resources.extend(_expand(resource_type, name, body))
    return resources


def resolve_hcl_text(text: str) -> list[NormalizedResource]:
    """Expand HCL given as a string (handy for tests)."""
    import io

    data = hcl2.load(io.StringIO(text), serialization_options=_OPTS)
    return resolve_hcl_data(data)


def resolve_hcl(path: str) -> list[NormalizedResource]:
    """Expand a ``.tf`` file or a directory of ``.tf`` files into instances."""
    if os.path.isdir(path):
        resources: list[NormalizedResource] = []
        for fname in sorted(os.listdir(path)):
            if fname.endswith(".tf"):
                resources.extend(resolve_hcl(os.path.join(path, fname)))
        return resources
    with open(path, "r", encoding="utf-8") as fh:
        data = hcl2.load(fh, serialization_options=_OPTS)
    return resolve_hcl_data(data)


# --- expansion -------------------------------------------------------------
def _expand(resource_type: str, name: str, body: dict[str, Any]) -> list[NormalizedResource]:
    """Expand one HCL resource block into one or more concrete instances."""
    base = f"{resource_type}.{name}"

    if "count" in body:
        return _expand_count(resource_type, base, body)
    if "for_each" in body:
        return _expand_for_each(resource_type, base, body)
    return [_instance(resource_type, base, body, refs={})]


def _expand_count(
    resource_type: str, base: str, body: dict[str, Any]
) -> list[NormalizedResource]:
    n = _as_count(body.get("count"))
    instances: list[NormalizedResource] = []
    for i in range(n):
        # count -> integer index_key -> base[0], base[1], ...
        address = f"{base}[{i}]"
        instances.append(
            _instance(resource_type, address, body, refs={"count.index": i})
        )
    return instances


def _expand_for_each(
    resource_type: str, base: str, body: dict[str, Any]
) -> list[NormalizedResource]:
    pairs = _as_for_each(body.get("for_each"))
    instances: list[NormalizedResource] = []
    # Terraform iterates for_each keys in sorted order; match that for stable,
    # reproducible output.
    for key in sorted(pairs):
        value = pairs[key]
        # for_each -> string index_key -> base["prod"], base["staging"]
        address = f'{base}["{key}"]'
        instances.append(
            _instance(
                resource_type,
                address,
                body,
                refs={"each.key": key, "each.value": value},
            )
        )
    return instances


def _instance(
    resource_type: str,
    address: str,
    body: dict[str, Any],
    refs: dict[str, Any],
) -> NormalizedResource:
    """Build one ``NormalizedResource`` from a (sub)body, resolving references
    and stripping meta-arguments before normalization."""
    resolved = _resolve_refs(body, refs)
    attrs = {k: v for k, v in resolved.items() if k not in _META_ARGS}
    return NormalizedResource(
        resource_address=address,
        resource_type=resource_type,
        cloud_id=None,  # desired state — not created yet
        attributes=normalize(resource_type, DESIRED, attrs),
        source=DESIRED,
    )


# --- meta-argument coercion ------------------------------------------------
def _as_count(raw: Any) -> int:
    """Coerce a ``count`` value to a non-negative integer.

    Only integer literals are supported in Sprint 4; computed counts (e.g.
    ``length(var.subnets)``) arrive as interpolation strings and are out of
    scope.
    """
    if isinstance(raw, bool):  # bool is an int subclass — reject explicitly
        raise ValueError(f"count must be an integer, got bool: {raw!r}")
    if isinstance(raw, int):
        return max(0, raw)
    if isinstance(raw, str) and raw.strip().lstrip("-").isdigit():
        return max(0, int(raw.strip()))
    raise ValueError(
        f"unsupported count value {raw!r}; only integer literals are resolved"
    )


def _as_for_each(raw: Any) -> dict[str, Any]:
    """Coerce a ``for_each`` value to a ``{key: value}`` map.

    Accepts a map (the common case) or a set/list of strings, which Terraform
    treats as a set where each key equals its value.
    """
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    if isinstance(raw, (list, set, tuple)):
        return {str(v): str(v) for v in raw}
    raise ValueError(
        f"unsupported for_each value {raw!r}; expected a map or set of strings"
    )


# --- reference resolution --------------------------------------------------
def _resolve_refs(value: Any, refs: dict[str, Any]) -> Any:
    """Recursively substitute ``count.index`` / ``each.key`` / ``each.value``
    references inside attribute values.

    hcl2 renders interpolations as ``${...}``. When a string is *exactly* a
    single reference (``"${each.value}"``), the raw referenced value is
    returned so non-string values survive. Otherwise the reference is rendered
    inline (``"web-${count.index}"`` -> ``"web-0"``).
    """
    if not refs:
        return value
    if isinstance(value, dict):
        return {k: _resolve_refs(v, refs) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_refs(v, refs) for v in value]
    if isinstance(value, str):
        return _resolve_string(value, refs)
    return value


def _resolve_string(value: str, refs: dict[str, Any]) -> Any:
    for ref, replacement in refs.items():
        token = "${" + ref + "}"
        if value == token:
            # Whole-string reference: preserve the referenced value's type.
            return replacement
        if token in value:
            value = value.replace(token, str(replacement))
    return value
