"""Integration tests for document management API endpoints."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
import io

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestDocumentAPIIntegration:
    """Integration tests for document API endpoints."""
    
    def test_supported_formats_endpoint(self, client):
        """Test the supported formats endpoint."""
        response = client.get("/api/v1/documents/supported-formats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "supported_extensions" in data
        assert "max_file_size_mb" in data
        assert "supported_types" in data
        assert "processing_features" in data
        
        # Check that we have expected extensions
        extensions = data["supported_extensions"]
        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".txt" in extensions
        assert ".html" in extensions
        
        # Check file size limit is reasonable
        assert data["max_file_size_mb"] > 0
        
        # Check supported types
        types = data["supported_types"]
        assert "documents" in types
        assert "audio" in types
    
    def test_upload_endpoint_no_file(self, client):
        """Test upload endpoint without file."""
        response = client.post("/api/v1/documents/upload")
        
        # Should return validation error
        assert response.status_code == 422
    
    def test_upload_endpoint_unsupported_file(self, client):
        """Test upload with unsupported file type."""
        # Create a fake file with unsupported extension
        test_content = b"This is test content"
        test_file = io.BytesIO(test_content)
        
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.xyz", test_file, "application/octet-stream")}
        )
        
        # Should return validation error for unsupported type
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["message"]
    
    def test_database_stats_endpoint(self, client):
        """Test database stats endpoint."""
        response = client.get("/api/v1/database/stats")
        
        # Should work even with empty database
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_documents" in data
        assert "total_chunks" in data
        assert "total_size_mb" in data
        assert "by_type" in data
        assert "by_status" in data
        assert "by_language" in data
        
        # Values should be non-negative
        assert data["total_documents"] >= 0
        assert data["total_chunks"] >= 0
        assert data["total_size_mb"] >= 0
    
    def test_list_documents_endpoint(self, client):
        """Test list documents endpoint."""
        response = client.get("/api/v1/database/documents")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "documents" in data
        assert "total" in data
        
        # Should be lists/numbers even if empty
        assert isinstance(data["documents"], list)
        assert isinstance(data["total"], int)
        assert data["total"] >= 0
    
    def test_list_documents_with_pagination(self, client):
        """Test list documents with pagination parameters."""
        response = client.get(
            "/api/v1/database/documents",
            params={"skip": 0, "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data
    
    def test_get_nonexistent_document(self, client):
        """Test getting a document that doesn't exist."""
        response = client.get("/api/v1/database/documents/nonexistent-id")
        
        # Should return 404 for non-existent document
        assert response.status_code == 404
    
    def test_delete_nonexistent_document(self, client):
        """Test deleting a document that doesn't exist."""
        response = client.delete("/api/v1/database/documents/nonexistent-id")
        
        # Should return 404 for non-existent document
        assert response.status_code == 404
    
    def test_reindex_nonexistent_document(self, client):
        """Test reindexing a document that doesn't exist."""
        response = client.post("/api/v1/database/reindex/nonexistent-id")
        
        # Should return 404 for non-existent document
        assert response.status_code == 404
    
    def test_get_processing_status_nonexistent(self, client):
        """Test getting processing status for non-existent task."""
        response = client.get("/api/v1/documents/status/nonexistent-task")
        
        # Should return 404 for non-existent task
        assert response.status_code == 404
    
    def test_clear_database_without_confirmation(self, client):
        """Test clearing database without confirmation."""
        response = client.delete("/api/v1/database/clear")
        
        # Should require confirmation
        assert response.status_code == 400
        assert "confirmation" in response.json()["message"]
    
    def test_export_database_endpoint(self, client):
        """Test database export endpoint."""
        response = client.get("/api/v1/database/export")
        
        # Should work even with empty database
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]


class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_invalid_pagination_parameters(self, client):
        """Test invalid pagination parameters."""
        # Negative skip
        response = client.get(
            "/api/v1/database/documents",
            params={"skip": -1}
        )
        assert response.status_code == 422
        
        # Invalid limit
        response = client.get(
            "/api/v1/database/documents",
            params={"limit": 0}
        )
        assert response.status_code == 422
        
        # Limit too high
        response = client.get(
            "/api/v1/database/documents",
            params={"limit": 2000}
        )
        assert response.status_code == 422
    
    def test_invalid_processing_status_filter(self, client):
        """Test invalid processing status filter."""
        response = client.get(
            "/api/v1/database/documents",
            params={"status": "invalid_status"}
        )
        # Should handle invalid enum values gracefully
        assert response.status_code in [200, 422]  # Depends on validation implementation


if __name__ == "__main__":
    pytest.main([__file__])