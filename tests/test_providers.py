"""Tests for the cloud providers.

AWSProvider is exercised with a fake boto3 session (no network); GCPProvider is
verified to be an unimplemented stub.
"""

import pytest

from models.normalized import ACTUAL
from providers.aws.provider import AWSProvider, build_actual
from providers.gcp.provider import GCPProvider


# --- fake boto3 plumbing ---------------------------------------------------
class _FakeEC2:
    def __init__(self, instances, sgs):
        self._instances = instances
        self._sgs = sgs

    def describe_instances(self, **kwargs):
        return {"Reservations": [{"Instances": self._instances}]}

    def describe_security_groups(self, **kwargs):
        return {"SecurityGroups": self._sgs}


class _FakeS3:
    def __init__(self, buckets, versioning=None, tags=None):
        self._buckets = buckets
        self._versioning = versioning or {}
        self._tags = tags or {}  # bucket name -> {key: value}

    def list_buckets(self):
        return {"Buckets": self._buckets}

    def get_bucket_versioning(self, Bucket):
        return {"Status": self._versioning.get(Bucket, "Disabled")}

    def get_bucket_tagging(self, Bucket):
        if Bucket not in self._tags:
            # mirror the real API, which raises NoSuchTagSet for untagged buckets
            raise Exception("NoSuchTagSet")
        return {"TagSet": [{"Key": k, "Value": v} for k, v in self._tags[Bucket].items()]}


class _FakeSession:
    def __init__(self, ec2, s3):
        self._ec2 = ec2
        self._s3 = s3

    def client(self, name, region_name=None):
        return {"ec2": self._ec2, "s3": self._s3}[name]


@pytest.fixture
def fake_provider():
    ec2 = _FakeEC2(
        instances=[
            {"InstanceId": "i-1", "InstanceType": "t3.micro", "ImageId": "ami-1", "State": {"Name": "running"}},
            {"InstanceId": "i-dead", "InstanceType": "t3.micro", "ImageId": "ami-1", "State": {"Name": "terminated"}},
        ],
        sgs=[
            {
                "GroupId": "sg-1",
                "GroupName": "web",
                "Description": "web sg",
                "IpPermissions": [
                    {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
                ],
                "IpPermissionsEgress": [],
            }
        ],
    )
    s3 = _FakeS3(
        buckets=[{"Name": "my-bucket"}],
        versioning={"my-bucket": "Enabled"},
        tags={"my-bucket": {"Name": "my-bucket", "Environment": "prod"}},
    )
    return AWSProvider(region="ap-south-1", session=_FakeSession(ec2, s3))


def test_build_actual_sets_cloud_id_and_source():
    r = build_actual("aws_instance", {"InstanceId": "i-9", "InstanceType": "t3.micro"})
    assert r.cloud_id == "i-9"
    assert r.source == ACTUAL
    assert r.resource_address == ""
    assert r.get("instance_type") == "t3.micro"


def test_list_ec2_skips_terminated(fake_provider):
    instances = fake_provider.list_resources(["aws_instance"])
    assert len(instances) == 1
    assert instances[0].cloud_id == "i-1"
    assert instances[0].get("instance_type") == "t3.micro"


def test_list_sg_normalizes_ingress(fake_provider):
    sgs = fake_provider.list_resources(["aws_security_group"])
    assert len(sgs) == 1
    assert sgs[0].cloud_id == "sg-1"
    assert sgs[0].get("ingress") == ["tcp:443-443:0.0.0.0/0"]


def test_list_s3_includes_versioning(fake_provider):
    buckets = fake_provider.list_resources(["aws_s3_bucket"])
    assert len(buckets) == 1
    assert buckets[0].cloud_id == "my-bucket"
    assert buckets[0].get("bucket") == "my-bucket"
    assert buckets[0].get("versioning") == "Enabled"


def test_list_s3_includes_tags(fake_provider):
    buckets = fake_provider.list_resources(["aws_s3_bucket"])
    assert buckets[0].get("tags") == {"Environment": "prod", "Name": "my-bucket"}


def test_list_s3_untagged_bucket_yields_empty_tags():
    s3 = _FakeS3(buckets=[{"Name": "no-tags"}])  # no tags registered -> NoSuchTagSet
    provider = AWSProvider(region="ap-south-1", session=_FakeSession(_FakeEC2([], []), s3))
    buckets = provider.list_resources(["aws_s3_bucket"])
    assert buckets[0].get("tags") == {}


def test_list_resources_filters_by_type(fake_provider):
    only_ec2 = fake_provider.list_resources(["aws_instance"])
    assert all(r.resource_type == "aws_instance" for r in only_ec2)


def test_get_resource_by_instance_id(fake_provider):
    r = fake_provider.get_resource("i-1")
    assert r.resource_type == "aws_instance"
    assert r.cloud_id == "i-1"


def test_gcp_provider_is_stub():
    gcp = GCPProvider()
    with pytest.raises(NotImplementedError):
        gcp.list_resources(["aws_instance"])
    with pytest.raises(NotImplementedError):
        gcp.get_resource("x")
