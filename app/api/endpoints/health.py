"""Health check API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import structlog

from app.services.health_service import HealthService, HealthStatus

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize health service
health_service = HealthService()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "message": "StudyRAG API is running"
    }


@router.get("/detailed")
async def detailed_health_check(
    force_refresh: bool = Query(False, description="Force refresh of cached health status")
):
    """Detailed health check with all service statuses."""
    try:
        health_status = await health_service.get_health_status(force_refresh=force_refresh)
        
        # Return appropriate HTTP status code based on health
        if health_status["status"] == HealthStatus.UNHEALTHY:
            raise HTTPException(status_code=503, detail=health_status)
        elif health_status["status"] == HealthStatus.DEGRADED:
            # Return 200 but with degraded status for monitoring
            pass
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Health check failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": HealthStatus.UNHEALTHY,
                "error": "Health check failed",
                "details": str(e)
            }
        )


@router.get("/ready")
async def readiness_check():
    """Readiness check for load balancers and orchestrators."""
    try:
        readiness_status = await health_service.get_readiness_status()
        
        if not readiness_status["ready"]:
            raise HTTPException(status_code=503, detail=readiness_status)
        
        return readiness_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness check failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "error": str(e)
            }
        )


@router.get("/live")
async def liveness_check():
    """Liveness check for orchestrators (simple ping)."""
    return {
        "alive": True,
        "message": "Service is alive"
    }


@router.get("/service/{service_name}")
async def service_health_check(service_name: str):
    """Check health of a specific service."""
    try:
        service_status = await health_service.check_service_connectivity(service_name)
        
        if service_status["status"] == HealthStatus.UNHEALTHY:
            raise HTTPException(status_code=503, detail=service_status)
        
        return service_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Service health check failed",
            service_name=service_name,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "service": service_name,
                "status": HealthStatus.UNHEALTHY,
                "error": str(e)
            }
        )