import uvicorn
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.lifespan import lifespan
from app.exceptions.handlers import register_exception_handlers
from app.middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    TracingMiddleware,
    setup_cors,
)
# Optional middleware (uncomment to enable):
# from app.middleware import JWTAuthMiddleware, SignatureMiddleware


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Middleware order matters: first added = last executed
    # Recommended order: CORS -> Security -> Tracing -> Auth -> Logging

    setup_cors(application)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(TracingMiddleware)
    application.add_middleware(RequestLoggingMiddleware)

    # Optional: JWT authentication middleware (validates token on all requests)
    # application.add_middleware(
    #     JWTAuthMiddleware,
    #     whitelist=["/health", "/docs", "/redoc", "/openapi.json"],
    #     whitelist_prefixes=["/api/v1/auth"],
    # )

    # Optional: Request signature verification (for API security)
    # application.add_middleware(
    #     SignatureMiddleware,
    #     secret_key=settings.SIGN_SECRET_KEY,
    #     whitelist=["/health", "/docs"],
    # )

    register_exception_handlers(application)

    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
