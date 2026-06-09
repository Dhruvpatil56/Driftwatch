"""Tests for the GitHub PR opener (Sprint 6, Goal 2).

No real network: when GITHUB_TOKEN/GITHUB_REPO are unset, open_pr must return
None without any HTTP call. The PR body formatting is checked directly.
"""

import pytest

from api import github_pr
from models.drift import INFRASTRUCTURE_DRIFT, DriftResult
from models.remediation import RemediationPatch


def _patch():
    return RemediationPatch(
        resource_address="aws_instance.web",
        patch_hcl='resource "aws_instance" "web" {\n  instance_type = "m5.large"\n}',
        import_command=None,
        description="Set instance_type to m5.large.",
    )


def _drift():
    return DriftResult(
        resource_address="aws_instance.web",
        drift_type=INFRASTRUCTURE_DRIFT,
        field="instance_type",
        desired="t3.micro",
        recorded="t3.micro",
        actual="m5.large",
        risk_impact="High",
    )


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    yield


def test_open_pr_skips_without_token(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("must not hit the network without a token")

    monkeypatch.setattr(github_pr.httpx, "Client", fail)
    assert github_pr.open_pr(_patch(), _drift()) is None


def test_open_pr_skips_without_repo(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_xxx")
    # GITHUB_REPO still unset -> disabled.
    assert github_pr.open_pr(_patch(), _drift()) is None


def test_slug_makes_branch_safe():
    assert github_pr._slug("aws_instance.web[0]") == "aws_instance.web-0"
    assert github_pr._slug('aws_instance.env["prod"]') == "aws_instance.env-prod"


def test_pr_body_contains_summary_and_footer():
    body = github_pr._pr_body(_patch(), _drift())
    assert "aws_instance.web" in body
    assert "High" in body  # risk
    assert "```hcl" in body
    assert "requires human review before merge" in body


def test_pr_body_includes_import_command_when_present():
    patch = _patch()
    patch.import_command = "terraform import aws_instance.web i-123"
    body = github_pr._pr_body(patch, _drift())
    assert "terraform import aws_instance.web i-123" in body
