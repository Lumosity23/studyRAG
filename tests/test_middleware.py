"""Tests for FastAPI middleware components."""

import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    ErrorHandlingMiddleware,
    RateLimitMiddleware
)
from app.core.exceptions import APIException


class TestRequestLoggingMiddleware:
    """Test request logging middleware."""
    
    def test_request_logging_adds_headers(self):
        """Test that request logging adds required headers."""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers
        assert float(response.headers["X-Process-Time"]) >= 0
    
    def test_request_logging_preserves_existing_request_id(self):
        """Test that existing request ID is preserved."""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        custom_request_id = "custom-123"
        response = client.get("/test", headers={"X-Request-ID": custom_request_id})
        
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == custom_request_id
    
    @patch('app.core.middleware.logger')
    def test_request_logging_logs_request_and_response(self, mock_logger):
        """Test that requests and responses are logged."""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Check that info was called for request start and completion
        assert mock_logger.info.call_count >= 2
        
        # Check log messages
        call_args = [call[0][0] for call in mock_logger.info.call_args_list]
        assert "Request started" in call_args
        assert "Request completed" in call_args
    
    @patch('app.core.middleware.logger')
    def test_request_logging_logs_errors(self, mock_logger):
        """Test that errors are logged."""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            raise ValueError("Test error")
        
        client = TestClient(app)
        
        with pytest.raises(ValueError):
            client.get("/test")
        
        # Check that error was logged
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "Request failed" in call_args


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""
    
    def test_security_headers_added(self):
        """Test that security headers are added to responses."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Check security headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
    
    def test_csp_header_content(self):
        """Test Content Security Policy header content."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "connect-src 'self' ws: wss:" in csp


class TestErrorHandlingMiddleware:
    """Test error handling middleware."""
    
    def test_api_exception_handling(self):
        """Test that APIException is properly handled."""
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            raise APIException(
                error_code="TEST_001",
                message="Test error",
                status_code=400,
                details={"test": "data"}
            )
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "TEST_001"
        assert data["message"] == "Test error"
        assert data["details"]["test"] == "data"
        assert "request_id" in data
        assert "timestamp" in data
    
    def test_generic_exception_handling(self):
        """Test that generic exceptions are converted to APIException."""
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            raise ValueError("Generic error")
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == "INTERNAL_001"
        assert data["message"] == "Internal server error"
        assert "Generic error" in data["details"]["original_error"]
    
    @patch('app.core.middleware.logger')
    def test_error_logging(self, mock_logger):
        """Test that errors are logged."""
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            raise ValueError("Test error")
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 500
        mock_logger.error.assert_called_once()


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""
    
    def test_rate_limit_allows_normal_requests(self):
        """Test that normal requests are allowed."""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, calls=10, period=60)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # Make several requests within limit
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200
    
    def test_rate_limit_blocks_excessive_requests(self):
        """Test that excessive requests are blocked."""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, calls=3, period=60)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # Make requests up to limit
        for _ in range(3):
            response = client.get("/test")
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429
        
        data = response.json()
        assert data["error_code"] == "RATE_LIMIT_001"
        assert "Retry-After" in response.headers
    
    def test_rate_limit_skips_health_checks(self):
        """Test that health check endpoints are not rate limited."""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, calls=1, period=60)
        
        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # Health checks should not be rate limited
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200
        
        # Regular endpoint should still be rate limited
        response = client.get("/test")
        assert response.status_code == 200
        
        response = client.get("/test")
        assert response.status_code == 429
    
    def test_rate_limit_cleanup(self):
        """Test that old entries are cleaned up."""
        app = FastAPI()
        middleware = RateLimitMiddleware(app, calls=5, period=1)  # 1 second period
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # Make requests
        for _ in range(3):
            response = client.get("/test")
            assert response.status_code == 200
        
        # Wait for period to expire
        time.sleep(1.1)
        
        # Should be able to make requests again
        response = client.get("/test")
        assert response.status_code == 200


class TestMiddlewareIntegration:
    """Test middleware integration."""
    
    def test_middleware_order(self):
        """Test that middleware is applied in correct order."""
        app = FastAPI()
        
        # Add middleware in reverse order (last added = first executed)
        app.add_middleware(ErrorHandlingMiddleware)
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Check that all middleware effects are present
        assert "X-Request-ID" in response.headers  # RequestLoggingMiddleware
        assert "X-Content-Type-Options" in response.headers  # SecurityHeadersMiddleware
    
    def test_middleware_with_exception(self):
        """Test middleware behavior when exception occurs."""
        app = FastAPI()
        
        app.add_middleware(ErrorHandlingMiddleware)
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            raise APIException("TEST_001", "Test error", 400)
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 400
        
        # Security headers should still be present
        assert "X-Content-Type-Options" in response.headers
        
        # Error should be properly formatted
        data = response.json()
        assert data["error_code"] == "TEST_001"