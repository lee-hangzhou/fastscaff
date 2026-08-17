import hashlib
import hmac
import json
import time
from typing import Any, Callable, Dict, List, Optional, Set, Union

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.exceptions.codes import ErrInvalidParams, ErrUnauthorized
from app.exceptions.handlers import build_error_response, log_app_error


class SignatureMiddleware(BaseHTTPMiddleware):
    """Request signature verification using HMAC-SHA256."""

    def __init__(
        self,
        app,
        secret_key: Optional[str] = None,
        whitelist: Optional[List[str]] = None,
        whitelist_prefixes: Optional[List[str]] = None,
        timestamp_tolerance: int = 300,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self.secret_key: Optional[str] = secret_key or getattr(
            settings, "SIGN_SECRET_KEY", None
        )
        self.whitelist: Set[str] = set(whitelist or [])
        self.whitelist_prefixes: List[str] = whitelist_prefixes or []
        self.timestamp_tolerance = timestamp_tolerance
        self.enabled = enabled
        self._used_nonces: Dict[str, float] = {}

    def _is_whitelisted(self, path: str) -> bool:
        if path in self.whitelist:
            return True

        for prefix in self.whitelist_prefixes:
            if path.startswith(prefix):
                return True

        return False

    def _cleanup_nonces(self) -> None:
        now = time.time()
        expired = [
            nonce
            for nonce, ts in self._used_nonces.items()
            if now - ts > self.timestamp_tolerance * 2
        ]
        for nonce in expired:
            del self._used_nonces[nonce]

    def _calculate_signature(
        self,
        params: Dict[str, Any],
        timestamp: str,
        nonce: str,
    ) -> str:
        if self.secret_key is None:
            raise ValueError("Secret key is not configured")

        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        sign_str = f"{param_str}&timestamp={timestamp}&nonce={nonce}"

        return hmac.new(
            self.secret_key.encode(),
            sign_str.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled or not self.secret_key:
            return await call_next(request)

        path = request.url.path

        if self._is_whitelisted(path):
            return await call_next(request)

        timestamp = request.headers.get("X-Timestamp")
        nonce = request.headers.get("X-Nonce")
        signature = request.headers.get("X-Signature")

        if not timestamp or not nonce or not signature:
            err = ErrInvalidParams.new("Missing signature headers")
            log_app_error(request, err)
            return build_error_response(err)

        try:
            ts = int(timestamp)
        except ValueError:
            err = ErrInvalidParams.new("Invalid timestamp format")
            log_app_error(request, err)
            return build_error_response(err)

        now = int(time.time())
        if abs(now - ts) > self.timestamp_tolerance:
            err = ErrInvalidParams.new("Request timestamp expired")
            log_app_error(request, err)
            return build_error_response(err)

        self._cleanup_nonces()

        if nonce in self._used_nonces:
            err = ErrInvalidParams.new("Duplicate request (replay attack detected)")
            log_app_error(request, err)
            return build_error_response(err)

        params: Dict[str, Any] = dict(request.query_params)

        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        body_params = json.loads(body)
                        if isinstance(body_params, dict):
                            params.update(body_params)

                        async def receive() -> Dict[str, Union[str, bytes]]:
                            return {"type": "http.request", "body": body}

                        request._receive = receive
                except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                    pass

        expected_signature = self._calculate_signature(params, timestamp, nonce)

        if not hmac.compare_digest(signature, expected_signature):
            err = ErrUnauthorized.new("Invalid signature")
            log_app_error(request, err)
            return build_error_response(err)

        self._used_nonces[nonce] = time.time()

        return await call_next(request)
