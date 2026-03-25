"""Tests for MCP tool registration and error-handling behaviour."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import smartschool_mcp.server as srv

# ── Tool registration ─────────────────────────────────────────────────────────

EXPECTED_TOOLS = [
    "get_courses",
    "get_results",
    "get_future_tasks",
    "get_messages",
    "get_schedule",
    "get_periods",
    "get_reports",
    "get_planned_elements",
    "get_student_support_links",
]


def test_all_tools_are_defined() -> None:
    for name in EXPECTED_TOOLS:
        assert hasattr(srv, name), f"Tool {name!r} not found in server module"
        assert callable(getattr(srv, name))


def test_mcp_server_name() -> None:
    assert srv.mcp.name == "Smartschool MCP"


# ── Error-handling: every tool must catch exceptions ─────────────────────────


def test_get_courses_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.Courses", side_effect=RuntimeError("network")):
        result = srv.get_courses()
    assert isinstance(result, list)
    assert "error" in result[0]
    assert "network" in result[0]["error"]


def test_get_results_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.Results", side_effect=RuntimeError("auth")):
        result = srv.get_results()
    assert isinstance(result, dict)
    assert "error" in result
    assert "auth" in result["error"]


def test_get_future_tasks_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.FutureTasks", side_effect=RuntimeError("timeout")):
        result = srv.get_future_tasks()
    assert isinstance(result, dict)
    assert "error" in result


def test_get_messages_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.MessageHeaders", side_effect=RuntimeError("403")):
        result = srv.get_messages()
    assert isinstance(result, dict)
    assert "error" in result


def test_get_schedule_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.SmartschoolLessons", side_effect=RuntimeError("503")):
        result = srv.get_schedule()
    assert isinstance(result, dict)
    assert "error" in result


def test_get_periods_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.Periods", side_effect=RuntimeError("oops")):
        result = srv.get_periods()
    assert isinstance(result, list)
    assert "error" in result[0]


def test_get_reports_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.Reports", side_effect=RuntimeError("oops")):
        result = srv.get_reports()
    assert isinstance(result, list)
    assert "error" in result[0]


def test_get_planned_elements_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.PlannedElements", side_effect=RuntimeError("oops")):
        result = srv.get_planned_elements()
    assert isinstance(result, dict)
    assert "error" in result


def test_get_student_support_links_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.StudentSupportLinks", side_effect=RuntimeError("oops")):
        result = srv.get_student_support_links()
    assert isinstance(result, list)
    assert "error" in result[0]


# ── Happy-path: verify tool processes library objects correctly ───────────────


def test_get_courses_returns_list() -> None:
    mock_course = MagicMock()
    mock_course.name = "Wiskunde"
    mock_course.teachers = []

    with patch("smartschool_mcp.server.Courses", return_value=[mock_course]):
        result = srv.get_courses()

    assert result == [{"name": "Wiskunde", "teachers": []}]


def test_get_future_tasks_counts_tasks_correctly() -> None:
    """total_tasks must count tasks, not dict keys."""
    mock_task = MagicMock()
    mock_task.label = "Read chapter 3"
    mock_task.description = "Pages 40–60"
    mock_task.warning = False

    mock_items = MagicMock()
    mock_items.tasks = [mock_task, mock_task]  # 2 tasks

    mock_course = MagicMock()
    mock_course.course_title = "Biology"
    mock_course.items = mock_items

    mock_day = MagicMock()
    mock_day.date = None
    mock_day.courses = [mock_course]

    with patch("smartschool_mcp.server.FutureTasks", return_value=[mock_day]):
        result = srv.get_future_tasks()

    assert result["total_tasks"] == 2  # was broken before (returned 4 = len(task_dict))


def test_get_messages_invalid_box_type_defaults_to_inbox() -> None:
    with patch("smartschool_mcp.server.MessageHeaders", return_value=[]) as mock_mh:
        srv.get_messages(box_type="INVALID_BOX")
    # Should not raise; BoxType.INBOX used as fallback
    mock_mh.assert_called_once()


def test_get_results_pagination() -> None:
    mock_result = MagicMock()
    mock_result.courses = [MagicMock(name="Math")]
    mock_result.name = "Test 1"
    mock_result.graphic = MagicMock(description="8/10", value=8, achieved_points=8.0, total_points=10.0, percentage=0.8)
    mock_result.date = None
    mock_result.availability_date = None
    mock_result.does_count = True
    mock_result.feedback = []
    mock_result.gradebook_owner = MagicMock()
    mock_result.gradebook_owner.name.starting_with_first_name = "John Doe"
    mock_result.period = MagicMock(name="Period 1")

    all_results = [mock_result] * 20

    with patch("smartschool_mcp.server.Results", return_value=all_results):
        result = srv.get_results(limit=5, offset=10, include_details=False)

    assert result["pagination"]["total"] == 20
    assert result["pagination"]["returned"] == 5
    assert result["pagination"]["offset"] == 10
    assert result["pagination"]["has_more"] is True


def test_get_messages_includes_attachment_fields() -> None:
    mock_header = MagicMock()
    mock_header.id = 1
    mock_header.from_ = "teacher@school.be"
    mock_header.subject = "Homework"
    mock_header.date = None
    mock_header.unread = False
    mock_header.priority = None
    # Simulate the library using 'attachments' as the field name
    mock_header.attachments = 2
    # Ensure getattr fallback for 'attachment' doesn't interfere
    del mock_header.attachment

    with patch("smartschool_mcp.server.MessageHeaders", return_value=[mock_header]):
        result = srv.get_messages(include_body=False)

    msg = result["messages"][0]
    assert msg["has_attachments"] is True
    assert msg["attachment_count"] == 2


def test_get_attachments_happy_path() -> None:
    mock_att = MagicMock()
    mock_att.fileID = 42
    mock_att.name = "homework.pdf"
    mock_att.mime = "application/pdf"
    mock_att.size = "100 KB"

    with patch("smartschool_mcp.server.Attachments", return_value=[mock_att]):
        result = srv.get_attachments(message_id=999)

    assert result["message_id"] == 999
    assert result["total"] == 1
    assert result["attachments"][0] == {
        "file_id": 42,
        "name": "homework.pdf",
        "mime_type": "application/pdf",
        "size": "100 KB",
    }


def test_get_attachments_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.Attachments", side_effect=RuntimeError("network")):
        result = srv.get_attachments(message_id=999)
    assert "error" in result
    assert "network" in result["error"]


def test_download_attachment_not_found() -> None:
    with patch("smartschool_mcp.server.Attachments", return_value=[]):
        result = srv.download_attachment(message_id=999, file_id=42)
    assert "error" in result
    assert "not found" in result["error"]


def test_download_attachment_writes_file(tmp_path) -> None:
    mock_att = MagicMock()
    mock_att.fileID = 42
    mock_att.name = "report.pdf"
    mock_att.mime = "application/pdf"
    mock_att.size = "50 KB"

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.content = b"PDF content"

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with (
        patch("smartschool_mcp.server.Attachments", return_value=[mock_att]),
        patch("smartschool_mcp.server._session", return_value=mock_session),
    ):
        result = srv.download_attachment(
            message_id=999,
            file_id=42,
            save_path=str(tmp_path),
        )

    assert result["name"] == "report.pdf"
    assert result["bytes_written"] == len(b"PDF content")
    assert (tmp_path / "report.pdf").read_bytes() == b"PDF content"


def test_download_attachment_returns_error_on_exception() -> None:
    with patch("smartschool_mcp.server.Attachments", side_effect=RuntimeError("boom")):
        result = srv.download_attachment(message_id=999, file_id=42)
    assert "error" in result
