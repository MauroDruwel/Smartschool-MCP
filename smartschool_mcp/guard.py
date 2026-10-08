"""One-shot Smartschool login guard for the MCP server.

Same rule as the Claude plugin scripts: one credential POST, then
``~/.cache/smartschool/<subdomain>/<user>/auth_failed``. That is the cache
directory of the shared credential store, so the Desktop bundle and the
plugin share one lockout. A response that stays on ``/login`` (including
``/login?error=1``) is a failure. Later calls refuse before another password
is sent.

The file lock is held only around that POST. The plugin scripts hold it until
the process exits; this server keeps running, so a process-lifetime lock would
stall later tool calls.
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlparse

from smartschool import Smartschool, SmartSchoolAuthenticationError

from smartschool_mcp.credentials import CredentialStoreError, profile_cache_dir

_logger = logging.getLogger(__name__)

_SCHOOL_SUFFIX = ".smartschool.be"
_LABEL_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_LOGIN_LOCK = threading.Lock()


def cache_dir(username: str, main_url: str) -> Path:
    """Session cache for one login, shared with the credential store.

    ``*.smartschool.be`` accounts use ``profile_cache_dir``
    (``~/.cache/smartschool/<subdomain>/<user>``). An allowlisted host that
    is not a Smartschool subdomain still gets a directory under that cache
    root so the lockout file can be written.
    """
    try:
        return profile_cache_dir(main_url, username)
    except (SmartSchoolAuthenticationError, CredentialStoreError):
        host = "unknown"
        if main_url.strip():
            try:
                host = credential_hostname(main_url)
            except SmartSchoolAuthenticationError:
                host = "unknown"
        safe_host = host.replace("/", "").replace("\\", "") or "unknown"
        safe_user = username.strip() or "unknown"
        return Path.home() / ".cache" / "smartschool" / safe_host / safe_user


def auth_failed_path(username: str, main_url: str) -> Path:
    return cache_dir(username, main_url) / "auth_failed"


def auth_failed_message(username: str, main_url: str) -> str:
    return (
        "LOGIN FAILED, niet opnieuw proberen. "
        f"Verwijder dit bestand handmatig: {auth_failed_path(username, main_url)}"
    )


def _split_host_port(raw: str) -> tuple[str, str | None]:
    text = raw.strip()
    if not text:
        return "", None
    port: str | None
    if "://" in text:
        parsed = urlparse(text)
        host = (parsed.hostname or "").lower().strip(".")
        port = str(parsed.port) if parsed.port else None
        return host, port
    bare = text.split("/")[0].strip()
    port = None
    if bare.count(":") == 1:
        host_part, port_part = bare.rsplit(":", 1)
        if port_part.isdigit():
            bare = host_part
            port = port_part
    return bare.lower().strip("."), port


def normalize_school_main_url(raw: str) -> str:
    """School host for ``SMARTSCHOOL_MAIN_URL``.

    A bare subdomain such as ``dering`` becomes ``dering.smartschool.be``.
    ``https://`` and a pasted ``.smartschool.be`` suffix are removed first.
    Any other hostname is returned unchanged so an allowlisted host still
    reaches ``_validate_school_url``.
    """
    host, port = _split_host_port(raw)
    if not host:
        if raw.strip():
            raise ValueError("Invalid school subdomain")
        return ""
    if host == "smartschool.be" or host.endswith(_SCHOOL_SUFFIX):
        labels = "" if host == "smartschool.be" else host[: -len(_SCHOOL_SUFFIX)]
        host = _join_school_host(labels.strip("."))
    elif "." not in host:
        host = _join_school_host(host)
    if port:
        return f"{host}:{port}"
    return host


def _join_school_host(labels: str) -> str:
    parts = [part for part in labels.split(".") if part]
    if not parts or any(_LABEL_RE.fullmatch(part) is None for part in parts):
        raise ValueError("Invalid school subdomain")
    return ".".join(parts) + _SCHOOL_SUFFIX


def credential_hostname(main_url: str) -> str:
    """Hostname a password may be posted to. Scheme, when present, is https."""
    raw = main_url.strip()
    if "://" in raw:
        parsed = urlparse(raw)
        if parsed.scheme != "https":
            raise SmartSchoolAuthenticationError("SMARTSCHOOL_MAIN_URL moet https zijn")
        host = parsed.hostname or ""
    else:
        host = raw.split("/")[0].split(":")[0]
    host = host.lower()
    if not host:
        raise SmartSchoolAuthenticationError(
            "SMARTSCHOOL_MAIN_URL moet eindigen op .smartschool.be"
        )
    return host


def _path_segments(url: str) -> set[str]:
    return {part for part in urlparse(url).path.split("/") if part}


def _path_has(url: str, *segments: str) -> bool:
    found = _path_segments(url)
    return any(segment in found for segment in segments)


def _acquire_windows_lock(fd: int):
    import msvcrt

    os.lseek(fd, 0, os.SEEK_SET)
    if os.fstat(fd).st_size < 1:
        os.write(fd, b"\0")
        os.lseek(fd, 0, os.SEEK_SET)
    msvcrt.locking(fd, msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]

    def _release() -> None:
        with contextlib.suppress(OSError):
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
            os.close(fd)

    return _release


def _acquire_posix_lock(fd: int):
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_EX)

    def _release() -> None:
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    return _release


def _acquire_session_lock(fd: int):
    """Exclusive lock on an open fd. Unix uses flock; Windows uses msvcrt."""
    if os.name == "nt":
        return _acquire_windows_lock(fd)
    return _acquire_posix_lock(fd)


@contextlib.contextmanager
def _credential_post_lock(username: str, main_url: str) -> Iterator[None]:
    """Block a second password POST in this process and in other local clients."""
    directory = cache_dir(username, main_url)
    directory.mkdir(parents=True, exist_ok=True)
    fd = os.open(directory / ".session.lock", os.O_CREAT | os.O_RDWR, 0o600)
    release = _acquire_session_lock(fd)
    try:
        with _LOGIN_LOCK:
            yield
    finally:
        release()


class GuardedSession(Smartschool):
    """One failed credential POST, pinned host, shared auth_failed marker.

    A rejected password (``/login`` or ``/login?error=1``) writes the lock
    file and is not posted again. A POST that leaves the login page may
    authenticate again later in this long-running process when the cookie
    expires; that second POST is the accepted password, not a retry loop.
    """

    _password_posts: int = 0
    _login_failed: bool = False

    def request(self, method, url, **kwargs):  # type: ignore[override]
        self._refuse_if_blocked()
        return super().request(method, url, **kwargs)

    def _do_login(self, response):  # type: ignore[override]
        self._assert_credential_target(getattr(response, "url", ""))
        creds = self._require_credentials()
        username = creds.username
        main_url = creds.main_url
        with _credential_post_lock(username, main_url):
            if self._login_failed or auth_failed_path(username, main_url).exists():
                self._block()
            self._password_posts += 1
            _logger.info("Smartschool login attempt")
            try:
                posted = super()._do_login(response)
            except Exception:
                self._login_failed = True
                self._block()
        posted_url = str(getattr(posted, "url", ""))
        # Birthday/2FA are the next step. Staying on /login, including
        # /login?error=1, means the password was rejected.
        if _path_has(posted_url, "login"):
            _logger.warning("Smartschool login failed")
            self._login_failed = True
            self._block()
        _logger.info("Smartschool login form accepted")
        return posted

    def _do_login_verification(self, response):  # type: ignore[override]
        self._assert_credential_target(getattr(response, "url", ""))
        creds = self._require_credentials()
        with _credential_post_lock(creds.username, creds.main_url):
            _logger.info("Smartschool account verification")
            posted = super()._do_login_verification(response)
        posted_url = str(getattr(posted, "url", ""))
        if _path_has(posted_url, "login", "account-verification"):
            _logger.warning("Smartschool login verification failed")
            self._block()
        return posted

    def _refuse_if_blocked(self) -> None:
        creds = self._require_credentials()
        if auth_failed_path(creds.username, creds.main_url).exists():
            raise SmartSchoolAuthenticationError(
                auth_failed_message(creds.username, creds.main_url)
            )

    def _block(self) -> NoReturn:
        creds = self._require_credentials()
        path = auth_failed_path(creds.username, creds.main_url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("login failed\n", encoding="utf-8")
        raise SmartSchoolAuthenticationError(
            auth_failed_message(creds.username, creds.main_url)
        )

    def _assert_credential_target(self, url: str) -> None:
        parsed = urlparse(url)
        expected = credential_hostname(self._require_credentials().main_url)
        actual = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or actual != expected:
            _logger.warning("Smartschool login stopped; credentials were not posted")
            raise SmartSchoolAuthenticationError(
                "Login stopped: credentials were not posted. "
                f"Host {actual!r} is not {expected!r}."
            )
