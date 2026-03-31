"""Tests for server session selection and caching helpers."""

from __future__ import annotations

import importlib
from builtins import __import__ as builtin_import
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from smartschool import AppCredentials


def _reload_server_module():
    import smartschool_mcp.server as srv

    return importlib.reload(srv)


def test_env_session_uses_lru_cache() -> None:
    srv = _reload_server_module()
    srv._env_session.cache_clear()

    with (
        patch("smartschool_mcp.server.EnvCredentials", return_value="env-creds"),
        patch("smartschool_mcp.server.Smartschool", return_value="session") as mock_ss,
    ):
        first = srv._env_session()
        second = srv._env_session()

    assert first == "session"
    assert second == "session"
    mock_ss.assert_called_once_with("env-creds")


def test_cached_app_session_uses_credentials_cache() -> None:
    srv = _reload_server_module()
    srv._session_cache.clear()

    with (
        patch(
            "smartschool_mcp.server.AppCredentials",
            side_effect=lambda **kwargs: kwargs,
        ) as mock_creds,
        patch(
            "smartschool_mcp.server.Smartschool", return_value="app-session"
        ) as mock_ss,
    ):
        first = srv._cached_app_session("user", "pass", "school.smartschool.be", "")
        second = srv._cached_app_session("user", "pass", "school.smartschool.be", "")

    assert first == "app-session"
    assert second == "app-session"
    mock_creds.assert_called_once_with(
        username="user",
        password="pass",
        main_url="school.smartschool.be",
        mfa="",
    )
    mock_ss.assert_called_once()


def test_session_uses_oauth_credentials_when_available() -> None:
    srv = _reload_server_module()
    creds = AppCredentials(
        username="john",
        password="secret",
        main_url="school.smartschool.be",
        mfa="2000-01-01",
    )
    token = SimpleNamespace(cred_key="cred-key")

    with (
        patch(
            "mcp.server.auth.middleware.auth_context.get_access_token",
            return_value=token,
        ),
        patch("smartschool_mcp.auth.get_credentials", return_value=creds),
        patch.object(
            srv, "_cached_app_session", return_value="oauth-session"
        ) as mock_cached,
        patch.object(srv, "_env_session", return_value="env-session") as mock_env,
    ):
        result = srv._session()

    assert result == "oauth-session"
    mock_cached.assert_called_once_with(
        "john",
        "secret",
        "school.smartschool.be",
        "2000-01-01",
    )
    mock_env.assert_not_called()


def test_session_falls_back_to_env_when_cred_key_missing() -> None:
    srv = _reload_server_module()

    with (
        patch(
            "mcp.server.auth.middleware.auth_context.get_access_token",
            return_value=SimpleNamespace(),
        ),
        patch.object(
            srv, "_cached_app_session", return_value="oauth-session"
        ) as mock_cached,
        patch.object(srv, "_env_session", return_value="env-session") as mock_env,
    ):
        result = srv._session()

    assert result == "env-session"
    mock_cached.assert_not_called()
    mock_env.assert_called_once()


def test_session_falls_back_to_env_when_import_error() -> None:
    srv = _reload_server_module()

    def guarded_import(name, *args, **kwargs):
        if name == "mcp.server.auth.middleware.auth_context":
            raise ImportError("missing auth context")
        return builtin_import(name, *args, **kwargs)

    with (
        patch("builtins.__import__", side_effect=guarded_import),
        patch.object(srv, "_env_session", return_value="env-session") as mock_env,
    ):
        result = srv._session()

    assert result == "env-session"
    mock_env.assert_called_once()


def test_session_falls_back_to_env_when_credentials_not_found() -> None:
    srv = _reload_server_module()
    token = SimpleNamespace(cred_key="missing-key")

    with (
        pytest.raises(srv.AuthenticationError, match="re-authentication required"),
        patch(
            "mcp.server.auth.middleware.auth_context.get_access_token",
            return_value=token,
        ),
        patch("smartschool_mcp.auth.get_credentials", return_value=None),
        patch.object(
            srv, "_cached_app_session", return_value="oauth-session"
        ) as mock_cached,
        patch.object(srv, "_env_session", return_value="env-session") as mock_env,
    ):
        srv._session()

    mock_cached.assert_not_called()
    mock_env.assert_not_called()
