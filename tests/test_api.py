"""Tests for the RemiApiClient."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.urbanhello_remi_unofficial.api import (
    RemiApiClient,
    RemiApiError,
    RemiAuthError,
)
from custom_components.urbanhello_remi_unofficial.const import (
    API_APP_ID,
    API_BASE_URL,
)

from .conftest import (
    MOCK_INSTALLATION_ID,
    MOCK_LOGIN_RESPONSE,
    MOCK_PASSWORD,
    MOCK_REMI_DATA,
    MOCK_REMI_ID,
    MOCK_SESSION_TOKEN,
    MOCK_USERNAME,
)


def _make_response(status: int, json_data: Any) -> MagicMock:
    """Build a mock aiohttp response."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    resp.text = AsyncMock(return_value=str(json_data))
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


@pytest.fixture
def mock_session() -> MagicMock:
    """Return a mock aiohttp.ClientSession."""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.post = MagicMock()
    session.request = MagicMock()
    return session


@pytest.fixture
def client(mock_session: MagicMock) -> RemiApiClient:
    """Return a RemiApiClient with a mock session."""
    c = RemiApiClient(MOCK_USERNAME, MOCK_PASSWORD, mock_session, MOCK_INSTALLATION_ID)
    c._session_token = MOCK_SESSION_TOKEN
    c._remi_id = MOCK_REMI_ID
    return c


class TestRemiApiClientInit:
    """Tests for RemiApiClient initialisation."""

    def test_initial_state(self, mock_session: MagicMock) -> None:
        c = RemiApiClient(MOCK_USERNAME, MOCK_PASSWORD, mock_session)
        assert c.remi_id is None
        assert c.session_token is None

    def test_set_remi_id(self, client: RemiApiClient) -> None:
        client.set_remi_id("new_id")
        assert client.remi_id == "new_id"

    def test_base_headers_unauthenticated(self, client: RemiApiClient) -> None:
        headers = client._base_headers(authenticated=False)
        assert "X-Parse-Session-Token" not in headers
        assert headers["X-Parse-Application-Id"] == API_APP_ID

    def test_base_headers_authenticated(self, client: RemiApiClient) -> None:
        headers = client._base_headers(authenticated=True)
        assert headers["X-Parse-Session-Token"] == MOCK_SESSION_TOKEN


