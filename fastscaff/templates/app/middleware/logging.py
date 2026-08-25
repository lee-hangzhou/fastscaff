import time
from typing import Dict, Optional, Union

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logger import logger

MAX_BODY_LOG_SIZE = 4096


def _is_loggable_media_type(content_type: str) -> bool:
    """Report whether a response body with this content type is worth logging."""
    media_type = content_type.split(";", 1)[0].strip().lower()
    # An SSE body is an open-ended frame stream: buffering it grows with the stream, and the
    # kept prefix would only ever hold the first few frames.
    if media_type == "text/event-stream":
        return False
    return media_type.startswith("text/") or media_type == "application/json" or media_type.endswith("+json")


class _BodyPrefix:
    """Accumulate a bounded byte prefix, counting the overflow without keeping it."""

    def __init__(self, limit: int) -> None:
        """Remember how many bytes may be kept."""
        self._limit = limit
        self._chunks: list[bytes] = []
        self._captured = 0
        self._total = 0

    def feed(self, chunk: bytes) -> None:
        """Take in one more slice of body bytes."""
        self._total += len(chunk)
        if self._captured >= self._limit:
            return
        kept = chunk[: self._limit - self._captured]
        self._chunks.append(kept)
        self._captured += len(kept)

    def render(self) -> Optional[str]:
        """Return the loggable text, or None when no byte was ever seen."""
        if self._total == 0:
            return None
        text = b"".join(self._chunks).decode("utf-8", errors="replace")
        if self._total > self._limit:
            return f"{text}...[truncated]"
        return text


class RequestLoggingMiddleware:
    """Access log as pure ASGI middleware: it observes body bytes without rewriting messages.

    Request and response bodies are recorded as-is, with no field redaction. Add redaction
    before exposing these logs to anything outside the owning team, since auth payloads carry
    credentials and tokens.

    BaseHTTPMiddleware is deliberately avoided. It wraps every layer in an anyio task group and
    wraps receive, and the usual "read the body, then replace receive so downstream can replay it"
    trick makes the stand-in yield http.request forever: a streaming response's disconnect
    listener then raises RuntimeError, and a real disconnect never reaches downstream. Starlette's
    own _CachedRequest already replays a body read inside dispatch, so that trick is both
    redundant and harmful. Response bodies are unreachable there anyway, because call_next hands
    back a _StreamingResponse that carries no .body attribute.
    """

    def __init__(
        self,
        app: ASGIApp,
        log_query: bool = True,
        exclude_paths: Optional[list[str]] = None,
    ) -> None:
        """Keep the downstream app and the skip rules."""
        self.app = app
        self.log_query = log_query
        self.exclude_paths = set(exclude_paths or ["/health", "/metrics"])

    def _should_skip(self, path: str) -> bool:
        """Report whether this path is excluded from the access log."""
        for excluded in self.exclude_paths:
            if path == excluded or path.startswith(excluded.rstrip("/") + "/"):
                return True
            # Match /api/v1/health when excluded is /health
            if path.endswith(excluded) or f"{excluded}/" in path:
                return True
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Log one HTTP round trip with its metadata and truncated bodies."""
        if scope["type"] != "http" or self._should_skip(scope["path"]):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        is_multipart = headers.get("content-type", "").startswith("multipart/form-data")
        request_prefix = _BodyPrefix(MAX_BODY_LOG_SIZE)

        async def receive_logging() -> Message:
            """Hand the downstream app the untouched message, copying a body prefix on the way."""
            message = await receive()
            # The original message object must be returned: build a stand-in here and
            # http.disconnect can never reach downstream again.
            if not is_multipart and message["type"] == "http.request":
                request_prefix.feed(message.get("body", b""))
            return message

        status_code: Optional[int] = None
        capture_response = False
        response_prefix = _BodyPrefix(MAX_BODY_LOG_SIZE)

        async def send_logging(message: Message) -> None:
            """Copy a response body prefix, then emit the original message."""
            nonlocal status_code, capture_response
            # Any message type not handled here is forwarded verbatim.
            if message["type"] == "http.response.start":
                status_code = message["status"]
                capture_response = _is_loggable_media_type(Headers(raw=message["headers"]).get("content-type", ""))
            elif message["type"] == "http.response.body" and capture_response:
                response_prefix.feed(message.get("body", b""))
            await send(message)

        start_time = time.perf_counter()
        await self.app(scope, receive_logging, send_logging)
        latency = self._format_latency(time.perf_counter() - start_time)

        # No response start means the round trip never completed, so the status is unknown.
        # Leave it to the error log rather than inventing one.
        if status_code is None:
            return

        fields: Dict[str, Union[str, int, None]] = {
            "method": scope["method"],
            "path": scope["path"],
            "query": scope["query_string"].decode("utf-8", errors="replace") if self.log_query else None,
            "status": status_code,
            "latency": latency,
            "ip": self._client_ip(headers, scope),
            "request": "[multipart/form-data]" if is_multipart else request_prefix.render(),
            "response": response_prefix.render(),
            "trace_id": scope.get("state", {}).get("trace_id"),
        }

        if status_code >= 500:
            logger.error("access log", **fields)
        elif status_code >= 400:
            logger.warning("access log", **fields)
        else:
            logger.info("access log", **fields)

    @staticmethod
    def _format_latency(seconds: float) -> str:
        """Render elapsed seconds as a millisecond string."""
        return f"{seconds * 1000:.1f}ms"

    @staticmethod
    def _client_ip(headers: Headers, scope: Scope) -> str:
        """Resolve the client IP, preferring the proxy forwarding header."""
        forwarded = headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = scope.get("client")
        if client:
            return client[0]
        return "unknown"
