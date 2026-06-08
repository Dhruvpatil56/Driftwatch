"""Tests for the three-way diff engine — the integration point of classifier,
matching, and scorer."""

from engine.diff.diff_engine import reconcile
from models.drift import INFRASTRUCTURE_DRIFT, OWNERSHIP_DRIFT
from models.normalized import ACTUAL, DESIRED, RECORDED, NormalizedResource


def _r(address, rtype, source, attrs, cloud_id=None):
    return NormalizedResource(
        resource_address=address,
        resource_type=rtype,
        cloud_id=cloud_id,
        attributes=attrs,
        source=source,
    )


def test_infrastructure_drift_on_instance_type():
    desired = [_r("aws_instance.web", "aws_instance", DESIRED, {"instance_type": "t3.micro"})]
    recorded = [_r("aws_instance.web", "aws_instance", RECORDED, {"instance_type": "t3.micro"}, cloud_id="i-1")]
    actual = [_r("", "aws_instance", ACTUAL, {"instance_type": "m5.large"}, cloud_id="i-1")]

    drifts = reconcile(desired, recorded, actual)

    assert len(drifts) == 1
    d = drifts[0]
    assert d.resource_address == "aws_instance.web"
    assert d.drift_type == INFRASTRUCTURE_DRIFT
    assert d.field == "instance_type"
    assert (d.desired, d.recorded, d.actual) == ("t3.micro", "t3.micro", "m5.large")
    # scored
    assert d.risk_impact == "Low"
    assert d.cost_impact == "Unknown"


def test_actual_matched_to_address_by_cloud_id():
    # actual carries no address; it must be matched via the recorded cloud_id
    desired = [_r("aws_instance.web", "aws_instance", DESIRED, {"instance_type": "t3.micro"})]
    recorded = [_r("aws_instance.web", "aws_instance", RECORDED, {"instance_type": "t3.micro"}, cloud_id="i-1")]
    actual = [_r("", "aws_instance", ACTUAL, {"instance_type": "t3.micro"}, cloud_id="i-1")]

    assert reconcile(desired, recorded, actual) == []


def test_orphan_actual_is_ownership_drift():
    actual = [_r("", "aws_instance", ACTUAL, {"instance_type": "t2.nano"}, cloud_id="i-orphan")]
    drifts = reconcile([], [], actual)
    assert len(drifts) == 1
    assert drifts[0].drift_type == OWNERSHIP_DRIFT
    assert drifts[0].actual == "i-orphan"
    assert drifts[0].risk_impact == "Medium"


def test_in_sync_resource_produces_no_drift():
    desired = [_r("aws_s3_bucket.data", "aws_s3_bucket", DESIRED, {"bucket": "b"})]
    recorded = [_r("aws_s3_bucket.data", "aws_s3_bucket", RECORDED, {"bucket": "b"}, cloud_id="b")]
    actual = [_r("", "aws_s3_bucket", ACTUAL, {"bucket": "b"}, cloud_id="b")]
    assert reconcile(desired, recorded, actual) == []


def test_s3_tag_drift_is_detected():
    # desired == recorded tags, but an out-of-band tag was added in the cloud
    tf_tags = {"Name": "b"}
    aws_tags = {"Name": "b", "Environment": "prod"}
    desired = [_r("aws_s3_bucket.data", "aws_s3_bucket", DESIRED, {"bucket": "b", "tags": tf_tags})]
    recorded = [_r("aws_s3_bucket.data", "aws_s3_bucket", RECORDED, {"bucket": "b", "tags": tf_tags}, cloud_id="b")]
    actual = [_r("", "aws_s3_bucket", ACTUAL, {"bucket": "b", "tags": aws_tags}, cloud_id="b")]

    drifts = reconcile(desired, recorded, actual)

    assert len(drifts) == 1
    assert drifts[0].field == "tags"
    assert drifts[0].drift_type == INFRASTRUCTURE_DRIFT


def test_deleted_out_of_band_is_configuration_drift():
    desired = [_r("aws_instance.web", "aws_instance", DESIRED, {"instance_type": "t3.micro"})]
    recorded = [_r("aws_instance.web", "aws_instance", RECORDED, {"instance_type": "t3.micro"}, cloud_id="i-1")]
    # actual empty -> the instance vanished from the cloud
    drifts = reconcile(desired, recorded, [])
    assert len(drifts) == 1
    assert drifts[0].drift_type == "Configuration Drift"
    assert drifts[0].actual == "missing"
    assert drifts[0].risk_impact == "High"
