# DriftWatch governance policies (Sprint 5).
#
# OPA evaluates one DriftResult at a time and returns a single decision:
#   { "risk": "<Low|Medium|High|Critical>", "governance": "<message>" }
#
# The scorer (engine/scorer/scorer.py) POSTs the drift as `input` to
#   /v1/data/driftwatch/policies/decision
# and applies the returned risk/governance. If OPA is unreachable the scorer
# falls back to its built-in Python rules, so these policies are never a hard
# dependency.
#
# Input shape (built by engine.scorer.scorer._opa_input):
#   {
#     "resource_address": "aws_security_group.web_sg",
#     "resource_type":    "aws_security_group",
#     "drift_type":       "Infrastructure Drift",
#     "field":            "ingress",
#     "desired":          "...",
#     "recorded":         "...",
#     "actual":           "tcp:22-22:0.0.0.0/0"
#   }
#
# Security-group rules arrive pre-normalized as "proto:from-to:cidr,cidr"
# (see engine/parser/normalize.py::_rule_key), e.g. "tcp:22-22:0.0.0.0/0".

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

# Normalized port range is "<from>-<to>"; an exact single-port rule for N is
# rendered ":N-". Anchoring on ":N-" avoids matching e.g. 2222 for 22.
exposes_port(port) if contains(input.actual, sprintf(":%v-", [port]))

# --- policies (each may add at most one violation) -------------------------

# 1. SG open to the world on port 22 (SSH) -> Critical
violations contains v if {
	is_sg_rule_field
	open_to_world
	exposes_port("22")
	v := {
		"risk": "Critical",
		"governance": sprintf("SSH (port 22) open to 0.0.0.0/0 on %s", [input.resource_address]),
	}
}

# 2. SG open to the world on port 3389 (RDP) -> Critical
violations contains v if {
	is_sg_rule_field
	open_to_world
	exposes_port("3389")
	v := {
		"risk": "Critical",
		"governance": sprintf("RDP (port 3389) open to 0.0.0.0/0 on %s", [input.resource_address]),
	}
}

# 3. S3 bucket missing a required tag -> Medium
violations contains v if {
	input.resource_type == "aws_s3_bucket"
	input.field == "tags"
	some tag in required_s3_tags
	not contains(input.actual, tag)
	v := {
		"risk": "Medium",
		"governance": sprintf("S3 bucket %s missing required tag '%s'", [input.resource_address, tag]),
	}
}

# 4. EC2 instance type not in the approved list -> High
violations contains v if {
	input.resource_type == "aws_instance"
	input.field == "instance_type"
	input.actual != ""
	not input.actual in approved_instance_types
	v := {
		"risk": "High",
		"governance": sprintf("EC2 instance type '%s' not in approved list", [input.actual]),
	}
}

# 5. Unmanaged resource (Ownership Drift) -> Medium
violations contains v if {
	input.drift_type == "Ownership Drift"
	v := {
		"risk": "Medium",
		"governance": "Untracked resource - exists in cloud but absent from Terraform",
	}
}

# --- decision: highest-severity violation, else Low/None -------------------
max_rank := max([r | some v in violations; r := severity_rank[v.risk]])

decision := v if {
	count(violations) > 0
	some v in violations
	severity_rank[v.risk] == max_rank
} else := {"risk": "Low", "governance": "None"}
