from typing import Callable, List, Optional, Set

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logger import bind_context
from app.core.security import decode_token
from app.exceptions.codes import ErrInvalidToken, ErrUnauthorized
from app.exceptions.handlers import build_error_response, log_app_error


class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        whitelist: Optional[List[str]] = None,
        whitelist_prefixes: Optional[List[str]] = None,
    ) -> None:
        super().__init__(app)
        self.whitelist: Set[str] = set(whitelist or [])
        self.whitelist_prefixes: List[str] = whitelist_prefixes or []

    def _is_whitelisted(self, path: str) -> bool:
        if path in self.whitelist:
            return True

        for prefix in self.whitelist_prefixes:
            if path.startswith(prefix):
                return True

        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if self._is_whitelisted(path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            err = ErrUnauthorized.new("Missing authorization header")
            log_app_error(request, err)
            return build_error_response(err)

        if not auth_header.startswith("Bearer "):
            err = ErrUnauthorized.new("Invalid authorization header format")
            log_app_error(request, err)
            return build_error_response(err)

        token = auth_header[7:]
        payload = decode_token(token)

        if not payload:
            err = ErrInvalidToken.new()
            log_app_error(request, err)
            return build_error_response(err)

        if payload.get("type") != "access":
            err = ErrInvalidToken.new("Invalid token type")
            log_app_error(request, err)
            return build_error_response(err)

        user_id = payload.get("sub")
        request.state.user_id = user_id
        request.state.user_roles = payload.get("roles", [])
        request.state.token_payload = payload
        if user_id is not None:
            bind_context(user_id=str(user_id))

        return await call_next(request)
