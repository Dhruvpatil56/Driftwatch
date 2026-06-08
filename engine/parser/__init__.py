"""Terraform parsers and the attribute normalization layer."""

from engine.parser.hcl_parser import parse_hcl, parse_hcl_dir, parse_hcl_file
from engine.parser.normalize import normalize
from engine.parser.tfstate_parser import parse_tfstate, parse_tfstate_dict

__all__ = [
    "parse_hcl",
    "parse_hcl_file",
    "parse_hcl_dir",
    "parse_tfstate",
    "parse_tfstate_dict",
    "normalize",
]
