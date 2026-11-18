from pathlib import Path
import sys

BASE_V015 = Path(__file__).resolve().parents[2] / "versions" / "TASK_DASH_002_implementation_v0_1_5"
SUPER_SELECTOR_APP = BASE_V015.parents[1]
if str(SUPER_SELECTOR_APP) not in sys.path:
    sys.path.insert(0, str(SUPER_SELECTOR_APP))
if str(BASE_V015) not in sys.path:
    sys.path.insert(0, str(BASE_V015))

