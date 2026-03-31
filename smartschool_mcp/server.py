"""
Smartschool MCP Server
Provides tools to interact with Smartschool API for courses, results, tasks,
messages and more.
"""

from __future__ import annotations

import os
import threading
from datetime import date, timedelta
from functools import lru_cache
from typing import Any, TypedDict

from cachetools import TTLCache, cached
from mcp.server.fastmcp import FastMCP
from smartschool import (
    AppCredentials,
    Attachments,
    BoxType,
    Courses,
    EnvCredentials,
    FutureTasks,
    Message,
    MessageHeaders,
    Periods,
    PlannedElements,
    Reports,
    Results,
    Smartschool,
    SmartschoolLessons,
    StudentSupportLinks,
)

# MCP server - tools are registered via @mcp.tool() decorators below
mcp = FastMCP("Smartschool MCP")


class AuthenticationError(RuntimeError):
    """Authentication state is present but credentials are no longer valid."""


@lru_cache(maxsize=1)
def _env_session() -> Smartschool:
    """Cached session using environment-variable credentials (single-user mode).

    Lazy-initialized on first tool invocation so that import-time errors
    (missing env vars, network failures) surface as tool errors rather than
    crashing the process on startup.
    """
    return Smartschool(EnvCredentials())


# How long (seconds) a cached Smartschool session is reused before the next
# request for those credentials creates a fresh one.  Cookie-based sessions
# expire server-side; keeping this below the server's idle-session timeout
# prevents stale-cookie failures.  Override with SESSION_TTL_SECONDS env var.
_SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "3600"))
_session_cache: TTLCache[tuple[str, str, str, str], Smartschool] = TTLCache(
    maxsize=256, ttl=_SESSION_TTL_SECONDS
)
_session_cache_lock = threading.Lock()


@cached(cache=_session_cache, lock=_session_cache_lock)
def _cached_app_session(
    username: str, password: str, main_url: str, mfa: str
) -> Smartschool:
    """TTL-cached session per unique credential tuple (universal mode).

    Entries expire after SESSION_TTL_SECONDS (default 3600) so stale cookies
    from server-side session expiry are automatically replaced.  Bounded to
    256 entries to cap memory use.
    """
    from smartschool_mcp.auth import _validate_school_url

    validated_host = _validate_school_url(main_url)
    if not validated_host:
        raise ValueError("Untrusted or invalid Smartschool host")

    return Smartschool(
        AppCredentials(
            username=username,
            password=password,
            main_url=validated_host,
            mfa=mfa,
        )
    )


def _session() -> Smartschool:
    """Return the active Smartschool session.

    In universal mode (OAuth), the access token carries a ``cred_key`` that
    maps to stored Smartschool credentials.  Sessions are cached per unique
    credential tuple so repeated calls reuse the same authenticated session.
    Falls back to the environment-variable session in single-user / stdio mode.
    """
    # Check OAuth context (universal mode via OAuth 2.1)
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token

        from smartschool_mcp.auth import get_credentials

        access_token = get_access_token()
        if access_token is not None and hasattr(access_token, "cred_key"):
            creds = get_credentials(access_token.cred_key)  # type: ignore[attr-defined]
            if creds is None:
                raise AuthenticationError(
                    "OAuth credentials expired; re-authentication required"
                )
            return _cached_app_session(
                creds.username, creds.password, creds.main_url, creds.mfa
            )
    except ImportError:
        pass

    return _env_session()


def _safe_get_teacher_names(
    teachers: list | None,
    use_last_name: bool = True,
) -> list[str]:
    """Safely extract teacher names from teacher objects."""
    if not teachers:
        return []

    try:
        if use_last_name:
            return [teacher.name.starting_with_last_name for teacher in teachers]
        else:
            return [teacher.name.starting_with_first_name for teacher in teachers]
    except (AttributeError, IndexError):
        return []


def _safe_format_date(date_obj: Any) -> str | None:
    """Safely format date objects to string."""
    try:
        return date_obj.strftime("%Y-%m-%d") if date_obj else None
    except (AttributeError, ValueError):
        return None


