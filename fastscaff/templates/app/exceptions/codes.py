from typing import Optional

from app.exceptions.base import AppError

OK_CODE = 0
OK_MESSAGE = "Success"


class ErrorDef:
    """Sentinel error definition (storyflow-style New / Wrap)."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message

    def new(self, message: Optional[str] = None) -> AppError:
        return AppError(self.code, message or self.message)

    def wrap(self, cause: BaseException, message: Optional[str] = None) -> AppError:
        return AppError(self.code, message or self.message, cause=cause)


# 1xxxx — caller errors
ErrInvalidParams = ErrorDef(10001, "Invalid parameters")
ErrUnauthorized = ErrorDef(10002, "Unauthorized")
ErrInvalidToken = ErrorDef(10003, "Invalid or expired token")
ErrForbidden = ErrorDef(10004, "Permission denied")
ErrConflict = ErrorDef(10005, "Resource already exists")
ErrTooManyRequests = ErrorDef(10006, "Too many requests")
ErrNotFound = ErrorDef(10101, "Resource not found")
ErrUserNotFound = ErrorDef(10102, "User not found")

# 2xxxx — upstream / external
ErrExternal = ErrorDef(20001, "External service error")

# 5xxxx — internal
ErrInternal = ErrorDef(50001, "Internal server error")
