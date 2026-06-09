"""Tests for the resource resolver (engine/resolver).

The resolver expands Terraform ``count`` / ``for_each`` meta-arguments into the
concrete, indexed addresses Terraform would manage — so the desired (HCL) view
lines up with the recorded (state) view in the diff engine.

Per the permanent test rules: no real AWS IDs, assert shape/format only, and
use tests/fixtures/ for any state/HCL on disk.
"""

import os

import pytest

from engine.parser.tfstate_parser import _address
from engine.resolver import resolve_hcl, resolve_hcl_data, resolve_hcl_text
from models.normalized import DESIRED

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


@pytest.fixture
def meta_tf_path():
    return os.path.join(FIXTURES_DIR, "resolver_meta.tf")


def _by_addr(resources):
    return {r.resource_address: r for r in resources}


# --- simple resources (build order step 1: verify unchanged) ---------------
def test_simple_resource_passes_through_with_base_address():
    resources = resolve_hcl_text(
        """
        resource "aws_instance" "web" {
          ami           = "ami-0simple000000001"
          instance_type = "t3.micro"
        }
        """
    )
    assert len(resources) == 1
    r = resources[0]
    assert r.resource_address == "aws_instance.web"
    assert r.resource_type == "aws_instance"
    assert r.source == DESIRED
    assert r.cloud_id is None
    assert r.get("instance_type") == "t3.micro"
    # Shape/format only — never a hardcoded AMI.
    assert r.get("ami", "").startswith("ami-")


# --- count -----------------------------------------------------------------
def test_count_expands_to_indexed_addresses():
    resources = resolve_hcl_text(
        """
        resource "aws_instance" "web" {
          count         = 3
          ami           = "ami-0count0000000001"
          instance_type = "t3.micro"
        }
        """
    )
    addresses = [r.resource_address for r in resources]
    assert addresses == [
        "aws_instance.web[0]",
        "aws_instance.web[1]",
        "aws_instance.web[2]",
    ]
    for r in resources:
        assert r.source == DESIRED
        assert r.get("instance_type") == "t3.micro"


def test_count_addresses_match_tfstate_parser_format():
    # The diff engine matches desired<->recorded by address, so the resolver
    # must produce exactly what the state parser produces for count instances.
    resources = resolve_hcl_text(
        'resource "aws_instance" "web" { count = 2 ami = "ami-0x" instance_type = "t3.micro" }'
    )
    addresses = {r.resource_address for r in resources}
    expected = {_address("aws_instance", "web", i) for i in range(2)}
    assert addresses == expected


def test_count_zero_produces_no_instances():
    resources = resolve_hcl_text(
        'resource "aws_instance" "web" { count = 0 ami = "ami-0x" instance_type = "t3.micro" }'
    )
    assert resources == []


def test_count_index_interpolation_is_resolved():
    # Unknown type uses the passthrough normalizer, so scalar attrs survive and
    # we can observe the substituted count.index.
    resources = resolve_hcl_text(
        """
        resource "aws_thing" "n" {
          count = 2
          name  = "thing-${count.index}"
        }
        """
    )
    by_addr = _by_addr(resources)
    assert by_addr["aws_thing.n[0]"].get("name") == "thing-0"
    assert by_addr["aws_thing.n[1]"].get("name") == "thing-1"


def test_count_meta_arg_does_not_leak_into_attributes():
    resources = resolve_hcl_text(
        'resource "aws_thing" "n" { count = 1 name = "x" }'
    )
    assert "count" not in resources[0].attributes


# --- for_each --------------------------------------------------------------
def test_for_each_map_expands_to_quoted_string_keys():
    resources = resolve_hcl_text(
        """
        resource "aws_instance" "env" {
          for_each      = { prod = "t3.large", staging = "t3.micro" }
          ami           = "ami-0each0000000001"
          instance_type = each.value
        }
        """
    )
    by_addr = _by_addr(resources)
    assert set(by_addr) == {
        'aws_instance.env["prod"]',
        'aws_instance.env["staging"]',
    }
    # each.value resolved per instance.
    assert by_addr['aws_instance.env["prod"]'].get("instance_type") == "t3.large"
    assert by_addr['aws_instance.env["staging"]'].get("instance_type") == "t3.micro"


def test_for_each_addresses_match_tfstate_parser_format():
    resources = resolve_hcl_text(
        'resource "aws_instance" "env" { for_each = { prod = "t3.large" } '
        'ami = "ami-0x" instance_type = each.value }'
    )
    addresses = {r.resource_address for r in resources}
    assert addresses == {_address("aws_instance", "env", "prod")}


def test_for_each_keys_are_sorted():
    resources = resolve_hcl_text(
        'resource "aws_thing" "n" { for_each = { c = "1", a = "2", b = "3" } '
        'name = each.key }'
    )
    keys = [r.resource_address for r in resources]
    assert keys == [
        'aws_thing.n["a"]',
        'aws_thing.n["b"]',
        'aws_thing.n["c"]',
    ]


def test_for_each_each_key_interpolation_is_resolved():
    resources = resolve_hcl_text(
        'resource "aws_thing" "n" { for_each = { prod = "x" } name = "env-${each.key}" }'
    )
    assert resources[0].get("name") == "env-prod"


def test_for_each_set_uses_element_as_key_and_value():
    resources = resolve_hcl_text(
        'resource "aws_thing" "n" { for_each = ["a", "b"] name = each.value }'
    )
    by_addr = _by_addr(resources)
    assert set(by_addr) == {'aws_thing.n["a"]', 'aws_thing.n["b"]'}
    assert by_addr['aws_thing.n["a"]'].get("name") == "a"


def test_for_each_meta_arg_does_not_leak_into_attributes():
    resources = resolve_hcl_text(
        'resource "aws_thing" "n" { for_each = { a = "1" } name = "x" }'
    )
    assert "for_each" not in resources[0].attributes


# --- file / dir entry points + multiple blocks -----------------------------
def test_resolve_hcl_file_expands_both_meta_args(meta_tf_path):
    resources = resolve_hcl(meta_tf_path)
    addresses = {r.resource_address for r in resources}
    assert addresses == {
        "aws_instance.web[0]",
        "aws_instance.web[1]",
        "aws_instance.web[2]",
        'aws_instance.env["prod"]',
        'aws_instance.env["staging"]',
    }
    for r in resources:
        assert r.get("ami", "").startswith("ami-")


def test_resolve_hcl_data_handles_multiple_blocks():
    data = {
        "resource": [
            {"aws_instance": {"a": {"count": 2, "instance_type": "t3.micro", "ami": "ami-0x"}}},
            {"aws_s3_bucket": {"b": {"bucket": "my-bucket"}}},
        ]
    }
    resources = resolve_hcl_data(data)
    addresses = {r.resource_address for r in resources}
    assert addresses == {
        "aws_instance.a[0]",
        "aws_instance.a[1]",
        "aws_s3_bucket.b",
    }


# --- unsupported / computed values ----------------------------------------
def test_computed_count_raises():
    with pytest.raises(ValueError):
        resolve_hcl_text(
            'resource "aws_thing" "n" { count = "${length(var.subnets)}" name = "x" }'
        )
