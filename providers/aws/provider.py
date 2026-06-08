"""AWSProvider — scrapes live AWS resources via boto3.

Supports the Sprint 1 resource set: EC2 instances, S3 buckets, security groups.
Each AWS object is converted to a ``NormalizedResource`` (source = ``actual``)
via :func:`build_actual`, which is also reused by the offline demo loader so
both paths share one normalization codepath.

``resource_address`` is intentionally left blank for actual resources — the
cloud has no notion of a Terraform address. The diff engine matches actual
resources to their address using ``cloud_id``.
"""

from __future__ import annotations

from typing import Any

import boto3

from engine.parser.normalize import normalize
from models.normalized import ACTUAL, NormalizedResource
from providers.base import CloudProvider

DEFAULT_REGION = "ap-south-1"

# Terraform type -> the loader method on the provider.
_SUPPORTED = ("aws_instance", "aws_s3_bucket", "aws_security_group")


def _cloud_id(resource_type: str, raw: dict) -> str | None:
    if resource_type == "aws_instance":
        return raw.get("InstanceId")
    if resource_type == "aws_security_group":
        return raw.get("GroupId")
    if resource_type == "aws_s3_bucket":
        return raw.get("Name") or raw.get("bucket")
    return None


def build_actual(resource_type: str, raw: dict) -> NormalizedResource:
    """Build an actual ``NormalizedResource`` from a raw AWS API object."""
    return NormalizedResource(
        resource_address="",
        resource_type=resource_type,
        cloud_id=_cloud_id(resource_type, raw),
        attributes=normalize(resource_type, ACTUAL, raw),
        source=ACTUAL,
    )


class AWSProvider(CloudProvider):
    """Live AWS provider. Pass a custom boto3 ``session`` to inject fakes in
    tests; otherwise a default session is created for ``region``."""

    def __init__(self, region: str = DEFAULT_REGION, session: Any = None):
        self.region = region
        self._session = session or boto3.Session(region_name=region)

    # -- CloudProvider interface --------------------------------------------
    def list_resources(self, resource_types: list[str]) -> list[NormalizedResource]:
        out: list[NormalizedResource] = []
        if "aws_instance" in resource_types:
            out.extend(self._list_ec2())
        if "aws_s3_bucket" in resource_types:
            out.extend(self._list_s3())
        if "aws_security_group" in resource_types:
            out.extend(self._list_sg())
        return out

    def get_resource(self, resource_id: str) -> NormalizedResource:
        if resource_id.startswith("i-"):
            ec2 = self._session.client("ec2", region_name=self.region)
            resp = ec2.describe_instances(InstanceIds=[resource_id])
            for reservation in resp.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    return build_actual("aws_instance", inst)
        elif resource_id.startswith("sg-"):
            ec2 = self._session.client("ec2", region_name=self.region)
            resp = ec2.describe_security_groups(GroupIds=[resource_id])
            for group in resp.get("SecurityGroups", []):
                return build_actual("aws_security_group", group)
        else:
            # treat as an S3 bucket name
            return build_actual("aws_s3_bucket", {"Name": resource_id})
        raise ValueError(f"resource not found: {resource_id}")

    # -- per-service scrapers -----------------------------------------------
    def _list_ec2(self) -> list[NormalizedResource]:
        ec2 = self._session.client("ec2", region_name=self.region)
        resources: list[NormalizedResource] = []
        for page in _paginate(ec2.describe_instances):
            for reservation in page.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    state = inst.get("State", {}).get("Name")
                    if state == "terminated":
                        continue
                    resources.append(build_actual("aws_instance", inst))
        return resources

    def _list_sg(self) -> list[NormalizedResource]:
        ec2 = self._session.client("ec2", region_name=self.region)
        resources: list[NormalizedResource] = []
        for page in _paginate(ec2.describe_security_groups):
            for group in page.get("SecurityGroups", []):
                resources.append(build_actual("aws_security_group", group))
        return resources

    def _list_s3(self) -> list[NormalizedResource]:
        s3 = self._session.client("s3", region_name=self.region)
        resp = s3.list_buckets()
        resources: list[NormalizedResource] = []
        for bucket in resp.get("Buckets", []):
            raw = dict(bucket)
            # enrich with versioning status (best effort)
            try:
                versioning = s3.get_bucket_versioning(Bucket=bucket["Name"])
                raw["Versioning"] = versioning.get("Status", "Disabled")
            except Exception:
                pass
            # enrich with tags so tag drift is detectable. Buckets with no tags
            # raise NoSuchTagSet; treat that as an empty tag set.
            try:
                tagging = s3.get_bucket_tagging(Bucket=bucket["Name"])
                raw["TagSet"] = tagging.get("TagSet", [])
            except Exception:
                raw["TagSet"] = []
            resources.append(build_actual("aws_s3_bucket", raw))
        return resources


def _paginate(operation):
    """Yield every page of a boto3 operation that may support pagination.

    Falls back to a single call for fake clients in tests that don't implement
    ``can_paginate``/``get_paginator``.
    """
    can_paginate = getattr(operation, "__self__", None)
    if can_paginate is not None and hasattr(can_paginate, "get_paginator"):
        client = operation.__self__
        op_name = operation.__name__
        try:
            if client.can_paginate(op_name):
                yield from client.get_paginator(op_name).paginate()
                return
        except Exception:
            pass
    yield operation()
