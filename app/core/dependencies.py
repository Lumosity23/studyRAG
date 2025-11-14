"""Dependency injection for FastAPI application."""

from functools import lru_cache
from typing import Optional
from fastapi import Depends, HTTPException, Request
import structlog

from app.core.config import get_settings, Settings
from app.services.vector_database import VectorDatabaseService
from app.services.embedding_service import EmbeddingService
from app.services.ollama_client import OllamaClient
from app.services.search_engine import SearchEngine
from app.services.chat_engine import ChatEngine
from app.services.conversation_manager import ConversationManager
from app.services.health_service import HealthService

logger = structlog.get_logger(__name__)


# Configuration dependency
def get_app_settings() -> Settings:
    """Get application settings."""
    return get_settings()


# Database dependencies
@lru_cache()
def get_vector_database() -> VectorDatabaseService:
    """Get vector database instance."""
    return VectorDatabaseService()


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance."""
    return EmbeddingService()


@lru_cache()
def get_ollama_client() -> OllamaClient:
    """Get Ollama client instance."""
    return OllamaClient()


@lru_cache()
def get_conversation_manager() -> ConversationManager:
    """Get conversation manager instance."""
    return ConversationManager()


@lru_cache()
def get_health_service() -> HealthService:
    """Get health service instance."""
    return HealthService()


# Composite service dependencies
def get_search_engine(
    vector_db: VectorDatabaseService = Depends(get_vector_database),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> SearchEngine:
    """Get search engine instance with dependencies."""
    return SearchEngine(vector_db, embedding_service)


def get_chat_engine(
    search_engine: SearchEngine = Depends(get_search_engine),
    ollama_client: OllamaClient = Depends(get_ollama_client),
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
) -> ChatEngine:
    """Get chat engine instance with dependencies."""
    return ChatEngine(search_engine, ollama_client, conversation_manager)


# Request context dependencies
def get_request_id(request: Request) -> str:
    """Get request ID from request state or headers."""
    # Try to get from request state (set by middleware)
    if hasattr(request.state, 'request_id'):
        return request.state.request_id
    
    # Fallback to header
    return request.headers.get("X-Request-ID", "unknown")


def get_client_ip(request: Request) -> str:
    """Get client IP address."""
    # Check for forwarded headers first (for reverse proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


# Authentication dependencies (placeholder for future implementation)
async def get_current_user(request: Request) -> Optional[dict]:
    """Get current authenticated user (placeholder)."""
    # TODO: Implement authentication when needed
    # For now, return None (no authentication)
    return None


def require_authentication(
    current_user: Optional[dict] = Depends(get_current_user)
) -> dict:
    """Require authentication (placeholder)."""
    # TODO: Implement when authentication is needed
    # For now, allow all requests
    return {"user_id": "anonymous", "permissions": ["read", "write"]}


# Service health dependencies
async def require_healthy_vector_db(
    vector_db: VectorDatabaseService = Depends(get_vector_database)
) -> VectorDatabaseService:
    """Ensure vector database is healthy before processing request."""
    try:
        await vector_db.connect()
        return vector_db
    except Exception as e:
        logger.error("Vector database health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "SERVICE_UNAVAILABLE_001",
                "message": "Vector database is not available",
                "service": "chromadb"
            }
        )


async def require_healthy_ollama(
    ollama_client: OllamaClient = Depends(get_ollama_client)
) -> OllamaClient:
    """Ensure Ollama is healthy before processing request."""
    try:
        is_available = await ollama_client.health_check()
        if not is_available:
            raise Exception("Ollama service not available")
        return ollama_client
    except Exception as e:
        logger.error("Ollama health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "SERVICE_UNAVAILABLE_002",
                "message": "Ollama service is not available",
                "service": "ollama"
            }
        )


async def require_healthy_embeddings(
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> EmbeddingService:
    """Ensure embedding service is healthy before processing request."""
    try:
        # Quick health check by accessing current model
        if not embedding_service._active_model_key:
            raise Exception("No embedding model loaded")
        return embedding_service
    except Exception as e:
        logger.error("Embedding service health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "SERVICE_UNAVAILABLE_003",
                "message": "Embedding service is not available",
                "service": "embeddings"
            }
        )


# Validation dependencies
def validate_file_upload(request: Request) -> dict:
    """Validate file upload parameters."""
    settings = get_settings()
    
    # Get content length
    content_length = request.headers.get("Content-Length")
    if content_length:
        content_length = int(content_length)
        if content_length > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail={
                    "error_code": "FILE_TOO_LARGE_001",
                    "message": f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes",
                    "max_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024)
                }
            )
    
    return {"max_file_size": settings.MAX_FILE_SIZE}


def validate_search_params(
    query: str,
    top_k: int = 10,
    min_similarity: float = 0.5
) -> dict:
    """Validate search parameters."""
    if not query or not query.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_QUERY_001",
                "message": "Search query cannot be empty"
            }
        )
    
    if len(query) > 1000:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_QUERY_002",
                "message": "Search query too long (maximum 1000 characters)"
            }
        )
    
    if top_k < 1 or top_k > 100:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_PARAM_001",
                "message": "top_k must be between 1 and 100"
            }
        )
    
    if min_similarity < 0.0 or min_similarity > 1.0:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_PARAM_002",
                "message": "min_similarity must be between 0.0 and 1.0"
            }
        )
    
    return {
        "query": query.strip(),
        "top_k": top_k,
        "min_similarity": min_similarity
    }


# Cleanup dependencies
async def cleanup_resources():
    """Cleanup resources on application shutdown."""
    logger.info("Cleaning up application resources")
    
    # Clear LRU caches
    get_vector_database.cache_clear()
    get_embedding_service.cache_clear()
    get_ollama_client.cache_clear()
    get_conversation_manager.cache_clear()
    get_health_service.cache_clear()
    
    logger.info("Resource cleanup completed")