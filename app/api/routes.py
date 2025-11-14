"""Main API router configuration."""

from fastapi import APIRouter
from app.core.config import get_settings

# Import route modules
from app.api.endpoints import documents, database, search, chat, config

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(database.router, prefix="/database", tags=["database"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(config.router, prefix="/config", tags=["config"])

@api_router.get("/")
async def api_root():
    """API root endpoint."""
    settings = get_settings()
    return {
        "message": "StudyRAG API v1",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "health": "/health",
            "docs": "/docs" if settings.DEBUG else None,
            "openapi": "/api/openapi.json" if settings.DEBUG else None
        }
    }


@api_router.get("/status")
async def api_status():
    """API status endpoint."""
    settings = get_settings()
    return {
        "api_version": "v1",
        "application_version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "services": {
            "chroma_url": settings.chroma_url,
            "ollama_url": settings.ollama_url,
            "embedding_model": settings.EMBEDDING_MODEL
        }
    }