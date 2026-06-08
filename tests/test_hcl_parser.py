"""Tests for the HCL parser against the demo Terraform."""

from engine.parser.hcl_parser import parse_hcl
from models.normalized import DESIRED


def test_parse_demo_hcl_returns_three_resources(hcl_path):
    resources = parse_hcl(hcl_path)
    addresses = {r.resource_address for r in resources}
    assert addresses == {
        "aws_instance.web",
        "aws_security_group.web_sg",
        "aws_s3_bucket.data",
    }


def test_parsed_resources_are_desired_with_no_cloud_id(hcl_path):
    resources = parse_hcl(hcl_path)
    for r in resources:
        assert r.source == DESIRED
        assert r.cloud_id is None


def test_ec2_attributes_are_normalized(hcl_path):
    resources = {r.resource_address: r for r in parse_hcl(hcl_path)}
    web = resources["aws_instance.web"]
    assert web.get("instance_type") == "t3.micro"
    assert web.get("ami") == "ami-0abcdef1234567890"


def test_parse_directory_discovers_tf_files(demo_dir):
    # Passing the directory should find main.tf inside it.
    resources = parse_hcl(demo_dir)
    assert any(r.resource_address == "aws_instance.web" for r in resources)