class TestLogin:
    """Tests for RemiApiClient.login()."""

    async def test_login_success_single_device(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.post.return_value = _make_response(200, MOCK_LOGIN_RESPONSE)

        token, remi_id, all_ids = await client.login()

        assert token == MOCK_SESSION_TOKEN
        assert remi_id == MOCK_REMI_ID
        assert all_ids == [MOCK_REMI_ID]
        assert client.session_token == MOCK_SESSION_TOKEN
        assert client.remi_id == MOCK_REMI_ID

    async def test_login_success_multiple_devices(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        response = {
            **MOCK_LOGIN_RESPONSE,
            "remis": [MOCK_REMI_ID, "remi_id_2"],
        }
        mock_session.post.return_value = _make_response(200, response)

        _, _, all_ids = await client.login()

        assert all_ids == [MOCK_REMI_ID, "remi_id_2"]

    async def test_login_no_remis_falls_back_to_current(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        response = {**MOCK_LOGIN_RESPONSE, "remis": []}
        mock_session.post.return_value = _make_response(200, response)

        _, _, all_ids = await client.login()

        assert all_ids == [MOCK_REMI_ID]

    async def test_login_401_raises_auth_error(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.post.return_value = _make_response(401, {"error": "Unauthorized"})

        with pytest.raises(RemiAuthError):
            await client.login()

    async def test_login_500_raises_api_error(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.post.return_value = _make_response(500, {"error": "Server Error"})

        with pytest.raises(RemiApiError):
            await client.login()

    async def test_login_missing_session_token_raises_auth_error(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        response = {**MOCK_LOGIN_RESPONSE, "sessionToken": None}
        mock_session.post.return_value = _make_response(200, response)

        with pytest.raises(RemiAuthError):
            await client.login()

    async def test_login_missing_current_remi_raises_auth_error(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        response = {**MOCK_LOGIN_RESPONSE, "currentRemi": {}}
        mock_session.post.return_value = _make_response(200, response)

        with pytest.raises(RemiAuthError):
            await client.login()


class TestRequest:
    """Tests for RemiApiClient._request()."""

    async def test_request_success(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _make_response(200, {"results": []})

        result = await client._request("GET", "/parse/test")

        assert result == {"results": []}

    async def test_request_201_success(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _make_response(201, {"objectId": "new_id"})

        result = await client._request("POST", "/parse/classes/Event", {})

        assert result == {"objectId": "new_id"}

    async def test_request_non_200_raises_api_error(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _make_response(400, {"error": "Bad Request"})

        with pytest.raises(RemiApiError, match="400"):
            await client._request("GET", "/parse/test")

    async def test_request_401_triggers_reauth(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        """On 401, the client should re-login and retry once."""
        resp_401 = _make_response(401, {"error": "Unauthorized"})
        resp_ok = _make_response(200, {"results": [MOCK_REMI_DATA]})
        mock_session.request.side_effect = [resp_401, resp_ok]
        mock_session.post.return_value = _make_response(200, MOCK_LOGIN_RESPONSE)

        result = await client._request("POST", "/parse/classes/Remi", {})

        assert result == {"results": [MOCK_REMI_DATA]}
        mock_session.post.assert_called_once()

    async def test_request_401_no_retry_raises_api_error(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        """With retry_auth=False, a 401 should raise immediately."""
        mock_session.request.return_value = _make_response(401, {"error": "Unauthorized"})

        with pytest.raises(RemiApiError):
            await client._request("GET", "/parse/test", retry_auth=False)


class TestGetRemi:
    """Tests for RemiApiClient.get_remi()."""

    async def test_get_remi_success(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _make_response(200, {"results": [MOCK_REMI_DATA]})

        result = await client.get_remi()

        assert result == MOCK_REMI_DATA

    async def test_get_remi_empty_results_raises(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _make_response(200, {"results": []})

        with pytest.raises(RemiApiError, match="No Remi device found"):
            await client.get_remi()

    @pytest.mark.parametrize("response", [{"objectId": "other-device"}, {"lux": 12}])
    async def test_rejects_wrong_or_missing_device(self, client, mock_session, response):
        mock_session.request.return_value = _make_response(200, {"results": [response]})
        with pytest.raises(RemiApiError, match="does not match"):
            await client.get_remi()

    async def test_reauth_preserves_selected_device_for_subsequent_reads(self, client, mock_session):
        mock_session.request.side_effect = [
            _make_response(401, {}),
            _make_response(200, {"results": [MOCK_REMI_DATA]}),
            _make_response(200, {"results": []}),
        ]
        mock_session.post.return_value = _make_response(200, {
            **MOCK_LOGIN_RESPONSE,
            "sessionToken": "replacement-token",
            "currentRemi": {"objectId": "other-device"},
            "remis": [MOCK_REMI_ID, "other-device"],
        })
        assert await client.get_remi() == MOCK_REMI_DATA
        await client.get_events()
        assert client.remi_id == MOCK_REMI_ID
        assert client.session_token == "replacement-token"
        calls = mock_session.request.call_args_list
        assert len(calls) == 3
        assert all(call.args[0] == "POST" for call in calls)
        assert all(call.kwargs["json"]["_method"] == "GET" for call in calls)
        assert calls[0].kwargs["json"]["where"]["objectId"] == MOCK_REMI_ID
        assert calls[1].kwargs["json"]["where"]["objectId"] == MOCK_REMI_ID
        assert calls[2].kwargs["json"]["where"]["remi"]["objectId"] == MOCK_REMI_ID
        mock_session.post.assert_called_once()

    async def test_error_does_not_expose_path_or_body(self, client, mock_session):
        response = _make_response(403, {"error": "private-token private-device"})
        mock_session.request.return_value = response
        with pytest.raises(RemiApiError) as exc:
            await client._request("GET", "/private-device")
        assert str(exc.value) == "API error 403"
        response.text.assert_not_awaited()

    async def test_wrong_device_after_reauth_is_rejected(self, client, mock_session):
        mock_session.request.side_effect = [
            _make_response(401, {}),
            _make_response(200, {"results": [{"objectId": "other-device", "lux": 2}]}),
        ]
        mock_session.post.return_value = _make_response(200, {
            **MOCK_LOGIN_RESPONSE, "currentRemi": {"objectId": "other-device"},
        })
        with pytest.raises(RemiApiError, match="does not match"):
            await client.get_remi()
        assert client.remi_id == MOCK_REMI_ID


class TestGetEvents:
    """Tests for RemiApiClient.get_events()."""

    async def test_get_events_success(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        events = [{"objectId": "ev1", "name": "Wake Up"}]
        mock_session.request.return_value = _make_response(200, {"results": events})

        result = await client.get_events()

        assert result == events

    async def test_get_events_empty(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _make_response(200, {"results": []})

        result = await client.get_events()

        assert result == []


class TestEventCrud:
    """Tests for alarm event CRUD methods."""

    async def test_create_event(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _make_response(201, {"objectId": "new_ev"})

        result = await client.create_event({"name": "Test", "enabled": True})

        assert result["objectId"] == "new_ev"
        call_kwargs = mock_session.request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs.args[2] if len(call_kwargs.args) > 2 else call_kwargs.kwargs["json"]
        assert payload["remi"]["objectId"] == MOCK_REMI_ID

    async def test_update_event(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _make_response(200, {"updatedAt": "2024-01-01"})

        result = await client.update_event("ev1", {"enabled": False})

        assert "updatedAt" in result

    async def test_delete_event(self, client: RemiApiClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _make_response(200, {})

        await client.delete_event("ev1")

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args.args[0] == "DELETE"
