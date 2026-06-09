# DriftWatch governance policies.
package driftwatch.policies

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# --- tunables --------------------------------------------------------------
approved_instance_types := {"t2.micro", "t3.nano", "t3.micro", "t3.small", "t3.medium"}
required_s3_tags := {"Name", "Environment"}
severity_rank := {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}

# --- helpers ---------------------------------------------------------------
is_sg_rule_field if input.field in {"ingress", "egress"}
open_to_world if contains(input.actual, "0.0.0.0/0")
exposes_port(port) if contains(input.actual, sprintf(":%v-", [port]))

# --- violations ------------------------------------------------------------
violations contains v if {
    is_sg_rule_field
    open_to_world
    exposes_port("22")
    v := {"risk": "Critical", "governance": sprintf("SSH (port 22) open to 0.0.0.0/0 on %s", [input.resource_address])}
}

violations contains v if {
    is_sg_rule_field
    open_to_world
    exposes_port("3389")
    v := {"risk": "Critical", "governance": sprintf("RDP (port 3389) open to 0.0.0.0/0 on %s", [input.resource_address])}
}

violations contains v if {
    input.resource_type == "aws_s3_bucket"
    input.field == "tags"
    some tag in required_s3_tags
    not contains(input.actual, tag)
    v := {"risk": "Medium", "governance": sprintf("S3 bucket %s missing required tag '%s'", [input.resource_address, tag])}
}

violations contains v if {
    input.resource_type == "aws_instance"
    input.field == "instance_type"
    input.actual != ""
    not input.actual in approved_instance_types
    v := {"risk": "Medium", "governance": sprintf("EC2 instance type '%s' not in approved list", [input.actual])}
}

violations contains v if {
    input.drift_type == "Ownership Drift"
    v := {"risk": "Medium", "governance": "Untracked resource - exists in cloud but absent from Terraform"}
}

# --- decision: pick highest severity, deduplicate by taking sorted first ---
default decision = {"risk": "Low", "governance": "None"}

max_rank := max({r | some v in violations; r := severity_rank[v.risk]}) if {
    count(violations) > 0
}

top_violations := [v | some v in violations; severity_rank[v.risk] == max_rank]

decision := top_violations[0] if {
    count(violations) > 0
    count(top_violations) > 0
}
