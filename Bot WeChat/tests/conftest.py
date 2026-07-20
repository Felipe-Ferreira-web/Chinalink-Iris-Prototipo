"""Stub de libs Windows-only, só pra permitir import fora do servidor."""

import sys
from unittest.mock import MagicMock

for _module_name in ("win32clipboard", "win32con"):
    try:
        __import__(_module_name)
    except ImportError:
        sys.modules[_module_name] = MagicMock()

try:
    from pywinauto import Desktop  # noqa: F401
except ImportError:
    sys.modules["pywinauto"] = MagicMock()
