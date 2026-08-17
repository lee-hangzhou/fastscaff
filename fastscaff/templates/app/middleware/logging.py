import time
from typing import Callable, Dict, Optional, Union

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logger import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    MAX_BODY_LOG_SIZE = 4096

    def __init__(
        self,
        app,
        log_request_body: bool = True,
        log_response_body: bool = True,
        log_query: bool = True,
        exclude_paths: Optional[list[str]] = None,
    ) -> None:
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.log_query = log_query
        self.exclude_paths = set(exclude_paths or ["/health", "/metrics"])

    def _should_skip(self, path: str) -> bool:
        for excluded in self.exclude_paths:
            if path == excluded or path.startswith(excluded.rstrip("/") + "/"):
                return True
            # Match /api/v1/health when excluded is /health
            if path.endswith(excluded) or f"{excluded}/" in path:
                return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self._should_skip(request.url.path):
            return await call_next(request)

        request_body: Optional[str] = None
        if self.log_request_body:
            request_body = await self._get_request_body(request)

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # Handlers own error logging; avoid duplicate stacks here.
            raise

        latency = self._format_latency(time.perf_counter() - start_time)
        response_body: Optional[str] = None
        if self.log_response_body:
            response, response_body = await self._capture_response_body(response)

        fields: Dict[str, Union[str, int, None]] = {
            "method": request.method,
            "path": request.url.path,
            "query": (request.url.query or None) if self.log_query else None,
            "status": response.status_code,
            "latency": latency,
            "ip": self._get_client_ip(request),
            "request": request_body,
            "response": response_body,
            "trace_id": getattr(request.state, "trace_id", None),
        }

        if response.status_code >= 500:
            logger.error("access log", **fields)
        elif response.status_code >= 400:
            logger.warning("access log", **fields)
        else:
            logger.info("access log", **fields)

        return response

    @staticmethod
    def _format_latency(seconds: float) -> str:
        return f"{seconds * 1000:.1f}ms"

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def _get_request_body(self, request: Request) -> Optional[str]:
        if request.method not in {"POST", "PUT", "PATCH"}:
            return None

        content_type = request.headers.get("content-type", "")
        if content_type.startswith("multipart/form-data"):
            return "[multipart/form-data]"

        try:
            body_bytes = await request.body()

            async def receive() -> Dict[str, Union[str, bytes]]:
                return {"type": "http.request", "body": body_bytes}

            request._receive = receive
            return self._truncate(body_bytes)
        except (UnicodeDecodeError, RuntimeError):
            return "[unable to read body]"

    async def _capture_response_body(
        self,
        response: Response,
    ) -> tuple[Response, Optional[str]]:
        body = getattr(response, "body", None)
        if body is None:
            return response, None
        if not isinstance(body, (bytes, bytearray)):
            return response, None
        return response, self._truncate(bytes(body))

    def _truncate(self, body_bytes: bytes) -> Optional[str]:
        if not body_bytes:
            return None
        text = body_bytes.decode("utf-8", errors="replace")
        if len(body_bytes) > self.MAX_BODY_LOG_SIZE:
            return text[: self.MAX_BODY_LOG_SIZE] + "...[truncated]"
        return text
