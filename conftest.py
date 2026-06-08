"""Root conftest — ensures the repository root is importable as the package
root for `models`, `engine`, and `providers` during test collection."""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
