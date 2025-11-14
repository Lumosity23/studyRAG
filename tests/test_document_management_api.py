"""Tests for document management API endpoints."""

import os
import json
import tempfile
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import UploadFile
import io

from app.main import create_app
from app.models.document import Document, ProcessingStatus, DocumentType
from app.services.document_processor import DocumentProcessor
from app.services.vector_database import VectorDatabase
from app.services.embedding_service import EmbeddingService


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_document_processor():
    """Mock document processor."""
    processor = Mock(spec=DocumentProcessor)
    processor.get_supported_extensions.return_value = ['.pdf', '.docx', '.txt', '.html']
    return processor


@pytest.fixture
def mock_vector_database():
    """Mock vector database."""
    db = Mock(spec=VectorDatabase)
    return db


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = Mock(spec=EmbeddingService)
    service.get_available_models.return_value = [
        {"key": "model1", "name": "Test Model 1"},
        {"key": "model2", "name": "Test Model 2"}
    ]
    return service


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return Document(
        id="test-doc-1",
        filename="test.pdf",
        file_type=DocumentType.PDF,
        file_size=1024000,
        processing_status=ProcessingStatus.COMPLETED,
        chunk_count=5,
        embedding_model="test-model"
    )


class TestDocumentUpload:
    """Test document upload endpoint."""
    
    def test_upload_document_success(self, client, mock_document_processor, mock_vector_database, mock_embedding_service):
        """Test successful document upload."""
        # Create test file
        test_content = b"This is a test PDF content"
        test_file = io.BytesIO(test_content)
        
        with patch('app.api.endpoints.documents.get_document_processor', return_value=mock_document_processor), \
             patch('app.api.endpoints.documents.get_vector_database', return_value=mock_vector_database), \
             patch('app.api.endpoints.documents.get_embedding_service', return_value=mock_embedding_service), \
             patch('os.makedirs'), \
             patch('builtins.open', create=True) as mock_open:
            
            mock_open.return_value.__enter__.return_value.write = Mock()
            
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", test_file, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["filename"] == "test.pdf"
        assert data["processing_status"] == "pending"
        assert "message" in data
    
    def test_upload_document_no_file(self, client):
        """Test upload without file."""
        response = client.post("/api/v1/documents/upload")
        assert response.status_code == 422  # Validation error
    
    def test_upload_document_unsupported_type(self, client, mock_document_processor):
        """Test upload with unsupported file type."""
        mock_document_processor.get_supported_extensions.return_value = ['.pdf', '.docx']
        
        test_content = b"This is a test file"
        test_file = io.BytesIO(test_content)
        
        with patch('app.api.endpoints.documents.get_document_processor', return_value=mock_document_processor):
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.xyz", test_file, "application/octet-stream")}
            )
        
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]
    
    def test_upload_document_with_metadata(self, client, mock_document_processor, mock_vector_database, mock_embedding_service):
        """Test upload with metadata."""
        test_content = b"This is a test PDF content"
        test_file = io.BytesIO(test_content)
        metadata = {"author": "Test Author", "category": "Research"}
        
        with patch('app.api.endpoints.documents.get_document_processor', return_value=mock_document_processor), \
             patch('app.api.endpoints.documents.get_vector_database', return_value=mock_vector_database), \
             patch('app.api.endpoints.documents.get_embedding_service', return_value=mock_embedding_service), \
             patch('os.makedirs'), \
             patch('builtins.open', create=True) as mock_open:
            
            mock_open.return_value.__enter__.return_value.write = Mock()
            
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", test_file, "application/pdf")},
                data={"metadata": json.dumps(metadata)}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"


