import uvicorn
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.lifespan import lifespan
from app.exceptions.handlers import register_exception_handlers
from app.middleware import (
    DatabaseMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    TracingMiddleware,
    setup_cors,
)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    setup_cors(application)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(DatabaseMiddleware)
    application.add_middleware(TracingMiddleware)
    application.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
