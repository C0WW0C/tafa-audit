# TAFA V7 PRO — core package
from __future__ import annotations

# Path bootstrap for Windows when imported as top-level package
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
