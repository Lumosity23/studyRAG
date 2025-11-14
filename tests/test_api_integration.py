"""Integration tests for FastAPI application."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.health_service import HealthStatus


class TestAPIIntegration:
    """Test API integration and middleware."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "StudyRAG API"
        assert "version" in data
        assert data["status"] == "running"
    
    def test_api_root_endpoint(self, client):
        """Test API root endpoint."""
        response = client.get("/api/v1/")
        
        assert response.status_code == 200
        data = response.json()
        assert "StudyRAG API v1" in data["message"]
        assert "version" in data
        assert "endpoints" in data
    
    def test_api_status_endpoint(self, client):
        """Test API status endpoint."""
        response = client.get("/api/v1/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["api_version"] == "v1"
        assert "application_version" in data
        assert "environment" in data
        assert "services" in data
    
    def test_health_check_basic(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["message"] == "StudyRAG API is running"
    
    def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True
    
    @patch('app.services.health_service.HealthService.get_health_status')
    def test_detailed_health_check_healthy(self, mock_health_status, client):
        """Test detailed health check when all services are healthy."""
        mock_health_status.return_value = {
            "status": HealthStatus.HEALTHY,
            "timestamp": "2024-01-01T00:00:00",
            "version": "0.1.0",
            "environment": "test",
            "services": {
                "chroma": {"status": HealthStatus.HEALTHY},
                "ollama": {"status": HealthStatus.HEALTHY},
                "embeddings": {"status": HealthStatus.HEALTHY},
                "system": {"status": HealthStatus.HEALTHY}
            }
        }
        
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == HealthStatus.HEALTHY
        assert "services" in data
    
    @patch('app.services.health_service.HealthService.get_health_status')
    def test_detailed_health_check_unhealthy(self, mock_health_status, client):
        """Test detailed health check when services are unhealthy."""
        mock_health_status.return_value = {
            "status": HealthStatus.UNHEALTHY,
            "timestamp": "2024-01-01T00:00:00",
            "version": "0.1.0",
            "environment": "test",
            "services": {
                "chroma": {"status": HealthStatus.UNHEALTHY, "error": "Connection failed"},
                "ollama": {"status": HealthStatus.UNHEALTHY, "error": "Service unavailable"},
                "embeddings": {"status": HealthStatus.UNHEALTHY, "error": "Model not loaded"},
                "system": {"status": HealthStatus.HEALTHY}
            }
        }
        
        response = client.get("/health/detailed")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == HealthStatus.UNHEALTHY
    
    @patch('app.services.health_service.HealthService.get_readiness_status')
    def test_readiness_check_ready(self, mock_readiness_status, client):
        """Test readiness check when service is ready."""
        mock_readiness_status.return_value = {
            "ready": True,
            "timestamp": "2024-01-01T00:00:00",
            "services": {
                "chroma": True,
                "embeddings": True
            }
        }
        
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
    
    @patch('app.services.health_service.HealthService.get_readiness_status')
    def test_readiness_check_not_ready(self, mock_readiness_status, client):
        """Test readiness check when service is not ready."""
        mock_readiness_status.return_value = {
            "ready": False,
            "timestamp": "2024-01-01T00:00:00",
            "services": {
                "chroma": False,
                "embeddings": True
            }
        }
        
        response = client.get("/health/ready")
        
        assert response.status_code == 503
        data = response.json()
        assert data["ready"] is False
    
    @patch('app.services.health_service.HealthService.check_service_connectivity')
    def test_service_health_check(self, mock_service_check, client):
        """Test individual service health check."""
        mock_service_check.return_value = {
            "status": HealthStatus.HEALTHY,
            "response_time": 0.1,
            "url": "http://localhost:8001"
        }
        
        response = client.get("/health/service/chroma")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == HealthStatus.HEALTHY
        mock_service_check.assert_called_once_with("chroma")
    
    def test_middleware_request_id_header(self, client):
        """Test that request ID header is added by middleware."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers
    
    def test_middleware_security_headers(self, client):
        """Test that security headers are added by middleware."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Content-Security-Policy" in response.headers
    
    def test_cors_headers(self, client):
        """Test CORS headers."""
        # Preflight request
        response = client.options(
            "/api/v1/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
    
    def test_custom_request_id_preserved(self, client):
        """Test that custom request ID is preserved."""
        custom_id = "test-request-123"
        response = client.get("/", headers={"X-Request-ID": custom_id})
        
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == custom_id
    
    def test_404_error_handling(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert "request_id" in data
    
    def test_method_not_allowed_handling(self, client):
        """Test method not allowed handling."""
        response = client.post("/")  # Root only accepts GET
        
        assert response.status_code == 405
        data = response.json()
        assert "error_code" in data
        assert "message" in data
    
    def test_validation_error_handling(self, client):
        """Test validation error handling."""
        # This would trigger validation error if we had endpoints with validation
        # For now, test with invalid query parameters
        response = client.get("/health/detailed?force_refresh=invalid")
        
        # Should still work as force_refresh is parsed as bool
        assert response.status_code in [200, 503]  # Depends on service health
    
    def test_openapi_schema_in_debug_mode(self, client):
        """Test OpenAPI schema availability in debug mode."""
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.DEBUG = True
            
            response = client.get("/api/openapi.json")
            
            # Should be available in debug mode
            assert response.status_code == 200
            data = response.json()
            assert "openapi" in data
            assert "info" in data
    
    def test_rate_limiting_not_applied_in_development(self, client):
        """Test that rate limiting is not applied in development environment."""
        # Make multiple requests quickly
        for _ in range(10):
            response = client.get("/")
            assert response.status_code == 200
        
        # Should not be rate limited in development
        response = client.get("/")
        assert response.status_code == 200
    
    def test_health_endpoints_not_rate_limited(self, client):
        """Test that health endpoints are not rate limited."""
        # Even if rate limiting was enabled, health checks should work
        for _ in range(10):
            response = client.get("/health/")
            assert response.status_code == 200
    
    def test_error_response_format(self, client):
        """Test error response format consistency."""
        response = client.get("/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        
        # Check required fields
        required_fields = ["error_code", "message", "request_id"]
        for field in required_fields:
            assert field in data
        
        # Check field types
        assert isinstance(data["error_code"], str)
        assert isinstance(data["message"], str)
        assert isinstance(data["request_id"], str)
    
    def test_response_time_header(self, client):
        """Test that response time header is present and valid."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0
        assert process_time < 10  # Should be less than 10 seconds for simple request
    
    def test_content_type_headers(self, client):
        """Test content type headers."""
        response = client.get("/api/v1/")
        
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
    
    @patch('app.services.health_service.HealthService.get_health_status')
    def test_health_check_force_refresh(self, mock_health_status, client):
        """Test health check with force refresh parameter."""
        mock_health_status.return_value = {
            "status": HealthStatus.HEALTHY,
            "timestamp": "2024-01-01T00:00:00",
            "services": {}
        }
        
        response = client.get("/health/detailed?force_refresh=true")
        
        assert response.status_code == 200
        mock_health_status.assert_called_once_with(force_refresh=True)