@mcp.tool()
def get_courses() -> list[dict[str, Any]]:
    """
    Retrieve all available courses with their teachers.

    Returns:
        List of courses with name and teacher information.
    """
    try:
        courses_list = []

        for course in Courses(_session()):
            teacher_names = _safe_get_teacher_names(course.teachers, use_last_name=True)
            courses_list.append(
                {
                    "name": course.name,
                    "teachers": teacher_names,
                }
            )

        return courses_list

    except Exception as e:
        return [{"error": f"Failed to retrieve courses: {e!s}"}]


@mcp.tool()
def get_results(
    limit: int = 15,
    offset: int = 0,
    course_filter: str | None = None,
    include_details: bool = True,
) -> dict[str, Any]:
    """
    Retrieve student results/grades with detailed information.

    Args:
        limit: Maximum number of results to return (default: 15)
        offset: Number of results to skip from the beginning (default: 0)
        course_filter: Filter results by course name (partial match, case-insensitive)
        include_details: Whether to fetch detailed info (teacher, average, median)
            - saves API calls if False

    Returns:
        Dictionary with results list and pagination info.

    Examples:
        - get_results() -> First 15 results with details
        - get_results(course_filter="Math") -> Results from courses containing "Math"
        - get_results(include_details=False) -> Basic info only, faster response
    """
    try:
        results = Results(_session())
        all_results = list(results)

        # Apply course filtering
        if course_filter:
            filtered = []
            for result in all_results:
                course_name = result.courses[0].name if result.courses else ""
                if course_filter.lower() in course_name.lower():
                    filtered.append(result)
            all_results = filtered

        # Apply pagination
        end_index = offset + limit
        paginated = all_results[offset:end_index]

        results_list = []

        for result in paginated:
            # Basic result information (teacher comes from gradebook_owner,
            # no extra API call)
            graphic = result.graphic
            result_data = {
                "course": result.courses[0].name if result.courses else "Unknown",
                "assignment": result.name or "Unknown Assignment",
                "teacher": result.gradebook_owner.name.starting_with_first_name,
                "period": result.period.name if result.period else None,
                "score_description": getattr(graphic, "description", "N/A"),
                "score_value": getattr(graphic, "value", None),
                "achieved_points": getattr(graphic, "achieved_points", None),
                "total_points": getattr(graphic, "total_points", None),
                "percentage": getattr(graphic, "percentage", None),
                "date": _safe_format_date(result.date),
                "published_date": _safe_format_date(result.availability_date),
                "counts": result.does_count,
                "feedback": result.feedback[0].text if result.feedback else "",
            }

            # Fetch central tendencies (average/median) only when requested
            if include_details:
                result_data.update({"average": None, "median": None})

                try:
                    # details is a lazy-loaded property — fetches on first access
                    detail = result.details

                    # Extract statistical information (central tendencies)
                    if detail and detail.central_tendencies:
                        tendencies = detail.central_tendencies

                        if len(tendencies) > 0 and hasattr(tendencies[0], "graphic"):
                            g = tendencies[0].graphic
                            result_data["average"] = {
                                "description": getattr(g, "description", "N/A"),
                                "value": getattr(g, "value", None),
                            }

                        if len(tendencies) > 1 and hasattr(tendencies[1], "graphic"):
                            g = tendencies[1].graphic
                            result_data["median"] = {
                                "description": getattr(g, "description", "N/A"),
                                "value": getattr(g, "value", None),
                            }

                except Exception:
                    # central_tendencies unavailable — keep default None values
                    pass

            results_list.append(result_data)

        total_results = len(all_results)
        return {
            "results": results_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_results,
                "returned": len(results_list),
                "has_more": end_index < total_results,
            },
            "filters": {
                "course_filter": course_filter,
                "include_details": include_details,
            },
        }

    except Exception as e:
        return {"error": f"Failed to retrieve results: {e!s}"}


class _TaskDict(TypedDict):
    label: str
    description: str
    warning: bool


class _CourseDict(TypedDict):
    name: str
    tasks: list[_TaskDict]


class _DayDict(TypedDict):
    date: str | None
    courses: list[_CourseDict]


