"""Tests for recipe_finder.api_client with respx."""

import httpx
import pytest
import respx

from recipe_finder.api_client import ApiClient, ApiClientError
from recipe_finder.schemas import SearchRequest


@respx.mock
def test_get_languages_success() -> None:
    respx.get("http://127.0.0.1:8000/languages").respond(
        json=[
            {"language_code": "en", "language_name": "English"},
            {"language_code": "tr", "language_name": "Türkçe"},
        ]
    )

    client = ApiClient()
    langs = client.get_languages()
    assert len(langs) == 2
    assert langs[0].language_code == "en"
    assert langs[1].language_name == "Türkçe"


@respx.mock
def test_suggest_ingredients_success() -> None:
    respx.get("http://127.0.0.1:8000/ingredients/suggest").respond(
        json=[
            {"ingredient_id": 1, "name": "Chicken Breast"},
            {"ingredient_id": 2, "name": "Chicken Thigh"},
        ]
    )

    client = ApiClient()
    suggestions = client.suggest_ingredients("chick", lang="en")
    assert len(suggestions) == 2
    assert suggestions[0].name == "Chicken Breast"


@respx.mock
def test_search_success() -> None:
    respx.post("http://127.0.0.1:8000/search").respond(
        json={"recipe_ids": [10, 20, 30], "total": 3}
    )

    client = ApiClient()
    result = client.search(SearchRequest(min_protein=25))
    assert result.recipe_ids == [10, 20, 30]
    assert result.total == 3


@respx.mock
def test_api_client_error_handling() -> None:
    respx.get("http://127.0.0.1:8000/languages").respond(
        status_code=503,
        json={"detail": "db_unavailable"},
    )

    client = ApiClient()
    with pytest.raises(ApiClientError) as exc_info:
        client.get_languages()

    assert exc_info.value.error_code == "db_unavailable"
    assert exc_info.value.is_server_error is True


@respx.mock
def test_api_client_connection_error() -> None:
    respx.get("http://127.0.0.1:8000/languages").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    client = ApiClient()
    with pytest.raises(ApiClientError) as exc_info:
        client.get_languages()

    assert exc_info.value.error_code == "server_unavailable"
    assert exc_info.value.is_server_error is True


def test_api_client_context_manager_and_close() -> None:
    with ApiClient() as client:
        assert client._client.is_closed is False
    assert client._client.is_closed is True


@pytest.mark.parametrize(
    "error",
    [
        httpx.RemoteProtocolError("Connection closed"),
        httpx.ReadError("Read error"),
        httpx.WriteTimeout("Write timed out"),
    ],
)
@respx.mock
def test_api_client_transport_error(error: Exception) -> None:
    respx.get("http://127.0.0.1:8000/languages").mock(side_effect=error)

    client = ApiClient()
    with pytest.raises(ApiClientError) as exc_info:
        client.get_languages()

    assert exc_info.value.error_code == "server_unavailable"
    assert exc_info.value.is_server_error is True


@respx.mock
def test_api_client_validation_error_with_list_detail() -> None:
    respx.get("http://127.0.0.1:8000/languages").respond(
        status_code=422,
        json={"detail": [{"loc": ["query", "limit"], "msg": "value is not a valid integer"}]},
    )

    client = ApiClient()
    with pytest.raises(ApiClientError) as exc_info:
        client.get_languages()

    assert exc_info.value.error_code is None
    assert exc_info.value.message == "API returned status 422"
    assert exc_info.value.is_server_error is False


@respx.mock
def test_api_client_non_json_error_response() -> None:
    respx.get("http://127.0.0.1:8000/languages").respond(
        status_code=502,
        content=b"Bad Gateway HTML",
    )

    client = ApiClient()
    with pytest.raises(ApiClientError) as exc_info:
        client.get_languages()

    assert exc_info.value.error_code is None
    assert exc_info.value.message == "API returned status 502"
    assert exc_info.value.is_server_error is True


@respx.mock
def test_check_health_success() -> None:
    respx.get("http://127.0.0.1:8000/languages").respond(json=[])

    client = ApiClient()
    assert client.check_health() is True


@respx.mock
def test_check_health_api_client_error() -> None:
    respx.get("http://127.0.0.1:8000/languages").respond(status_code=500)

    client = ApiClient()
    assert client.check_health() is False


def test_check_health_unexpected_error_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ApiClient()

    def buggy_get_languages() -> list[object]:
        raise TypeError("Unexpected code bug")

    monkeypatch.setattr(client, "get_languages", buggy_get_languages)
    with pytest.raises(TypeError, match="Unexpected code bug"):
        client.check_health()
