"""Attribute normalization.

Each source describes the same resource with different field names and shapes:

  * Terraform HCL / state -> ``instance_type``, ``ingress = [{...}]``
  * AWS API               -> ``InstanceType``, ``IpPermissions = [{...}]``

The diff engine must compare apples to apples, so every source is funnelled
through here into a canonical attribute dict with identical keys. This is the
seed of the full normalization pipeline (expanded in Sprint 2).

Only the attributes that matter for Sprint 1 (instance type/image, SG rules,
bucket name) are normalized. Unknown resource types fall back to a passthrough
so nothing explodes — they simply won't produce meaningful diffs yet.
"""

from __future__ import annotations

from typing import Any

from models.normalized import ACTUAL


# --- security-group rule canonicalization ----------------------------------
def _rule_key(protocol: Any, from_port: Any, to_port: Any, cidrs: list[Any]) -> str:
    """Render one ingress/egress rule as a single comparable string.

    The ``-1`` / ``all`` protocol is special-cased so the Terraform shape
    (``protocol = "-1", from_port = 0, to_port = 0``) and the AWS shape
    (``IpProtocol = "-1"`` with no ports) collapse to the same key instead of
    reporting a spurious drift.
    """
    protocol = str(protocol)
    if protocol in ("-1", "all"):
        ports = "all"
    else:
        ports = f"{from_port}-{to_port}"
    rendered_cidrs = ",".join(sorted(str(c) for c in cidrs))
    return f"{protocol}:{ports}:{rendered_cidrs}"


def _tf_rules(blocks: Any) -> list[str]:
    if not blocks:
        return []
    return sorted(
        _rule_key(
            b.get("protocol"),
            b.get("from_port"),
            b.get("to_port"),
            b.get("cidr_blocks") or [],
        )
        for b in blocks
    )


def _aws_rules(perms: Any) -> list[str]:
    if not perms:
        return []
    rules = []
    for p in perms:
        cidrs = [r.get("CidrIp") for r in p.get("IpRanges", []) if r.get("CidrIp")]
        rules.append(
            _rule_key(p.get("IpProtocol"), p.get("FromPort"), p.get("ToPort"), cidrs)
        )
    return sorted(rules)


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


# --- Terraform-shaped sources (desired + recorded) -------------------------
def _tf_ec2(raw: dict) -> dict:
    return _drop_none({"instance_type": raw.get("instance_type"), "ami": raw.get("ami")})


def _tf_sg(raw: dict) -> dict:
    return _drop_none(
        {
            "name": raw.get("name"),
            "description": raw.get("description"),
            "ingress": _tf_rules(raw.get("ingress")),
            "egress": _tf_rules(raw.get("egress")),
        }
    )


def _tf_s3(raw: dict) -> dict:
    return _drop_none({"bucket": raw.get("bucket")})


# --- AWS-shaped source (actual) --------------------------------------------
def _aws_ec2(raw: dict) -> dict:
    return _drop_none(
        {"instance_type": raw.get("InstanceType"), "ami": raw.get("ImageId")}
    )


def _aws_sg(raw: dict) -> dict:
    return _drop_none(
        {
            "name": raw.get("GroupName"),
            "description": raw.get("Description"),
            "ingress": _aws_rules(raw.get("IpPermissions")),
            "egress": _aws_rules(raw.get("IpPermissionsEgress")),
        }
    )


def _aws_s3(raw: dict) -> dict:
    out: dict[str, Any] = {"bucket": raw.get("Name") or raw.get("bucket")}
    # versioning is only known if the scraper looked it up
    if "Versioning" in raw:
        out["versioning"] = raw["Versioning"]
    return _drop_none(out)


_TF_NORMALIZERS = {
    "aws_instance": _tf_ec2,
    "aws_security_group": _tf_sg,
    "aws_s3_bucket": _tf_s3,
}

_AWS_NORMALIZERS = {
    "aws_instance": _aws_ec2,
    "aws_security_group": _aws_sg,
    "aws_s3_bucket": _aws_s3,
}


def normalize(resource_type: str, source: str, raw: dict) -> dict[str, Any]:
    """Map a raw, source-specific attribute dict to canonical attributes.

    ``source`` is one of ``desired`` | ``recorded`` | ``actual``. Desired and
    recorded are both Terraform-shaped and share normalizers; actual is
    AWS-shaped.
    """
    table = _AWS_NORMALIZERS if source == ACTUAL else _TF_NORMALIZERS
    fn = table.get(resource_type)
    if fn is None:
        # Unknown type: keep scalar attributes so something is comparable.
        return {k: v for k, v in raw.items() if isinstance(v, (str, int, float, bool))}
    return fn(raw)
