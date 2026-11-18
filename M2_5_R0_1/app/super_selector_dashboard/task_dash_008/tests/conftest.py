from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
V015_ROOT = APP_ROOT / "versions" / "TASK_DASH_002_implementation_v0_1_5"
for path in (APP_ROOT, V015_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
