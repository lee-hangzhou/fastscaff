from typing import Any, Dict, Optional


class AppError(Exception):
    def __init__(
        self,
        code: int,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(self.message)

    @property
    def status_code(self) -> int:
        if self.code < 1000:
            return self.code
        return self.code // 100


# 400xx - Client errors
InvalidCredentials = AppError(40001, "Invalid username or password")
InvalidToken = AppError(40002, "Invalid or expired token")
PermissionDenied = AppError(40003, "Permission denied")
UserAlreadyExists = AppError(40004, "User already exists")

# 404xx - Not found
NotFound = AppError(40401, "Resource not found")
UserNotFound = AppError(40402, "User not found")

# 500xx - Server errors
InternalError = AppError(50001, "Internal server error")