@mcp.tool()
def get_future_tasks() -> dict[str, Any]:
    """
    Retrieve upcoming assignments and tasks.

    Returns:
        Dictionary with future tasks organized by date and course.
    """
    try:
        future_tasks = FutureTasks(_session())
        tasks_data: list[_DayDict] = []

        for day in future_tasks:
            day_data: _DayDict = {
                "date": _safe_format_date(day.date),
                "courses": [],
            }

            for course in day.courses:
                course_data: _CourseDict = {
                    "name": course.course_title,
                    "tasks": [],
                }

                # Extract tasks from the course
                if hasattr(course, "items") and hasattr(course.items, "tasks"):
                    for task in course.items.tasks:
                        task_data: _TaskDict = {
                            "label": getattr(task, "label", "N/A"),
                            "description": getattr(task, "description", "N/A"),
                            "warning": getattr(task, "warning", False),
                        }
                        course_data["tasks"].append(task_data)

                # Only add course if it has tasks
                if course_data["tasks"]:
                    day_data["courses"].append(course_data)

            # Only add day if it has courses with tasks
            if day_data["courses"]:
                tasks_data.append(day_data)

        total_tasks = sum(
            len(course["tasks"]) for day in tasks_data for course in day["courses"]
        )

        return {
            "future_tasks": tasks_data,
            "total_days": len(tasks_data),
            "total_tasks": total_tasks,
        }

    except Exception as e:
        return {"error": f"Failed to retrieve future tasks: {e!s}"}


@mcp.tool()
def get_messages(
    limit: int = 15,
    offset: int = 0,
    box_type: str = "INBOX",
    search_query: str | None = None,
    sender_filter: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """
    Retrieve messages from the specified mailbox with filtering options.

    Args:
        limit: Maximum number of messages to return (default: 15)
        offset: Number of messages to skip from the beginning (default: 0)
        box_type: Type of mailbox - "INBOX", "SENT", "DRAFT", "SCHEDULED",
            "TRASH" (default: "INBOX")
        search_query: Search in subject and body content (case-insensitive)
        sender_filter: Filter messages by sender name (partial match,
            case-insensitive)
        include_body: Whether to include full message body
            (default: False for performance)

    Returns:
        Dictionary with messages list and pagination info.

    Examples:
        - get_messages() -> First 15 inbox messages (headers only)
        - get_messages(search_query="homework") -> Messages containing "homework"
        - get_messages(sender_filter="teacher") -> Messages from senders containing
          "teacher"
        - get_messages(include_body=True) -> Full messages with body content
    """
    try:
        # Convert string box_type to BoxType enum
        try:
            box_type_enum = getattr(BoxType, box_type.upper())
        except AttributeError:
            box_type_enum = BoxType.INBOX  # Default fallback

        # Get message headers — headers already carry from_, subject, date, unread
        all_headers = list(MessageHeaders(_session(), box_type=box_type_enum))

        # Apply sender filter directly from headers (no full message fetch needed)
        if sender_filter:
            all_headers = [
                h
                for h in all_headers
                if sender_filter.lower() in (getattr(h, "from_", "") or "").lower()
            ]

        # Apply search query: check subject first, only fetch body when subject
        # doesn't match
        if search_query:
            matched = []
            for header in all_headers:
                subject = (getattr(header, "subject", "") or "").lower()
                if search_query.lower() in subject:
                    matched.append(header)
                    continue
                # Fall back to fetching full message body
                try:
                    full_msg = Message(_session(), header.id).get()
                    body = (getattr(full_msg, "body", "") or "").lower()
                    if search_query.lower() in body:
                        header._cached_message = full_msg
                        matched.append(header)
                except Exception:
                    continue
            all_headers = matched

        # Apply pagination
        end_index = offset + limit
        paginated = all_headers[offset:end_index]

        messages_list = []

        for header in paginated:
            attachment_count = (
                getattr(header, "attachments", None)
                or getattr(header, "attachment", 0)
                or 0
            )
            message_data = {
                "id": getattr(header, "id", None),
                "from": getattr(header, "from_", "Unknown Sender"),
                "subject": getattr(header, "subject", "No Subject"),
                "date": _safe_format_date(getattr(header, "date", None)),
                "unread": getattr(header, "unread", None),
                "priority": getattr(header, "priority", None),
                "has_attachments": attachment_count > 0,
                "attachment_count": attachment_count,
            }

            # Include body if explicitly requested or already cached from search
            cached = getattr(header, "_cached_message", None)
            if include_body:
                try:
                    full_msg = cached or Message(_session(), header.id).get()
                    message_data["body"] = getattr(full_msg, "body", "")
                except Exception:
                    message_data["body"] = ""
            else:
                if cached:
                    body = getattr(cached, "body", "") or ""
                    message_data["body_preview"] = (
                        body[:100] + "..." if len(body) > 100 else body
                    )
                else:
                    message_data["body_preview"] = None

            messages_list.append(message_data)

        total_messages = len(all_headers)
        return {
            "messages": messages_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_messages,
                "returned": len(messages_list),
                "has_more": end_index < total_messages,
            },
            "filters": {
                "box_type": box_type,
                "search_query": search_query,
                "sender_filter": sender_filter,
                "include_body": include_body,
            },
        }

    except Exception as e:
        return {"error": f"Failed to retrieve messages: {e!s}"}


