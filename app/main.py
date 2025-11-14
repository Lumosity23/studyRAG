"""Main FastAPI application entry point."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
import uvicorn
import structlog
from contextlib import asynccontextmanager
import os

from app.core.config import get_settings
from app.core.exceptions import APIException
from app.core.middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    ErrorHandlingMiddleware,
    RateLimitMiddleware,
    setup_logging
)
from app.core.dependencies import cleanup_resources
from app.api.routes import api_router

# Setup logging first
setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    
    # Startup
    logger.info(
        "Starting StudyRAG Application",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG
    )
    
    # Create necessary directories
    settings.create_directories()
    
    # Log configuration
    logger.info(
        "Application configuration",
        chroma_url=settings.chroma_url,
        ollama_url=settings.ollama_url,
        embedding_model=settings.EMBEDDING_MODEL,
        max_file_size_mb=settings.MAX_FILE_SIZE / (1024 * 1024)
    )
    
    yield
    
    # Shutdown
    logger.info("Shutting down StudyRAG Application")
    await cleanup_resources()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title="StudyRAG API",
        description="Retrieval-Augmented Generation system for academic research and document analysis",
        version=settings.VERSION,
        docs_url=None,  # We'll create custom docs endpoints
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Add middleware in reverse order (last added = first executed)
    
    # 1. Error handling (outermost)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # 2. Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 3. Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # 4. Rate limiting (if not in development)
    if settings.ENVIRONMENT != "development":
        app.add_middleware(
            RateLimitMiddleware,
            calls=100,  # 100 requests per minute
            period=60
        )
    
    # 5. Trusted host middleware (production only)
    if settings.ENVIRONMENT == "production":
        allowed_hosts = ["*"]  # Configure based on your domain
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    
    # 6. CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"]
    )
    
    # Exception handlers
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle custom API exceptions."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        logger.error(
            "API exception occurred",
            request_id=request_id,
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
                "timestamp": exc.timestamp.isoformat()
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": request_id
            }
        )
    
    @app.exception_handler(422)
    async def validation_exception_handler(request: Request, exc):
        """Handle validation errors."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors() if hasattr(exc, 'errors') else str(exc),
                "request_id": request_id
            }
        )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoints (at root level for load balancers)
    from app.api.endpoints.health import router as health_router
    app.include_router(health_router, prefix="/health", tags=["health"])
    
    # Serve the web application
    @app.get("/")
    async def serve_app():
        """Serve the main web application."""
        from fastapi.responses import FileResponse
        static_dir = "static"
        index_file = os.path.join(static_dir, "index.html")
        
        if os.path.exists(index_file):
            return FileResponse(index_file)
        else:
            # Fallback to API info if static files not available
            return {
                "name": "StudyRAG API",
                "version": settings.VERSION,
                "status": "running",
                "docs_url": "/docs" if settings.DEBUG else None,
                "health_url": "/health",
                "message": "Web interface not available. Static files not found."
            }
    
    # Custom documentation endpoints (only in debug mode)
    if settings.DEBUG:
        @app.get("/docs", include_in_schema=False)
        async def custom_swagger_ui_html():
            """Custom Swagger UI."""
            return get_swagger_ui_html(
                openapi_url="/api/openapi.json",
                title=f"{app.title} - Swagger UI",
                oauth2_redirect_url="/docs/oauth2-redirect",
                swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
                swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            )
        
        @app.get("/redoc", include_in_schema=False)
        async def redoc_html():
            """Custom ReDoc."""
            return get_redoc_html(
                openapi_url="/api/openapi.json",
                title=f"{app.title} - ReDoc",
                redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
            )
    
    # Serve static files (if directory exists)
    static_dir = "static"
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    

    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    
    # Configure uvicorn logging
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["default"],
        },
    }
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        log_config=log_config if settings.LOG_FORMAT != "json" else None,
        access_log=settings.DEBUG
    )