"""Tests for the attribute normalization layer — the heart of cross-source
comparison."""

from engine.parser.normalize import normalize
from models.normalized import ACTUAL, DESIRED, RECORDED


def test_ec2_terraform_and_aws_normalize_to_same_keys():
    tf = normalize("aws_instance", DESIRED, {"instance_type": "t3.micro", "ami": "ami-1"})
    aws = normalize("aws_instance", ACTUAL, {"InstanceType": "t3.micro", "ImageId": "ami-1"})
    assert tf == aws == {"instance_type": "t3.micro", "ami": "ami-1"}


def test_s3_bucket_name_normalizes_across_sources():
    tf = normalize("aws_s3_bucket", RECORDED, {"bucket": "my-bucket", "id": "my-bucket"})
    aws = normalize("aws_s3_bucket", ACTUAL, {"Name": "my-bucket"})
    assert tf["bucket"] == aws["bucket"] == "my-bucket"


def test_s3_tags_normalize_to_same_dict_across_sources():
    # Terraform stores a dict; AWS returns a TagSet list — both collapse equal.
    tf = normalize("aws_s3_bucket", RECORDED, {"bucket": "b", "tags": {"Name": "b", "Env": "prod"}})
    aws = normalize(
        "aws_s3_bucket",
        ACTUAL,
        {"Name": "b", "TagSet": [{"Key": "Env", "Value": "prod"}, {"Key": "Name", "Value": "b"}]},
    )
    assert tf["tags"] == aws["tags"] == {"Env": "prod", "Name": "b"}


def test_s3_untagged_normalizes_to_empty_tags():
    assert normalize("aws_s3_bucket", ACTUAL, {"Name": "b"})["tags"] == {}
    assert normalize("aws_s3_bucket", RECORDED, {"bucket": "b"})["tags"] == {}


def test_sg_ingress_rule_matches_between_terraform_and_aws():
    tf = normalize(
        "aws_security_group",
        DESIRED,
        {
            "name": "sg",
            "ingress": [
                {"protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]}
            ],
        },
    )
    aws = normalize(
        "aws_security_group",
        ACTUAL,
        {
            "GroupName": "sg",
            "IpPermissions": [
                {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
            ],
        },
    )
    assert tf["ingress"] == aws["ingress"] == ["tcp:443-443:0.0.0.0/0"]


def test_sg_all_traffic_egress_collapses_to_same_key():
    # Terraform shape uses protocol "-1" with from/to ports; AWS omits the ports.
    tf = normalize(
        "aws_security_group",
        DESIRED,
        {"name": "sg", "egress": [{"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}]},
    )
    aws = normalize(
        "aws_security_group",
        ACTUAL,
        {"GroupName": "sg", "IpPermissionsEgress": [{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]},
    )
    assert tf["egress"] == aws["egress"] == ["-1:all:0.0.0.0/0"]


def test_unknown_type_keeps_scalars_only():
    out = normalize("aws_widget", DESIRED, {"size": 3, "name": "w", "nested": {"x": 1}})
    assert out == {"size": 3, "name": "w"}