@mcp.tool()
def get_schedule(date_offset: int = 0) -> dict[str, Any]:
    """
    Retrieve the lesson schedule for a given day.

    Args:
        date_offset: Days from today (0=today, 1=tomorrow, -1=yesterday,
            default: 0)

    Returns:
        Dictionary with the lessons scheduled for the given date.
    """
    try:
        target_date = date.today() + timedelta(days=date_offset)
        lessons_list = []

        for lesson in SmartschoolLessons(_session(), timestamp_to_use=target_date):
            lessons_list.append(
                {
                    "moment_id": lesson.moment_id,
                    "date": _safe_format_date(lesson.date),
                    "hour": lesson.hour,
                    "course": lesson.course_title,
                    "classroom": lesson.classroom_title,
                    "teacher": lesson.teacher_title,
                    "subject": lesson.subject,
                    "note": lesson.note,
                    "color": lesson.color,
                    "assignment_end_status": lesson.assignment_end_status,
                    "test_deadline_status": lesson.test_deadline_status,
                }
            )

        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "lessons": lessons_list,
            "total": len(lessons_list),
        }

    except Exception as e:
        return {"error": f"Failed to retrieve schedule: {e!s}"}


@mcp.tool()
def get_periods() -> list[dict[str, Any]]:
    """
    Retrieve academic periods/terms for the current school year.

    Returns:
        List of academic periods with name, dates, and active status.
    """
    try:
        periods_list = []

        for period in Periods(_session()):
            periods_list.append(
                {
                    "name": period.name,
                    "is_active": period.is_active,
                    "class": period.class_.name if period.class_ else None,
                    "school_year_start": _safe_format_date(
                        period.skore_work_year.date_range.start
                    ),
                    "school_year_end": _safe_format_date(
                        period.skore_work_year.date_range.end
                    ),
                }
            )

        return periods_list

    except Exception as e:
        return [{"error": f"Failed to retrieve periods: {e!s}"}]


@mcp.tool()
def get_reports() -> list[dict[str, Any]]:
    """
    Retrieve available academic report cards.

    Returns:
        List of report cards with name, date, class, and school year label.
    """
    try:
        reports_list = []

        for report in Reports(_session()):
            reports_list.append(
                {
                    "name": report.name,
                    "date": _safe_format_date(report.date),
                    "class": report.class_.name if report.class_ else None,
                    "schoolyear_label": report.schoolyear_label,
                }
            )

        return reports_list

    except Exception as e:
        return [{"error": f"Failed to retrieve reports: {e!s}"}]


@mcp.tool()
def get_planned_elements(days_ahead: int = 34) -> dict[str, Any]:
    """
    Retrieve planned assignments and to-dos from the Smartschool planner.

    Args:
        days_ahead: Number of days ahead to fetch (default: 34)

    Returns:
        Dictionary with planned elements including dates, courses, and assignment types.
    """
    try:
        from_date = date.today()
        till_date = from_date + timedelta(days=days_ahead)
        elements_list = []

        for element in PlannedElements(_session(), till_date=till_date):
            period = getattr(element, "period", None)
            element_data = {
                "name": element.name,
                "type": element.planned_element_type,
                "from": (
                    period.date_time_from.strftime("%Y-%m-%d %H:%M") if period else None
                ),
                "to": (
                    period.date_time_to.strftime("%Y-%m-%d %H:%M") if period else None
                ),
                "color": element.color,
                "courses": [c.name for c in element.courses] if element.courses else [],
                "unconfirmed": element.unconfirmed,
                "pinned": element.pinned,
                "assignment_type": (
                    element.assignment_type.name if element.assignment_type else None
                ),
            }
            elements_list.append(element_data)

        return {
            "planned_elements": elements_list,
            "total": len(elements_list),
            "period": {
                "from": from_date.strftime("%Y-%m-%d"),
                "to": till_date.strftime("%Y-%m-%d"),
            },
        }

    except Exception as e:
        return {"error": f"Failed to retrieve planned elements: {e!s}"}


