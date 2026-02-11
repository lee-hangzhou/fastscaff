from typing import Any, Dict, Optional


class AppError(Exception):
    """Base application error with structured error code.

    Can be used directly (e.g. ``raise AppError(40001, "msg")``) or subclassed
    to define reusable error types that are safe under concurrency.
    """

    code: int = 0
    message: str = ""

    def __init__(
        self,
        code: int = 0,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.code = code or self.__class__.code
        self.message = message or self.__class__.message
        self.details = details
        super().__init__(self.message)

    @property
    def status_code(self) -> int:
        if self.code < 1000:
            return self.code
        return self.code // 100


# 400xx - Client errors
class InvalidCredentialsError(AppError):
    code = 40001
    message = "Invalid username or password"


class InvalidTokenError(AppError):
    code = 40002
    message = "Invalid or expired token"


class PermissionDeniedError(AppError):
    code = 40003
    message = "Permission denied"


class UserAlreadyExistsError(AppError):
    code = 40004
    message = "User already exists"


# 404xx - Not found
class NotFoundError(AppError):
    code = 40401
    message = "Resource not found"


class UserNotFoundError(AppError):
    code = 40402
    message = "User not found"


# 500xx - Server errors
class InternalError(AppError):
    code = 50001
    message = "Internal server error"
