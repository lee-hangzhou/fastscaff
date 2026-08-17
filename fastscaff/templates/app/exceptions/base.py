from typing import Any, Dict, Optional


class AppError(Exception):
    """Business error with a stable client-facing code and optional cause.

    Handlers always return HTTP 200 with ``{code, message, data}``.
    The optional ``cause`` is for logging only and is never returned to clients.
    """

    code: int = 0
    message: str = ""

    def __init__(
        self,
        code: int = 0,
        message: str = "",
        *,
        cause: Optional[BaseException] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.code = code or self.__class__.code
        self.message = message or self.__class__.message
        self.cause = cause
        self.details = details
        super().__init__(self.message)
        if cause is not None:
            self.__cause__ = cause


# 1xxxx — caller / business errors
class InvalidParamsError(AppError):
    code = 10001
    message = "Invalid parameters"


class InvalidCredentialsError(AppError):
    code = 10002
    message = "Invalid username or password"


class UnauthorizedError(AppError):
    code = 10002
    message = "Unauthorized"


class InvalidTokenError(AppError):
    code = 10003
    message = "Invalid or expired token"


class PermissionDeniedError(AppError):
    code = 10004
    message = "Permission denied"


class UserAlreadyExistsError(AppError):
    code = 10005
    message = "User already exists"


class TooManyRequestsError(AppError):
    code = 10006
    message = "Too many requests"


class NotFoundError(AppError):
    code = 10101
    message = "Resource not found"


class UserNotFoundError(AppError):
    code = 10102
    message = "User not found"


# 2xxxx — external / upstream
class ExternalError(AppError):
    code = 20001
    message = "External service error"


# 5xxxx — internal
class InternalError(AppError):
    code = 50001
    message = "Internal server error"
