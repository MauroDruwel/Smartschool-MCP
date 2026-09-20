"""Live portal smoke wrapper. Never runs unless PORTAL_SMOKE=1."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke_portal.py"
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import smoke_portal as smoke  # noqa: E402


@pytest.mark.integration
def test_portal_smoke() -> None:
    if os.environ.get("PORTAL_SMOKE") != "1":
        pytest.skip("Set PORTAL_SMOKE=1 to run the live portal smoke test")
    smoke.load_dotenv(REPO_ROOT / ".env")
    if smoke.missing_credentials():
        pytest.skip("SMARTSCHOOL_USERNAME / PASSWORD / MAIN_URL required")

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            f"smoke_portal.py exited {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
