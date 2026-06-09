"""Resource resolver — expands Terraform ``count`` / ``for_each`` into instances.

See :mod:`engine.resolver.resolver`. Maps a Terraform resource block to the
concrete set of indexed addresses Terraform would manage, so the desired (HCL)
view lines up with the recorded (state) view in the diff engine.
"""

from engine.resolver.resolver import (
    resolve_hcl,
    resolve_hcl_data,
    resolve_hcl_text,
)

__all__ = ["resolve_hcl", "resolve_hcl_data", "resolve_hcl_text"]
