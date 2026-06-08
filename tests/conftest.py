"""Shared test fixtures and paths."""

import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_DIR = os.path.join(ROOT, "terraform-demo")
FIXTURES_DIR = os.path.join(ROOT, "tests", "fixtures")


@pytest.fixture
def demo_dir():
    return DEMO_DIR


@pytest.fixture
def hcl_path():
    return os.path.join(DEMO_DIR, "main.tf")


@pytest.fixture
def tfstate_path():
    # Always the checked-in fixture (fake, valid-format IDs) — never the
    # gitignored, machine-specific terraform-demo/terraform.tfstate.
    return os.path.join(FIXTURES_DIR, "demo.tfstate")
