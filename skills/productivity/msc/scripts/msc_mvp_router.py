#!/usr/bin/env python3
"""
Wrapper script forwarding execution to the primary router in the lib directory
to eliminate code drift and duplicate implementations.
"""
import sys
from pathlib import Path

# Add the lib directory to sys.path
SKILL_ROOT = Path(__file__).parent.parent
lib_dir = SKILL_ROOT / "lib"
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

import msc_mvp_router

if __name__ == "__main__":
    msc_mvp_router.main()