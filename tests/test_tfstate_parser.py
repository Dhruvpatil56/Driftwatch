"""Tests for the Terraform state parser."""

from engine.parser.tfstate_parser import parse_tfstate, parse_tfstate_dict
from models.normalized import RECORDED


def test_parse_demo_state_returns_recorded_resources(tfstate_path):
    resources = {r.resource_address: r for r in parse_tfstate(tfstate_path)}
    assert set(resources) == {
        "aws_instance.web",
        "aws_security_group.web_sg",
        "aws_s3_bucket.data",
    }
    for r in resources.values():
        assert r.source == RECORDED


def test_cloud_id_comes_from_state_id(tfstate_path):
    resources = {r.resource_address: r for r in parse_tfstate(tfstate_path)}
    assert resources["aws_instance.web"].cloud_id == "i-0demo0web00000001"
    assert resources["aws_security_group.web_sg"].cloud_id == "sg-0demo0websg000001"
    assert resources["aws_s3_bucket.data"].cloud_id == "driftwatch-demo-data"


def test_data_sources_are_ignored():
    state = {
        "resources": [
            {"mode": "data", "type": "aws_ami", "name": "ubuntu", "instances": [{"attributes": {"id": "ami-x"}}]},
            {"mode": "managed", "type": "aws_instance", "name": "web", "instances": [{"attributes": {"id": "i-1", "instance_type": "t3.micro"}}]},
        ]
    }
    resources = parse_tfstate_dict(state)
    assert len(resources) == 1
    assert resources[0].resource_address == "aws_instance.web"


def test_count_index_produces_indexed_address():
    state = {
        "resources": [
            {
                "mode": "managed",
                "type": "aws_instance",
                "name": "web",
                "instances": [
                    {"index_key": 0, "attributes": {"id": "i-0", "instance_type": "t3.micro"}},
                    {"index_key": 1, "attributes": {"id": "i-1", "instance_type": "t3.micro"}},
                ],
            }
        ]
    }
    addresses = {r.resource_address for r in parse_tfstate_dict(state)}
    assert addresses == {"aws_instance.web[0]", "aws_instance.web[1]"}
