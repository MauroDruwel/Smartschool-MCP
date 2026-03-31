"""Tests for SmartschoolOAuthProvider and login form routes."""

from __future__ import annotations

import time

import pytest
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl
from smartschool import AppCredentials

from smartschool_mcp.auth import (
    SmartschoolAccessToken,
    SmartschoolOAuthProvider,
    SmartschoolRefreshToken,
    _credential_store,
    _validate_school_url,
    get_credentials,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ISSUER = "http://localhost:8000"


def _make_provider() -> SmartschoolOAuthProvider:
    return SmartschoolOAuthProvider(issuer_url=ISSUER)


def _make_client(client_id: str = "test-client") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_secret="test-secret",
        redirect_uris=[AnyUrl("http://localhost:3000/callback")],
    )


def _make_auth_params(state: str = "test-state") -> AuthorizationParams:
    return AuthorizationParams(
        state=state,
        scopes=["read"],
        code_challenge="test-challenge-abc123",
        redirect_uri=AnyUrl("http://localhost:3000/callback"),
        redirect_uri_provided_explicitly=True,
    )


# ---------------------------------------------------------------------------
# _validate_school_url
# ---------------------------------------------------------------------------


class TestValidateSchoolUrl:
    def test_valid_hostname(self) -> None:
        assert _validate_school_url("school.smartschool.be") == "school.smartschool.be"

    def test_with_scheme(self) -> None:
        assert (
            _validate_school_url("https://school.smartschool.be")
            == "school.smartschool.be"
        )

    def test_with_port(self) -> None:
        result = _validate_school_url("school.smartschool.be:8443")
        assert result == "school.smartschool.be:8443"

    def test_invalid_hostname(self) -> None:
        assert _validate_school_url("not valid!") is None

    def test_empty_string(self) -> None:
        assert _validate_school_url("") is None

    def test_single_label(self) -> None:
        assert _validate_school_url("localhost") is None


# ---------------------------------------------------------------------------
# Client registration
# ---------------------------------------------------------------------------


class TestClientRegistration:
    @pytest.mark.asyncio
    async def test_register_and_get_client(self) -> None:
        provider = _make_provider()
        client = _make_client()

        await provider.register_client(client)
        result = await provider.get_client("test-client")
        assert result is not None
        assert result.client_id == "test-client"

    @pytest.mark.asyncio
    async def test_get_unknown_client_returns_none(self) -> None:
        provider = _make_provider()
        assert await provider.get_client("unknown") is None


# ---------------------------------------------------------------------------
# Authorization flow
# ---------------------------------------------------------------------------


class TestAuthorization:
    @pytest.mark.asyncio
    async def test_authorize_returns_login_url(self) -> None:
        provider = _make_provider()
        client = _make_client()
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        assert url.startswith(f"{ISSUER}/smartschool-login?pending=")

    @pytest.mark.asyncio
    async def test_authorize_stores_pending_auth(self) -> None:
        provider = _make_provider()
        client = _make_client()
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]

        pending = provider.get_pending_auth(pending_id)
        assert pending is not None
        assert pending.client_id == "test-client"
        assert pending.params.state == "test-state"


# ---------------------------------------------------------------------------
# Authorization code exchange
# ---------------------------------------------------------------------------


class TestAuthorizationCodeExchange:
    @pytest.mark.asyncio
    async def test_complete_authorization_creates_code(self) -> None:
        provider = _make_provider()
        client = _make_client()
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]

        auth_code = provider.complete_authorization(
            pending_id=pending_id,
            cred_key="test-cred-key",
        )
        assert auth_code.code
        assert auth_code.client_id == "test-client"
        assert auth_code.cred_key == "test-cred-key"

    @pytest.mark.asyncio
    async def test_load_authorization_code(self) -> None:
        provider = _make_provider()
        client = _make_client()
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]
        auth_code = provider.complete_authorization(
            pending_id=pending_id,
            cred_key="test-cred-key",
        )

        loaded = await provider.load_authorization_code(client, auth_code.code)
        assert loaded is not None
        assert loaded.code == auth_code.code

    @pytest.mark.asyncio
    async def test_load_authorization_code_wrong_client(self) -> None:
        provider = _make_provider()
        client = _make_client()
        other_client = _make_client(client_id="other-client")
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]
        auth_code = provider.complete_authorization(
            pending_id=pending_id,
            cred_key="test-cred-key",
        )

        loaded = await provider.load_authorization_code(other_client, auth_code.code)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_exchange_authorization_code(self) -> None:
        provider = _make_provider()
        client = _make_client()
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]
        auth_code = provider.complete_authorization(
            pending_id=pending_id,
            cred_key="test-cred-key",
        )

        token = await provider.exchange_authorization_code(client, auth_code)
        assert token.access_token
        assert token.refresh_token
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600

    @pytest.mark.asyncio
    async def test_exchange_removes_code(self) -> None:
        provider = _make_provider()
        client = _make_client()
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]
        auth_code = provider.complete_authorization(
            pending_id=pending_id,
            cred_key="test-cred-key",
        )

        await provider.exchange_authorization_code(client, auth_code)
        # Code should be consumed (one-time use)
        loaded = await provider.load_authorization_code(client, auth_code.code)
        assert loaded is None


