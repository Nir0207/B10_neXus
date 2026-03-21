from __future__ import annotations

import sys
from pathlib import Path

API_GATEWAY_ROOT = Path(__file__).resolve().parents[1]
if str(API_GATEWAY_ROOT) not in sys.path:
    sys.path.insert(0, str(API_GATEWAY_ROOT))
