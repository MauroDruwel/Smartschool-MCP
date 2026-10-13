"""
Shared pytest fixtures for the Smartschool MCP test suite.

All unit tests run without real Smartschool credentials.
The ``mock_session`` fixture patches the lazy ``_session()`` singleton so no
network connections are made during the test run.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import smartschool

# TEMPORARY SHIM -- REMOVE as soon as pyproject.toml / uv.lock require the
# smartschool release that contains StudentNotes (module ``_student_notes.py``).
# Until then the locked smartschool lacks these names, so ``smartschool_mcp.server``
# could not be imported.  Tests that use the real library objects
# (tests/test_student_notes_tools.py) are skipped while the shim is active.
for _name in ("StudentNotes", "StudentAbsences", "StudentNoteDetails"):
    if not hasattr(smartschool, _name):
        setattr(smartschool, _name, type(_name, (), {}))


@pytest.fixture(autouse=True)
def mock_session() -> MagicMock:
    """Replace the cached Smartschool session with a MagicMock.

    Applied automatically to every test in this suite.  Tests that need to
    configure specific return values can request this fixture explicitly.
    """
    mock = MagicMock()
    with patch("smartschool_mcp.server._session", return_value=mock):
        yield mock