# ---------------------------------------------------------------------------
# Access tokens
# ---------------------------------------------------------------------------


class TestAccessTokens:
    @pytest.mark.asyncio
    async def test_load_access_token(self) -> None:
        provider = _make_provider()
        client = _make_client()
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]
        auth_code = provider.complete_authorization(
            pending_id=pending_id,
            cred_key="test-cred-key",
        )
        token = await provider.exchange_authorization_code(client, auth_code)

        access = await provider.load_access_token(token.access_token)
        assert access is not None
        assert isinstance(access, SmartschoolAccessToken)
        assert access.cred_key == "test-cred-key"

    @pytest.mark.asyncio
    async def test_load_unknown_token_returns_none(self) -> None:
        provider = _make_provider()
        assert await provider.load_access_token("nonexistent") is None

    @pytest.mark.asyncio
    async def test_expired_access_token_returns_none(self) -> None:
        provider = _make_provider()
        # Manually insert an expired token
        expired = SmartschoolAccessToken(
            token="expired-token",
            client_id="test",
            scopes=[],
            expires_at=int(time.time()) - 10,
            cred_key="key",
        )
        provider._access_tokens["expired-token"] = expired

        result = await provider.load_access_token("expired-token")
        assert result is None


# ---------------------------------------------------------------------------
# Refresh tokens
# ---------------------------------------------------------------------------


class TestRefreshTokens:
    @pytest.mark.asyncio
    async def test_refresh_token_exchange_rotates_tokens(self) -> None:
        provider = _make_provider()
        client = _make_client()
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]
        auth_code = provider.complete_authorization(
            pending_id=pending_id,
            cred_key="test-cred-key",
        )
        original = await provider.exchange_authorization_code(client, auth_code)

        # Load and exchange refresh token
        rt = await provider.load_refresh_token(client, original.refresh_token)
        assert rt is not None
        assert isinstance(rt, SmartschoolRefreshToken)

        new_token = await provider.exchange_refresh_token(client, rt, ["read"])
        assert new_token.access_token != original.access_token
        assert new_token.refresh_token != original.refresh_token

        # Old refresh token should be gone
        old_rt = await provider.load_refresh_token(client, original.refresh_token)
        assert old_rt is None

        # New tokens carry the same cred_key
        new_access = await provider.load_access_token(new_token.access_token)
        assert new_access is not None
        assert new_access.cred_key == "test-cred-key"

    @pytest.mark.asyncio
    async def test_load_refresh_token_wrong_client(self) -> None:
        provider = _make_provider()
        client = _make_client()
        other = _make_client(client_id="other")
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]
        auth_code = provider.complete_authorization(
            pending_id=pending_id,
            cred_key="key",
        )
        token = await provider.exchange_authorization_code(client, auth_code)

        rt = await provider.load_refresh_token(other, token.refresh_token)
        assert rt is None


# ---------------------------------------------------------------------------
# Token revocation
# ---------------------------------------------------------------------------


class TestRevocation:
    @pytest.mark.asyncio
    async def test_revoke_access_token(self) -> None:
        provider = _make_provider()
        client = _make_client()
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]
        auth_code = provider.complete_authorization(
            pending_id=pending_id,
            cred_key="key",
        )
        token = await provider.exchange_authorization_code(client, auth_code)

        access = await provider.load_access_token(token.access_token)
        assert access is not None

        await provider.revoke_token(access)
        assert await provider.load_access_token(token.access_token) is None

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self) -> None:
        provider = _make_provider()
        client = _make_client()
        params = _make_auth_params()

        url = await provider.authorize(client, params)
        pending_id = url.split("pending=")[1]
        auth_code = provider.complete_authorization(
            pending_id=pending_id,
            cred_key="key",
        )
        token = await provider.exchange_authorization_code(client, auth_code)

        rt = await provider.load_refresh_token(client, token.refresh_token)
        assert rt is not None

        await provider.revoke_token(rt)
        assert await provider.load_refresh_token(client, token.refresh_token) is None


# ---------------------------------------------------------------------------
# Credential store
# ---------------------------------------------------------------------------


class TestCredentialStore:
    def test_get_credentials(self) -> None:
        creds = AppCredentials(
            username="user", password="pass", main_url="school.be", mfa=""
        )
        _credential_store["test-key"] = creds
        try:
            result = get_credentials("test-key")
            assert result is not None
            assert result.username == "user"
        finally:
            _credential_store.pop("test-key", None)

    def test_get_credentials_missing(self) -> None:
        assert get_credentials("nonexistent") is None
