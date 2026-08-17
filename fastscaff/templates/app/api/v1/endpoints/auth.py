from fastapi import APIRouter, Depends

from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, TokenResponse
from app.schemas.base import Response
from app.services import registry
from app.utils.auth import auth_required

router = APIRouter()


@router.post("/login")
async def login(request: LoginRequest) -> Response[LoginResponse]:
    result = await registry.auth_service.login(request.username, request.password)
    return Response(data=result)


@router.post("/refresh")
async def refresh_token(request: RefreshRequest) -> Response[TokenResponse]:
    result = await registry.auth_service.refresh_token(request.refresh_token)
    return Response(data=result)


@router.post("/logout", dependencies=[Depends(auth_required)])
async def logout() -> Response[None]:
    return Response(data=None, message="Logged out")
