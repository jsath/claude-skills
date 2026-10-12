#!/usr/bin/env python3
"""Entry point: python3 scripts/longform_edit.py <inbox>/<slug>/ [options]. See SKILL.md and --help."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lf.pipeline import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