class TestProcessingStatus:
    """Test processing status endpoints."""
    
    def test_get_processing_status_success(self, client):
        """Test getting processing status."""
        # Mock processing status
        task_id = "test-task-123"
        
        with patch('app.api.endpoints.documents.processing_status', {
            task_id: {
                "document_id": task_id,
                "status": "processing",
                "progress": 0.5,
                "message": "Processing document..."
            }
        }):
            response = client.get(f"/api/v1/documents/status/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == task_id
        assert data["status"] == "processing"
        assert data["progress"] == 0.5
    
    def test_get_processing_status_not_found(self, client):
        """Test getting status for non-existent task."""
        response = client.get("/api/v1/documents/status/non-existent-task")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_clear_processing_status_success(self, client):
        """Test clearing completed processing status."""
        task_id = "test-task-123"
        
        with patch('app.api.endpoints.documents.processing_status', {
            task_id: {
                "document_id": task_id,
                "status": "completed",
                "progress": 1.0,
                "message": "Processing completed"
            }
        }) as mock_status:
            response = client.delete(f"/api/v1/documents/status/{task_id}")
        
        assert response.status_code == 200
        assert task_id not in mock_status
    
    def test_clear_processing_status_active_task(self, client):
        """Test clearing status for active task."""
        task_id = "test-task-123"
        
        with patch('app.api.endpoints.documents.processing_status', {
            task_id: {
                "document_id": task_id,
                "status": "processing",
                "progress": 0.5,
                "message": "Processing..."
            }
        }):
            response = client.delete(f"/api/v1/documents/status/{task_id}")
        
        assert response.status_code == 400
        assert "Cannot clear status for active" in response.json()["detail"]


class TestSupportedFormats:
    """Test supported formats endpoint."""
    
    def test_get_supported_formats(self, client, mock_document_processor):
        """Test getting supported formats."""
        with patch('app.api.endpoints.documents.get_document_processor', return_value=mock_document_processor):
            response = client.get("/api/v1/documents/supported-formats")
        
        assert response.status_code == 200
        data = response.json()
        assert "supported_extensions" in data
        assert "max_file_size_mb" in data
        assert "supported_types" in data
        assert "processing_features" in data


class TestDatabaseManagement:
    """Test database management endpoints."""
    
    def test_list_documents_success(self, client, mock_vector_database, sample_document):
        """Test listing documents."""
        # Use AsyncMock for async methods
        async def mock_list_documents(skip=0, limit=50, filters=None):
            return {
                "documents": [sample_document.model_dump()],
                "total": 1
            }
        
        mock_vector_database.list_documents = mock_list_documents
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database):
            response = client.get("/api/v1/database/documents")
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["documents"]) == 1
    
    def test_list_documents_with_filters(self, client, mock_vector_database):
        """Test listing documents with filters."""
        mock_vector_database.list_documents = AsyncMock(return_value={
            "documents": [],
            "total": 0
        })
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database):
            response = client.get(
                "/api/v1/database/documents",
                params={
                    "skip": 10,
                    "limit": 20,
                    "status": "completed",
                    "file_type": "pdf",
                    "search": "test"
                }
            )
        
        assert response.status_code == 200
        mock_vector_database.list_documents.assert_called_once()
        call_args = mock_vector_database.list_documents.call_args
        assert call_args[1]["skip"] == 10
        assert call_args[1]["limit"] == 20
    
    def test_get_document_success(self, client, mock_vector_database, sample_document):
        """Test getting specific document."""
        mock_vector_database.get_document_info = AsyncMock(return_value=sample_document.model_dump())
        mock_vector_database.get_document_chunk_stats = AsyncMock(return_value={
            "total_chunks": 5,
            "total_content_length": 1000
        })
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database):
            response = client.get(f"/api/v1/database/documents/{sample_document.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_document.id
        assert data["filename"] == sample_document.filename
        assert "chunk_statistics" in data
    
    def test_get_document_not_found(self, client, mock_vector_database):
        """Test getting non-existent document."""
        mock_vector_database.get_document_info = AsyncMock(return_value=None)
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database):
            response = client.get("/api/v1/database/documents/non-existent")
        
        assert response.status_code == 404
    
    def test_delete_document_success(self, client, mock_vector_database, sample_document):
        """Test deleting document."""
        mock_vector_database.get_document_info = AsyncMock(return_value=sample_document.model_dump())
        mock_vector_database.get_document_chunk_stats = AsyncMock(return_value={"total_chunks": 5})
        mock_vector_database.delete_document = AsyncMock(return_value=True)
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database), \
             patch('os.path.exists', return_value=False):
            response = client.delete(f"/api/v1/database/documents/{sample_document.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document.id
        assert "chunks_deleted" in data
    
    def test_delete_document_not_found(self, client, mock_vector_database):
        """Test deleting non-existent document."""
        mock_vector_database.get_document_info = AsyncMock(return_value=None)
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database):
            response = client.delete("/api/v1/database/documents/non-existent")
        
        assert response.status_code == 404
    
    def test_reindex_document_success(self, client, mock_vector_database, mock_document_processor, mock_embedding_service, sample_document):
        """Test reindexing document."""
        mock_vector_database.get_document_info = AsyncMock(return_value=sample_document.model_dump())
        mock_embedding_service.get_available_models = AsyncMock(return_value=[
            {"key": "model1", "name": "Test Model 1"},
            {"key": "model2", "name": "Test Model 2"}
        ])
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database), \
             patch('app.api.endpoints.database.get_document_processor', return_value=mock_document_processor), \
             patch('app.api.endpoints.database.get_embedding_service', return_value=mock_embedding_service):
            response = client.post(
                f"/api/v1/database/reindex/{sample_document.id}",
                params={"new_model": "model1"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document.id
        assert data["new_model"] == "model1"
        assert data["status"] == "processing"
    
    def test_reindex_document_not_found(self, client, mock_vector_database):
        """Test reindexing non-existent document."""
        mock_vector_database.get_document_info = AsyncMock(return_value=None)
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database):
            response = client.post("/api/v1/database/reindex/non-existent")
        
        assert response.status_code == 404
    
    def test_reindex_document_invalid_model(self, client, mock_vector_database, mock_embedding_service, sample_document):
        """Test reindexing with invalid model."""
        mock_vector_database.get_document_info = AsyncMock(return_value=sample_document.model_dump())
        mock_embedding_service.get_available_models = AsyncMock(return_value=[
            {"key": "model1", "name": "Test Model 1"},
            {"key": "model2", "name": "Test Model 2"}
        ])
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database), \
             patch('app.api.endpoints.database.get_embedding_service', return_value=mock_embedding_service):
            response = client.post(
                f"/api/v1/database/reindex/{sample_document.id}",
                params={"new_model": "invalid-model"}
            )
        
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]
    
    def test_get_reindexing_status_success(self, client):
        """Test getting reindexing status."""
        document_id = "test-doc-1"
        
        with patch('app.api.endpoints.database.reindexing_status', {
            document_id: {
                "status": "processing",
                "progress": 0.7,
                "message": "Reindexing in progress..."
            }
        }):
            response = client.get(f"/api/v1/database/reindex/{document_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"] == 0.7
    
    def test_get_reindexing_status_not_found(self, client):
        """Test getting reindexing status for non-existent task."""
        response = client.get("/api/v1/database/reindex/non-existent/status")
        assert response.status_code == 404
    
    def test_get_database_stats(self, client, mock_vector_database):
        """Test getting database statistics."""
        mock_stats = {
            "total_documents": 10,
            "total_chunks": 50,
            "total_size_mb": 25.5,
            "by_type": {"pdf": 5, "docx": 3, "txt": 2},
            "by_status": {"completed": 8, "processing": 2},
            "by_language": {"en": 7, "fr": 2, "unknown": 1}
        }
        mock_vector_database.get_database_stats = AsyncMock(return_value=mock_stats)
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database):
            response = client.get("/api/v1/database/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 10
        assert data["total_chunks"] == 50
        assert data["total_size_mb"] == 25.5
    
    def test_export_database(self, client, mock_vector_database):
        """Test database export."""
        mock_export_data = {
            "documents": [{"id": "doc1", "filename": "test.pdf"}],
            "chunks": [],
            "metadata": {"exported_at": "2024-01-01T00:00:00"}
        }
        mock_vector_database.export_database = AsyncMock(return_value=mock_export_data)
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database):
            response = client.get("/api/v1/database/export")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
    
    def test_clear_database_without_confirmation(self, client):
        """Test clearing database without confirmation."""
        response = client.delete("/api/v1/database/clear")
        assert response.status_code == 400
        assert "confirmation" in response.json()["detail"]
    
    def test_clear_database_with_confirmation(self, client, mock_vector_database):
        """Test clearing database with confirmation."""
        mock_vector_database.get_database_stats = AsyncMock(return_value={
            "total_documents": 5,
            "total_chunks": 25
        })
        mock_vector_database.clear_database = AsyncMock(return_value=True)
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database):
            response = client.delete("/api/v1/database/clear", params={"confirm": True})
        
        assert response.status_code == 200
        data = response.json()
        assert "Database cleared successfully" in data["message"]
        assert data["documents_deleted"] == 5
        assert data["chunks_deleted"] == 25


class TestErrorHandling:
    """Test error handling in document management endpoints."""
    
    def test_upload_document_processing_error(self, client, mock_document_processor):
        """Test handling of document processing errors."""
        test_content = b"This is a test PDF content"
        test_file = io.BytesIO(test_content)
        
        with patch('app.api.endpoints.documents.get_document_processor', return_value=mock_document_processor), \
             patch('os.makedirs'), \
             patch('builtins.open', side_effect=IOError("Disk full")):
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", test_file, "application/pdf")}
            )
        
        assert response.status_code == 500
        assert "upload failed" in response.json()["detail"].lower()
    
    def test_database_operation_error(self, client, mock_vector_database):
        """Test handling of database operation errors."""
        mock_vector_database.list_documents = AsyncMock(side_effect=Exception("Database connection failed"))
        
        with patch('app.api.endpoints.database.get_vector_database', return_value=mock_vector_database):
            response = client.get("/api/v1/database/documents")
        
        assert response.status_code == 500
        assert "Failed to retrieve documents" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__])