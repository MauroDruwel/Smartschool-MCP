"""Offline classifier tests for the portal URL smoke plan.

These tests never hit the network. They load docs/portal-api/catalog.yml and
assert write/auth/XML rows are skipped while legacy library reads stay hittable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import smoke_portal as smoke  # noqa: E402

CATALOG = smoke.load_catalog()


def _by_library(name: str) -> smoke.CatalogEndpoint:
    for ep in CATALOG:
        if ep.library == name:
            return ep
    raise AssertionError(f"no catalog row with library={name!r}")


def _by_path_method(path: str, method: str = "GET") -> smoke.CatalogEndpoint:
    method = method.upper()
    for ep in CATALOG:
        if ep.path == path and ep.method == method:
            return ep
    raise AssertionError(f"no catalog row {method} {path}")


def test_catalog_is_loaded() -> None:
    assert len(CATALOG) >= 33
    assert any(ep.is_legacy for ep in CATALOG)


def test_legacy_agenda_and_tasks_are_library_hits() -> None:
    lessons = _by_library("SmartschoolLessons")
    tasks = _by_library("FutureTasks")
    attachments = _by_library("Attachments")
    assert lessons.is_legacy
    assert tasks.is_legacy
    assert smoke.classify(lessons) == smoke.HIT_LIBRARY
    assert smoke.classify(tasks) == smoke.HIT_LIBRARY
    assert smoke.classify(attachments) == smoke.HIT_LIBRARY


def test_writes_and_composer_are_skipped() -> None:
    assert smoke.classify(_by_library("MessageComposerForm")) == smoke.SKIP_WRITE
    assert smoke.classify(_by_library("MarkMessageUnread")) == smoke.SKIP_WRITE
    delete_file = _by_path_method("/mydoc/api/v1/files/{fileId}", "DELETE")
    assert smoke.classify(delete_file) == smoke.SKIP_WRITE
    create_todo = _by_path_method("/planner/api/v1/planned-to-dos/", "POST")
    assert smoke.classify(create_todo) == smoke.SKIP_WRITE


def test_auth_and_csrf_are_skipped() -> None:
    login = _by_path_method("/login", "POST")
    token = _by_path_method("/Topnav/Node/getToken", "POST")
    assert smoke.classify(login) == smoke.SKIP_AUTH
    assert smoke.classify(token) == smoke.SKIP_AUTH


def test_unmapped_xml_posts_are_skipped() -> None:
    matches = [
        ep for ep in CATALOG if ep.xml_action == "postboxes/calculate_postbox_counters"
    ]
    assert matches
    assert smoke.classify(matches[0]) == smoke.SKIP_UNMAPPED_XML


def test_live_gets_prefer_raw_http() -> None:
    pinned = _by_path_method("/planner/api/v1/planned-elements/pinned")
    assert smoke.classify(pinned, prefer_get=True) == smoke.HIT_GET
    planned = _by_library("PlannedElements")
    assert smoke.classify(planned, prefer_get=False) == smoke.HIT_LIBRARY
    assert smoke.classify(planned, prefer_get=True) == smoke.HIT_GET


def test_every_row_gets_a_known_decision() -> None:
    known = {
        smoke.SKIP_WRITE,
        smoke.SKIP_AUTH,
        smoke.SKIP_UNMAPPED_XML,
        smoke.SKIP_UNMAPPED_POST,
        smoke.HIT_LIBRARY,
        smoke.HIT_GET,
    }
    for ep in CATALOG:
        prefer_get = ep.method == "GET" and not ep.is_legacy
        decision = smoke.classify(ep, prefer_get=prefer_get)
        assert decision in known, f"{ep.method} {ep.label} -> {decision}"


def test_cli_exits_when_credentials_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smoke, "load_dotenv", lambda path: None)
    for key in (
        "SMARTSCHOOL_USERNAME",
        "SMARTSCHOOL_PASSWORD",
        "SMARTSCHOOL_MAIN_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    assert smoke.main(["--legacy-only"]) == 2


def test_load_dotenv_strips_inline_comments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SMARTSCHOOL_MFA=2014-11-12 # date of birth\n", encoding="utf-8"
    )
    monkeypatch.delenv("SMARTSCHOOL_MFA", raising=False)
    smoke.load_dotenv(env_file)
    assert os.environ["SMARTSCHOOL_MFA"] == "2014-11-12"


def test_format_table_does_not_put_exceptions_in_items() -> None:
    text = smoke.format_table(
        [
            smoke.SmokeResult(
                phase=1,
                method="GET",
                label="/lesson-content/api/v1/assignments/applicable-assigment-types",
                library="ApplicableAssignmentTypes",
                outcome="http_4xx",
                http="403",
                note="SmartSchoolDownloadError",
            )
        ]
    )
    items_header_at = text.splitlines()[0].index("ITEMS")
    data = text.splitlines()[2]
    items_cell = data[items_header_at : items_header_at + 5].strip()
    assert items_cell in {"-", "0"} or items_cell.isdigit()
    assert "SmartSchoolDownloadError" not in items_cell
    assert "http_4xx" in data
    assert "403" in data
