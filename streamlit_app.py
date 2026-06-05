"""Root entrypoint for Streamlit Community Cloud."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
APP_PATH = PROJECT_ROOT / "app" / "streamlit_app.py"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

runpy.run_path(str(APP_PATH), run_name="__main__")
