"""Health check service for monitoring system components."""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import structlog

from app.core.config import get_settings
from app.services.vector_database import VectorDatabaseService
from app.services.embedding_service import EmbeddingService
from app.services.ollama_client import OllamaClient

logger = structlog.get_logger(__name__)


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class HealthService:
    """Service for checking health of all system components."""
    
    def __init__(self):
        self.settings = get_settings()
        self._last_check_time = None
        self._cached_status = None
        self._cache_duration = 30  # Cache health status for 30 seconds
    
    async def get_health_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get comprehensive health status of all services.
        
        Args:
            force_refresh: Force refresh of cached status
            
        Returns:
            Dictionary containing health status of all services
        """
        current_time = time.time()
        
        # Return cached status if recent and not forcing refresh
        if (not force_refresh and 
            self._cached_status and 
            self._last_check_time and 
            current_time - self._last_check_time < self._cache_duration):
            return self._cached_status
        
        logger.info("Performing health check", force_refresh=force_refresh)
        
        # Perform health checks concurrently
        health_checks = await asyncio.gather(
            self._check_chroma_health(),
            self._check_ollama_health(),
            self._check_embedding_service_health(),
            self._check_system_resources(),
            return_exceptions=True
        )
        
        chroma_health, ollama_health, embedding_health, system_health = health_checks
        
        # Determine overall status
        service_statuses = [
            chroma_health.get("status", HealthStatus.UNKNOWN) if isinstance(chroma_health, dict) else HealthStatus.UNHEALTHY,
            ollama_health.get("status", HealthStatus.UNKNOWN) if isinstance(ollama_health, dict) else HealthStatus.UNHEALTHY,
            embedding_health.get("status", HealthStatus.UNKNOWN) if isinstance(embedding_health, dict) else HealthStatus.UNHEALTHY,
        ]
        
        # Calculate overall status
        if all(status == HealthStatus.HEALTHY for status in service_statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(status == HealthStatus.HEALTHY for status in service_statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNHEALTHY
        
        # Build comprehensive status
        status = {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "version": self.settings.VERSION,
            "environment": self.settings.ENVIRONMENT,
            "services": {
                "chroma": chroma_health if isinstance(chroma_health, dict) else {
                    "status": HealthStatus.UNHEALTHY,
                    "error": str(chroma_health)
                },
                "ollama": ollama_health if isinstance(ollama_health, dict) else {
                    "status": HealthStatus.UNHEALTHY,
                    "error": str(ollama_health)
                },
                "embeddings": embedding_health if isinstance(embedding_health, dict) else {
                    "status": HealthStatus.UNHEALTHY,
                    "error": str(embedding_health)
                },
                "system": system_health if isinstance(system_health, dict) else {
                    "status": HealthStatus.UNHEALTHY,
                    "error": str(system_health)
                }
            }
        }
        
        # Cache the status
        self._cached_status = status
        self._last_check_time = current_time
        
        logger.info(
            "Health check completed",
            overall_status=overall_status,
            chroma_status=status["services"]["chroma"]["status"],
            ollama_status=status["services"]["ollama"]["status"],
            embedding_status=status["services"]["embeddings"]["status"]
        )
        
        return status
    
    async def _check_chroma_health(self) -> Dict[str, Any]:
        """Check ChromaDB health."""
        try:
            start_time = time.time()
            
            # Initialize vector database
            vector_db = VectorDatabaseService()
            
            # Test connection and basic operations
            await vector_db.connect()
            
            # Test collection operations
            stats = await vector_db.get_collection_stats()
            
            response_time = time.time() - start_time
            
            return {
                "status": HealthStatus.HEALTHY,
                "response_time": round(response_time, 3),
                "url": self.settings.chroma_url,
                "collection_name": self.settings.CHROMA_COLLECTION_NAME,
                "details": stats
            }
            
        except Exception as e:
            logger.error("ChromaDB health check failed", error=str(e), exc_info=True)
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "url": self.settings.chroma_url
            }
    
    async def _check_ollama_health(self) -> Dict[str, Any]:
        """Check Ollama health."""
        try:
            start_time = time.time()
            
            # Initialize Ollama client
            ollama_client = OllamaClient()
            
            # Test connection
            is_available = await ollama_client.is_available()
            
            if not is_available:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "error": "Ollama service not available",
                    "url": self.settings.ollama_url
                }
            
            # Get available models
            models = await ollama_client.list_models()
            
            # Check if configured model is available
            configured_model = self.settings.OLLAMA_MODEL
            model_available = any(model.get("name") == configured_model for model in models)
            
            response_time = time.time() - start_time
            
            status = HealthStatus.HEALTHY if model_available else HealthStatus.DEGRADED
            
            return {
                "status": status,
                "response_time": round(response_time, 3),
                "url": self.settings.ollama_url,
                "configured_model": configured_model,
                "model_available": model_available,
                "available_models": [model.get("name") for model in models],
                "models_count": len(models)
            }
            
        except Exception as e:
            logger.error("Ollama health check failed", error=str(e), exc_info=True)
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "url": self.settings.ollama_url
            }
    
    async def _check_embedding_service_health(self) -> Dict[str, Any]:
        """Check embedding service health."""
        try:
            start_time = time.time()
            
            # Initialize embedding service
            embedding_service = EmbeddingService()
            
            # Test model loading and embedding generation
            test_text = "This is a test sentence for health check."
            embedding = await embedding_service.generate_embedding(test_text)
            
            response_time = time.time() - start_time
            
            return {
                "status": HealthStatus.HEALTHY,
                "response_time": round(response_time, 3),
                "current_model": embedding_service.current_model_key,
                "embedding_dimension": len(embedding) if embedding else 0,
                "available_models": list(embedding_service.available_models.keys()),
                "device": embedding_service.device
            }
            
        except Exception as e:
            logger.error("Embedding service health check failed", error=str(e), exc_info=True)
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "current_model": getattr(embedding_service, 'current_model_key', 'unknown') if 'embedding_service' in locals() else 'unknown'
            }
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status based on resource usage
            status = HealthStatus.HEALTHY
            warnings = []
            
            if cpu_percent > 90:
                status = HealthStatus.DEGRADED
                warnings.append(f"High CPU usage: {cpu_percent}%")
            
            if memory.percent > 90:
                status = HealthStatus.DEGRADED
                warnings.append(f"High memory usage: {memory.percent}%")
            
            if disk.percent > 90:
                status = HealthStatus.DEGRADED
                warnings.append(f"High disk usage: {disk.percent}%")
            
            return {
                "status": status,
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": round(disk.percent, 1),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "warnings": warnings
            }
            
        except ImportError:
            # psutil not available
            return {
                "status": HealthStatus.UNKNOWN,
                "error": "psutil not available for system monitoring"
            }
        except Exception as e:
            logger.error("System resource check failed", error=str(e), exc_info=True)
            return {
                "status": HealthStatus.UNKNOWN,
                "error": str(e)
            }
    
    async def check_service_connectivity(self, service_name: str) -> Dict[str, Any]:
        """Check connectivity to a specific service.
        
        Args:
            service_name: Name of service to check (chroma, ollama)
            
        Returns:
            Service connectivity status
        """
        if service_name == "chroma":
            return await self._check_chroma_health()
        elif service_name == "ollama":
            return await self._check_ollama_health()
        elif service_name == "embeddings":
            return await self._check_embedding_service_health()
        else:
            return {
                "status": HealthStatus.UNKNOWN,
                "error": f"Unknown service: {service_name}"
            }
    
    async def get_readiness_status(self) -> Dict[str, Any]:
        """Get readiness status (simplified health check for load balancers)."""
        try:
            # Quick checks for essential services
            chroma_check = await self._quick_chroma_check()
            embedding_check = await self._quick_embedding_check()
            
            ready = chroma_check and embedding_check
            
            return {
                "ready": ready,
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "chroma": chroma_check,
                    "embeddings": embedding_check
                }
            }
            
        except Exception as e:
            logger.error("Readiness check failed", error=str(e), exc_info=True)
            return {
                "ready": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _quick_chroma_check(self) -> bool:
        """Quick ChromaDB connectivity check."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.settings.chroma_url}/api/v1/heartbeat")
                return response.status_code == 200
        except Exception:
            return False
    
    async def _quick_embedding_check(self) -> bool:
        """Quick embedding service check."""
        try:
            embedding_service = EmbeddingService()
            # Just check if we can access the current model
            return embedding_service.current_model_key is not None
        except Exception:
            return False