@mcp.tool()
def get_student_support_links() -> list[dict[str, Any]]:
    """
    Retrieve student support links and resources.

    Returns:
        List of visible support links with name, description, and URL.
    """
    try:
        links_list = []

        for link in StudentSupportLinks(_session()):
            if link.is_visible:
                links_list.append(
                    {
                        "name": link.name,
                        "description": link.description,
                        "link": link.clean_link,
                    }
                )

        return links_list

    except Exception as e:
        return [{"error": f"Failed to retrieve support links: {e!s}"}]


@mcp.tool()
def get_attachments(message_id: int) -> dict[str, Any]:
    """
    List all attachments for a specific message.

    Args:
        message_id: The ID of the message to get attachments for
            (from get_messages results).

    Returns:
        Dictionary with attachment list including file names, sizes, and IDs
        for downloading.

    Examples:
        - get_attachments(249184) -> List attachments for message 249184
    """
    try:
        attachments_list = [
            {
                "file_id": getattr(att, "fileID", None),
                "name": getattr(att, "name", "Unknown"),
                "mime_type": getattr(att, "mime", "Unknown"),
                "size": getattr(att, "size", "Unknown"),
            }
            for att in Attachments(_session(), msg_id=message_id)
        ]
        return {
            "message_id": message_id,
            "attachments": attachments_list,
            "total": len(attachments_list),
        }
    except Exception as e:
        return {"error": f"Failed to retrieve attachments: {e!s}"}


@mcp.tool()
def download_attachment(
    message_id: int,
    file_id: int,
    save_path: str | None = None,
) -> dict[str, Any]:
    """
    Download a specific attachment from a message.

    Files are saved to *save_path* when provided, otherwise to
    ~/Downloads/smartschool/.  The directory is created automatically.
    Existing files are never overwritten — a counter suffix is appended
    instead (e.g. ``report (1).pdf``).

    Args:
        message_id: The ID of the message containing the attachment.
        file_id: The file ID of the attachment to download (from get_attachments).
        save_path: Optional directory to save the file into.

    Returns:
        Dictionary with the saved file path, filename, mime type, and bytes written.

    Examples:
        - download_attachment(249184, 12345) -> Download to ~/Downloads/smartschool/
        - download_attachment(249184, 12345, "/tmp") -> Download to /tmp/
    """
    from pathlib import Path

    try:
        target_attachment = None
        for att in Attachments(_session(), msg_id=message_id):
            if getattr(att, "fileID", None) == file_id:
                target_attachment = att
                break

        if target_attachment is None:
            return {"error": f"Attachment {file_id} not found in message {message_id}"}

        # The upstream library's Attachment.download() incorrectly base64-decodes the
        # response; Smartschool actually returns raw binary.  Call the session directly.
        resp = _session().get(
            f"/?module=Messages&file=download&fileID={file_id}&target=0"
        )
        if not resp.ok:
            return {"error": f"Download failed: HTTP {resp.status_code}"}

        download_dir = (
            Path(save_path) if save_path else Path.home() / "Downloads" / "smartschool"
        )
        download_dir.mkdir(parents=True, exist_ok=True)

        # Sanitise filename to prevent path-traversal attacks
        raw_name = getattr(target_attachment, "name", "") or ""
        filename = Path(raw_name).name or f"attachment_{file_id}"
        file_path = download_dir / filename

        # Never overwrite — append a counter suffix
        counter = 1
        stem = file_path.stem
        while file_path.exists():
            file_path = download_dir / f"{stem} ({counter}){file_path.suffix}"
            counter += 1

        file_path.write_bytes(resp.content)

        return {
            "file_id": file_id,
            "name": filename,
            "mime_type": getattr(target_attachment, "mime", "Unknown"),
            "size": getattr(target_attachment, "size", "Unknown"),
            "saved_to": str(file_path),
            "bytes_written": len(resp.content),
        }

    except Exception as e:
        return {"error": f"Failed to download attachment: {e!s}"}
