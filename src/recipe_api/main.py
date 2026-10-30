"""Creates the FastAPI app and adds the routers."""

from fastapi import FastAPI, HTTPException, status
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from recipe_api.routers import lookup, recipes, telemetry

MAX_BODY_BYTES = 64 * 1024
PAYLOAD_TOO_LARGE_CODE = "payload_too_large"


class BodySizeLimitMiddleware:
    """Reject requests whose body is bigger than the limit, with a short error code."""

    def __init__(self, app: ASGIApp, max_body_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None and int(content_length) > self.max_body_bytes:
            response = JSONResponse(
                {"detail": PAYLOAD_TOO_LARGE_CODE},
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, self._limit_stream(receive), send)

    def _limit_stream(self, receive: Receive) -> Receive:
        """Count the bytes of a body without Content-Length (chunked) while it is read."""
        received_bytes = 0

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_body_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=PAYLOAD_TOO_LARGE_CODE,
                    )
            return message

        return limited_receive


app = FastAPI(title="Recipe Finder API")
app.add_middleware(BodySizeLimitMiddleware)
app.include_router(lookup.router)
app.include_router(recipes.router)
app.include_router(telemetry.router)
