from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    result = pwd_context.verify(plain_password, hashed_password)
    if not isinstance(result, bool):
        raise TypeError(f"Expected bool from verify, got {type(result)}")
    return result


def get_password_hash(password: str) -> str:
    result = pwd_context.hash(password)
    if not isinstance(result, str):
        raise TypeError(f"Expected str from hash, got {type(result)}")
    return result


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {"exp": expire, "sub": str(subject), "type": "access"}
    if extra_data:
        to_encode.update(extra_data)

    result = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    if not isinstance(result, str):
        raise TypeError(f"Expected str from jwt.encode, got {type(result)}")
    return result


def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode: Dict[str, Any] = {"exp": expire, "sub": str(subject), "type": "refresh"}
    result = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    if not isinstance(result, str):
        raise TypeError(f"Expected str from jwt.encode, got {type(result)}")
    return result


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if not isinstance(payload, dict):
            return None
        return payload
    except InvalidTokenError:
        return None
