"""HTTP client for communicating with Recipe Finder API."""

from collections.abc import Sequence
from types import TracebackType

import httpx

from recipe_finder import __version__
from recipe_finder.config import CONNECT_TIMEOUT, DEFAULT_API_URL, READ_TIMEOUT
from recipe_finder.schemas import (
    CategoryResponse,
    EventRequest,
    IngredientSuggestionResponse,
    LanguageResponse,
    RecipeResponse,
    SearchRequest,
    SearchResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionUpdateRequest,
)


class ApiClientError(Exception):
    """Exception raised when an API request fails."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        is_server_error: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.is_server_error = is_server_error


class ApiClient:
    """Client for calling Recipe Finder API endpoints."""

    def __init__(
        self,
        base_url: str = DEFAULT_API_URL,
        session_id: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_id = session_id
        self.timeout = httpx.Timeout(
            connect=CONNECT_TIMEOUT,
            read=timeout or READ_TIMEOUT,
            write=READ_TIMEOUT,
            pool=CONNECT_TIMEOUT,
        )
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def __enter__(self) -> "ApiClient":
        self._client.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> None:
        self._client.__exit__(exc_type, exc_val, exc_tb)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def _get_headers(self) -> dict[str, str]:
        headers = {"X-App-Version": __version__}
        if self.session_id is not None:
            headers["X-Session-Id"] = str(self.session_id)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        json_data: dict[str, object] | Sequence[object] | None = None,
    ) -> httpx.Response:
        try:
            response = self._client.request(
                method=method,
                url=path,
                params=params,
                json=json_data,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response
        except httpx.TransportError as exc:
            raise ApiClientError(
                message="Cannot reach the API server.",
                error_code="server_unavailable",
                is_server_error=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            error_code: str | None = None
            try:
                body = exc.response.json()
                if isinstance(body, dict):
                    detail = body.get("detail")
                    if isinstance(detail, str):
                        error_code = detail
            except ValueError:
                pass
            message = error_code or f"API returned status {exc.response.status_code}"
            is_server = exc.response.status_code >= 500
            raise ApiClientError(
                message=message,
                error_code=error_code,
                is_server_error=is_server,
            ) from exc
        except Exception as exc:
            raise ApiClientError(
                message=str(exc),
                error_code="unexpected_error",
                is_server_error=True,
            ) from exc

    def get_languages(self) -> list[LanguageResponse]:
        """Fetch supported languages."""
        res = self._request("GET", "/languages")
        return [LanguageResponse.model_validate(item) for item in res.json()]

    def get_categories(self, lang: str = "en") -> list[CategoryResponse]:
        """Fetch categories localized in lang."""
        res = self._request("GET", "/categories", params={"lang": lang})
        return [CategoryResponse.model_validate(item) for item in res.json()]

    def get_ingredients(self, lang: str = "en") -> list[IngredientSuggestionResponse]:
        """Fetch every ingredient name and id in lang (for the local cache)."""
        res = self._request("GET", "/ingredients", params={"lang": lang})
        return [IngredientSuggestionResponse.model_validate(item) for item in res.json()]

    def suggest_ingredients(
        self, q: str, lang: str = "en", limit: int = 8
    ) -> list[IngredientSuggestionResponse]:
        """Fetch ingredient suggestions matching query q."""
        res = self._request(
            "GET", "/ingredients/suggest", params={"q": q, "lang": lang, "limit": limit}
        )
        return [IngredientSuggestionResponse.model_validate(item) for item in res.json()]

    def search(self, request: SearchRequest) -> SearchResponse:
        """Search recipes based on nutritional targets and ingredients."""
        res = self._request("POST", "/search", json_data=request.model_dump(exclude_none=True))
        return SearchResponse.model_validate(res.json())

    def get_recipe(self, recipe_id: int, lang: str = "en") -> RecipeResponse:
        """Fetch complete recipe detail by id."""
        res = self._request("GET", f"/recipes/{recipe_id}", params={"lang": lang})
        return RecipeResponse.model_validate(res.json())

    def start_session(self, app_version: str, language_code: str) -> SessionStartResponse:
        """Start a new telemetry session."""
        req = SessionStartRequest(app_version=app_version, language_code=language_code)
        res = self._request("POST", "/sessions", json_data=req.model_dump())
        data = SessionStartResponse.model_validate(res.json())
        self.session_id = data.session_id
        return data

    def update_session(self, session_id: int, update: SessionUpdateRequest) -> None:
        """Update session language or end time."""
        self._request(
            "PATCH",
            f"/sessions/{session_id}",
            json_data=update.model_dump(mode="json", exclude_none=True),
        )

    def send_event(self, event: EventRequest) -> None:
        """Send a telemetry event."""
        self._request("POST", "/events", json_data=event.model_dump(mode="json"))

    def check_health(self) -> bool:
        """Check if API is accessible and healthy."""
        try:
            self.get_languages()
            return True
        except ApiClientError:
            return False
