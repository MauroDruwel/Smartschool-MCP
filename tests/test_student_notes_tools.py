"""Tests for get_student_notes / get_student_absences.

All data is synthetic.  The tests build real ``StudentNote``/``StudentAbsence``/
``StudentNoteDetail`` objects from the smartschool library and patch the poster
classes with ``autospec``, so a wrong method or attribute name fails the test
instead of being accepted by a permissive MagicMock.  They need a smartschool
release that contains the student-notes classes and are skipped before that.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest
import smartschool

import smartschool_mcp.server as srv

_HAS_LIB = hasattr(smartschool, "StudentNote") and hasattr(
    smartschool, "StudentNoteDetail"
)
needs_lib = pytest.mark.skipif(
    not _HAS_LIB, reason="smartschool release with StudentNotes not installed"
)


def _epoch(day: date) -> int:
    return int(
        datetime(day.year, day.month, day.day, 9, tzinfo=timezone.utc).timestamp()
    )


def _note(
    item_id: int,
    day: date,
    *,
    cat: str = "Mededeling",
    private: bool = False,
) -> Any:
    return smartschool.StudentNote(
        item_id=item_id,
        group_id=1,
        pupil_id=2,
        cat_id=3,
        cat_name=cat,
        title="Synthetische titel",
        date=_epoch(day),
        author="Voorbeeld Leerkracht",
        author_reverse="Leerkracht Voorbeeld",
        viewed=False,
        private=private,
        school_year="2026-2027",
        study_direction=None,
    )


def _detail(item_id: int, html: str = "<p>Synthetische <b>tekst</b></p>") -> Any:
    return smartschool.StudentNoteDetail(
        item_id=item_id,
        params=[
            smartschool.StudentNoteParam(
                param_id=231, param_type=2, title="Mededeling", value=html
            ),
            smartschool.StudentNoteParam(
                param_id=227,
                param_type=1,
                title="Leerkracht",
                value="Andere Leerkracht",
            ),
            smartschool.StudentNoteParam(
                param_id=2,
                param_type=6,
                title="Bijlagen",
                value="files",
                option_value='[{"name": "voorbeeld.pdf"}]',
            ),
        ],
    )


def _absence(day: date, part: str = "VM") -> Any:
    return smartschool.StudentAbsence(
        absent_id=1,
        code="Z",
        description="Ziek",
        date=_epoch(day),
        info="",
        color="",
        part_of_day=part,
        school_year="2026-2027",
    )


def _notes(notes: list[Any]) -> Any:
    return patch("smartschool_mcp.server.StudentNotes", return_value=notes)


def _details(**kwargs: Any) -> Any:
    return patch("smartschool_mcp.server.StudentNoteDetails", autospec=True, **kwargs)


# ── errors ────────────────────────────────────────────────────────────────────


def test_get_student_notes_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.StudentNotes", side_effect=RuntimeError("x")):
        result = srv.get_student_notes()
    assert "error" in result


def test_get_student_notes_invalid_since_returns_error() -> None:
    with patch("smartschool_mcp.server.StudentNotes", return_value=[]):
        assert "error" in srv.get_student_notes(since="13/10/2026")


def test_get_student_absences_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.StudentAbsences", side_effect=RuntimeError("x")):
        assert "error" in srv.get_student_absences()


def test_get_student_absences_invalid_since_returns_error() -> None:
    with patch("smartschool_mcp.server.StudentAbsences", return_value=[]):
        assert "error" in srv.get_student_absences(since="gisteren")


# ── notes ─────────────────────────────────────────────────────────────────────


def test_get_student_notes_empty() -> None:
    with patch("smartschool_mcp.server.StudentNotes", return_value=[]):
        result = srv.get_student_notes()
    assert result["notes"] == []
    assert result["pagination"]["total"] == 0
    assert result["pagination"]["has_more"] is False


@needs_lib
def test_get_student_notes_sorted_newest_first_and_formats_fields() -> None:
    with _notes([_note(1, date(2026, 9, 2)), _note(2, date(2026, 10, 1))]):
        result = srv.get_student_notes()
    assert [n["id"] for n in result["notes"]] == [2, 1]
    first = result["notes"][0]
    assert first["date"] == "2026-10-01"
    assert first["category"] == "Mededeling"
    assert first["author"] == "Voorbeeld Leerkracht"
    assert "details" not in first


@needs_lib
def test_get_student_notes_without_details_never_fetches_details() -> None:
    with _notes([_note(1, date(2026, 9, 2))]), _details() as details_cls:
        srv.get_student_notes()
    details_cls.assert_not_called()


@needs_lib
def test_get_student_notes_hides_private_and_never_fetches_their_details() -> None:
    notes = [_note(1, date(2026, 9, 2)), _note(2, date(2026, 9, 3), private=True)]
    with _notes(notes), _details() as details_cls:
        details_cls.return_value.get.return_value = _detail(1)
        result = srv.get_student_notes(include_details=True)
    assert [n["id"] for n in result["notes"]] == [1]
    assert result["filters"]["private_hidden"] == 1
    assert [c.kwargs["item_id"] for c in details_cls.call_args_list] == [1]


@needs_lib
def test_get_student_notes_category_filter_is_case_insensitive() -> None:
    notes = [
        _note(1, date(2026, 9, 2), cat="Ordemaatregel"),
        _note(2, date(2026, 9, 3), cat="Mededeling"),
    ]
    with _notes(notes):
        result = srv.get_student_notes(category="ORDEMAAT")
    assert [n["id"] for n in result["notes"]] == [1]


@needs_lib
def test_get_student_notes_since_filter_and_forwarded_to_library() -> None:
    notes = [_note(1, date(2026, 9, 1)), _note(2, date(2026, 10, 1))]
    with patch("smartschool_mcp.server.StudentNotes", return_value=notes) as cls:
        result = srv.get_student_notes(since="2026-09-15")
    assert [n["id"] for n in result["notes"]] == [2]
    assert cls.call_args.kwargs["since"] == date(2026, 9, 15)


@needs_lib
def test_get_student_notes_pagination() -> None:
    notes = [_note(i, date(2026, 9, i)) for i in range(1, 8)]
    with _notes(notes):
        result = srv.get_student_notes(limit=3, offset=2)
    assert result["pagination"] == {
        "limit": 3,
        "offset": 2,
        "total": 7,
        "returned": 3,
        "has_more": True,
    }
    assert [n["id"] for n in result["notes"]] == [5, 4, 3]


@needs_lib
def test_get_student_notes_clamps_negative_limit_and_offset() -> None:
    with _notes([_note(1, date(2026, 9, 2))]):
        result = srv.get_student_notes(limit=-5, offset=-3)
    assert result["pagination"]["limit"] == 0
    assert result["pagination"]["offset"] == 0
    assert result["notes"] == []
    assert result["pagination"]["has_more"] is False


@needs_lib
def test_get_student_notes_caps_limit_with_details() -> None:
    notes = [_note(i, date(2026, 1, 1)) for i in range(1, 61)]
    with _notes(notes), _details() as details_cls:
        details_cls.return_value.get.return_value = _detail(1)
        result = srv.get_student_notes(limit=500, include_details=True)
    assert result["pagination"]["limit"] == 50
    assert result["pagination"]["returned"] == 50
    assert result["pagination"]["has_more"] is True
    assert result["filters"]["max_limit_with_details"] == 50
    assert details_cls.call_count == 50


@needs_lib
def test_get_student_notes_include_details_uses_library_details_class() -> None:
    """Regression: details must come from StudentNoteDetails, not a method on
    StudentNote (which does not exist and was silently swallowed)."""
    note = _note(7, date(2026, 9, 2))
    assert not hasattr(note, "details")
    with _notes([note]), _details() as details_cls:
        details_cls.return_value.get.return_value = _detail(7)
        result = srv.get_student_notes(include_details=True)
    assert details_cls.call_args.kwargs["item_id"] == 7
    details = result["notes"][0]["details"]
    assert details["text"] == "Synthetische tekst"
    assert "<" not in details["text"]
    assert details["attachments"] == [{"name": "voorbeeld.pdf"}]
    assert details["measure"] is None
    assert details["fields"] == {"Leerkracht": "Andere Leerkracht"}
    assert "details_error" not in result["notes"][0]
    assert result["filters"]["details_failed"] == 0


@needs_lib
def test_get_student_notes_details_failure_is_reported_not_swallowed() -> None:
    notes = [_note(1, date(2026, 9, 2)), _note(2, date(2026, 9, 3))]
    with _notes(notes), _details() as details_cls:
        details_cls.return_value.get.side_effect = RuntimeError("boom")
        result = srv.get_student_notes(include_details=True)
    for n in result["notes"]:
        assert n["details"] is None
        assert n["details_error"] == "RuntimeError: boom"
    assert result["filters"]["details_failed"] == 2


# ── absences ──────────────────────────────────────────────────────────────────


@needs_lib
def test_get_student_absences_sorted_and_filtered() -> None:
    absences = [
        _absence(date(2026, 9, 1)),
        _absence(date(2026, 10, 1), "NM"),
        _absence(date(2026, 9, 20)),
    ]
    with patch("smartschool_mcp.server.StudentAbsences", return_value=absences) as cls:
        result = srv.get_student_absences(since="2026-09-10")
    assert [a["date"] for a in result["absences"]] == ["2026-10-01", "2026-09-20"]
    assert result["absences"][0]["part_of_day"] == "NM"
    assert result["absences"][0]["description"] == "Ziek"
    assert result["total"] == 2
    assert result["filters"] == {"since": "2026-09-10"}
    assert cls.call_args.kwargs["since"] == date(2026, 9, 10)


def test_get_student_absences_empty() -> None:
    with patch("smartschool_mcp.server.StudentAbsences", return_value=[]):
        result = srv.get_student_absences()
    assert result == {"absences": [], "total": 0, "filters": {"since": None}}
