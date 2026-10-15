#!/usr/bin/env python3
"""Wrapper around lib/msc_mvp_router.py to keep scripts/ and lib/ consistent."""
from pathlib import Path
import sys

ROUTER_LIB = Path(__file__).resolve().parent.parent / "lib" / "msc_mvp_router.py"

if __name__ == "__main__":
    import runpy
    sys.path.insert(0, str(ROUTER_LIB.parent))
    runpy.run_path(str(ROUTER_LIB), run_name="__main__")