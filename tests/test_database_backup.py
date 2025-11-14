"""Tests for database backup and restore functionality."""

import pytest
import json
import base64
import gzip
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

from fastapi.testclient import TestClient
from app.main import app
from app.services.vector_database import VectorDatabase
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService


class TestDatabaseBackup:
    """Test database backup and export functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_vector_db(self):
        """Create mock vector database."""
        mock_db = Mock(spec=VectorDatabase)
        mock_db.export_database = AsyncMock()
        mock_db.get_database_stats = AsyncMock()
        mock_db.health_check = AsyncMock()
        mock_db.validate_schema = AsyncMock()
        return mock_db
    
    @pytest.fixture
    def sample_export_data(self):
        """Create sample export data."""
        return {
            "documents": [
                {
                    "id": "doc1",
                    "filename": "test.pdf",
                    "file_type": "pdf",
                    "file_size": 1024,
                    "processing_status": "completed",
                    "chunk_count": 2,
                    "chunks": [
                        {
                            "id": "chunk1",
                            "content": "Test content 1",
                            "metadata": {
                                "document_id": "doc1",
                                "chunk_index": 0,
                                "start_index": 0,
                                "end_index": 14,
                                "embedding_model": "test-model"
                            }
                        },
                        {
                            "id": "chunk2",
                            "content": "Test content 2",
                            "metadata": {
                                "document_id": "doc1",
                                "chunk_index": 1,
                                "start_index": 15,
                                "end_index": 29,
                                "embedding_model": "test-model"
                            }
                        }
                    ]
                }
            ]
        }
    
    @patch('app.api.endpoints.database.VectorDatabase')
    def test_export_database_json_success(self, mock_vector_db_class, client, sample_export_data):
        """Test successful JSON database export."""
        mock_vector_db = mock_vector_db_class.return_value
        mock_vector_db.export_database = AsyncMock(return_value=sample_export_data)
        mock_vector_db.get_database_stats = AsyncMock(return_value={
            "total_documents": 1,
            "total_chunks": 2,
            "total_size_mb": 1.0
        })
        
        response = client.get("/api/v1/database/export?format=json&compress=false")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
        
        # Verify export data structure
        export_data = response.json()
        assert "documents" in export_data
        assert "export_info" in export_data
        assert export_data["export_info"]["version"] == "2.0"
        assert export_data["export_info"]["total_documents"] == 1
        
        mock_vector_db.export_database.assert_called_once_with(include_files=False)
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_export_database_compressed(self, mock_get_db, client, mock_vector_db, sample_export_data):
        """Test compressed database export."""
        mock_get_db.return_value = mock_vector_db
        mock_vector_db.export_database.return_value = sample_export_data
        mock_vector_db.get_database_stats.return_value = {
            "total_documents": 1,
            "total_chunks": 2,
            "total_size_mb": 1.0
        }
        
        response = client.get("/api/v1/database/export?format=json&compress=true")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/gzip"
        assert ".gz" in response.headers["content-disposition"]
        
        # Verify compressed content can be decompressed
        compressed_data = response.content
        decompressed_data = gzip.decompress(compressed_data)
        export_data = json.loads(decompressed_data.decode('utf-8'))
        
        assert "documents" in export_data
        assert "export_info" in export_data
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_export_database_csv_format(self, mock_get_db, client, mock_vector_db, sample_export_data):
        """Test CSV format database export."""
        mock_get_db.return_value = mock_vector_db
        mock_vector_db.export_database.return_value = sample_export_data
        mock_vector_db.get_database_stats.return_value = {
            "total_documents": 1,
            "total_chunks": 2,
            "total_size_mb": 1.0
        }
        
        response = client.get("/api/v1/database/export?format=csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert ".zip" in response.headers["content-disposition"]
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_export_database_invalid_format(self, mock_get_db, client, mock_vector_db):
        """Test export with invalid format."""
        mock_get_db.return_value = mock_vector_db
        
        response = client.get("/api/v1/database/export?format=xml")
        
        assert response.status_code == 400
        assert "Unsupported export format" in response.json()["detail"]
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_export_database_with_files(self, mock_get_db, client, mock_vector_db, sample_export_data):
        """Test database export including files."""
        mock_get_db.return_value = mock_vector_db
        mock_vector_db.export_database.return_value = sample_export_data
        mock_vector_db.get_database_stats.return_value = {
            "total_documents": 1,
            "total_chunks": 2,
            "total_size_mb": 1.0
        }
        
        response = client.get("/api/v1/database/export?include_files=true")
        
        assert response.status_code == 200
        mock_vector_db.export_database.assert_called_once_with(include_files=True)
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_export_database_error(self, mock_get_db, client, mock_vector_db):
        """Test export database error handling."""
        mock_get_db.return_value = mock_vector_db
        mock_vector_db.export_database.side_effect = Exception("Export failed")
        
        response = client.get("/api/v1/database/export")
        
        assert response.status_code == 500
        assert "Failed to export database" in response.json()["detail"]


class TestDatabaseImport:
    """Test database import and restore functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_vector_db(self):
        """Create mock vector database."""
        mock_db = Mock(spec=VectorDatabase)
        mock_db.list_documents = AsyncMock()
        mock_db.get_document_info = AsyncMock()
        mock_db.delete_document = AsyncMock()
        mock_db.store_embeddings = AsyncMock()
        return mock_db
    
    @pytest.fixture
    def mock_processor(self):
        """Create mock document processor."""
        return Mock(spec=DocumentProcessor)
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        mock_service = Mock(spec=EmbeddingService)
        mock_service.generate_embedding = AsyncMock()
        return mock_service
    
    @pytest.fixture
    def sample_import_data(self):
        """Create sample import data."""
        return {
            "export_info": {
                "version": "2.0",
                "exported_at": "2024-01-01T00:00:00",
                "total_documents": 1,
                "checksum": "test_checksum"
            },
            "documents": [
                {
                    "id": "doc1",
                    "filename": "test.pdf",
                    "file_type": "pdf",
                    "file_size": 1024,
                    "processing_status": "completed",
                    "chunk_count": 1,
                    "chunks": [
                        {
                            "id": "chunk1",
                            "content": "Test content",
                            "metadata": {
                                "document_id": "doc1",
                                "chunk_index": 0,
                                "start_index": 0,
                                "end_index": 12,
                                "embedding_model": "test-model",
                                "embedding_vector": [0.1, 0.2, 0.3]
                            }
                        }
                    ]
                }
            ]
        }
    
    def encode_import_data(self, data: Dict[str, Any]) -> str:
        """Encode import data as base64."""
        json_data = json.dumps(data)
        return base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    
    @patch('app.api.endpoints.database.get_vector_database')
    @patch('app.api.endpoints.database.get_document_processor')
    @patch('app.api.endpoints.database.get_embedding_service')
    def test_import_database_validation_only(
        self, mock_get_embedding, mock_get_processor, mock_get_db, 
        client, mock_vector_db, mock_processor, mock_embedding_service, sample_import_data
    ):
        """Test import validation-only mode."""
        mock_get_db.return_value = mock_vector_db
        mock_get_processor.return_value = mock_processor
        mock_get_embedding.return_value = mock_embedding_service
        
        mock_vector_db.list_documents.return_value = {"documents": [], "total": 0}
        
        encoded_data = self.encode_import_data(sample_import_data)
        
        response = client.post(
            f"/api/v1/database/import?validate_only=true&import_file={encoded_data}"
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "validation_result" in result
        assert "import_preview" in result
        assert result["import_preview"]["total_documents"] == 1
    
    @patch('app.api.endpoints.database.get_vector_database')
    @patch('app.api.endpoints.database.get_document_processor')
    @patch('app.api.endpoints.database.get_embedding_service')
    def test_import_database_conflicts_without_overwrite(
        self, mock_get_embedding, mock_get_processor, mock_get_db,
        client, mock_vector_db, mock_processor, mock_embedding_service, sample_import_data
    ):
        """Test import with conflicts when overwrite is false."""
        mock_get_db.return_value = mock_vector_db
        mock_get_processor.return_value = mock_processor
        mock_get_embedding.return_value = mock_embedding_service
        
        # Mock existing document with same ID
        mock_vector_db.list_documents.return_value = {
            "documents": [{"id": "doc1", "filename": "existing.pdf"}],
            "total": 1
        }
        
        encoded_data = self.encode_import_data(sample_import_data)
        
        response = client.post(
            f"/api/v1/database/import?overwrite=false&import_file={encoded_data}"
        )
        
        assert response.status_code == 409
        result = response.json()
        assert "conflicts" in result["detail"]
        assert "doc1" in result["detail"]["conflicts"]
    
    @patch('app.api.endpoints.database.get_vector_database')
    @patch('app.api.endpoints.database.get_document_processor')
    @patch('app.api.endpoints.database.get_embedding_service')
    def test_import_database_success(
        self, mock_get_embedding, mock_get_processor, mock_get_db,
        client, mock_vector_db, mock_processor, mock_embedding_service, sample_import_data
    ):
        """Test successful database import."""
        mock_get_db.return_value = mock_vector_db
        mock_get_processor.return_value = mock_processor
        mock_get_embedding.return_value = mock_embedding_service
        
        mock_vector_db.list_documents.return_value = {"documents": [], "total": 0}
        
        encoded_data = self.encode_import_data(sample_import_data)
        
        response = client.post(
            f"/api/v1/database/import?import_file={encoded_data}"
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "import_task_id" in result
        assert result["status"] == "processing"
        assert "status_endpoint" in result
    
    @patch('app.api.endpoints.database.get_vector_database')
    @patch('app.api.endpoints.database.get_document_processor')
    @patch('app.api.endpoints.database.get_embedding_service')
    def test_import_database_invalid_data(
        self, mock_get_embedding, mock_get_processor, mock_get_db,
        client, mock_vector_db, mock_processor, mock_embedding_service
    ):
        """Test import with invalid data."""
        mock_get_db.return_value = mock_vector_db
        mock_get_processor.return_value = mock_processor
        mock_get_embedding.return_value = mock_embedding_service
        
        # Invalid base64 data
        invalid_data = "invalid_base64_data"
        
        response = client.post(
            f"/api/v1/database/import?import_file={invalid_data}"
        )
        
        assert response.status_code == 500
        assert "Failed to start database import" in response.json()["detail"]
    
    def test_get_import_status_not_found(self, client):
        """Test getting import status for non-existent task."""
        response = client.get("/api/v1/database/import/nonexistent/status")
        
        assert response.status_code == 404
        assert "No import status found" in response.json()["detail"]
    
    @patch('app.api.endpoints.database.import_status', {"task123": {"status": "processing", "progress": 0.5}})
    def test_get_import_status_success(self, client):
        """Test getting import status for existing task."""
        response = client.get("/api/v1/database/import/task123/status")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "processing"
        assert result["progress"] == 0.5


class TestDatabaseHealth:
    """Test database health and monitoring functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_vector_db(self):
        """Create mock vector database."""
        mock_db = Mock(spec=VectorDatabase)
        mock_db.health_check = AsyncMock()
        mock_db.get_database_stats = AsyncMock()
        mock_db.validate_schema = AsyncMock()
        return mock_db
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_database_health_success(self, mock_get_db, client, mock_vector_db):
        """Test successful database health check."""
        mock_get_db.return_value = mock_vector_db
        
        mock_vector_db.health_check.return_value = {
            "status": "healthy",
            "message": "ChromaDB is operational"
        }
        
        mock_vector_db.get_database_stats.return_value = {
            "total_documents": 10,
            "total_chunks": 100,
            "total_size_mb": 50.0
        }
        
        mock_vector_db.validate_schema.return_value = {
            "schema_valid": True,
            "collection_exists": True
        }
        
        response = client.get("/api/v1/database/health")
        
        assert response.status_code == 200
        result = response.json()
        assert result["overall_status"] == "healthy"
        assert "components" in result
        assert "statistics" in result
        assert "performance_metrics" in result
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_database_health_unhealthy(self, mock_get_db, client, mock_vector_db):
        """Test database health check when unhealthy."""
        mock_get_db.return_value = mock_vector_db
        
        mock_vector_db.health_check.return_value = {
            "status": "unhealthy",
            "message": "Connection failed"
        }
        
        mock_vector_db.get_database_stats.return_value = {
            "total_documents": 0,
            "total_chunks": 0,
            "total_size_mb": 0.0
        }
        
        mock_vector_db.validate_schema.return_value = {
            "schema_valid": False,
            "collection_exists": False
        }
        
        response = client.get("/api/v1/database/health")
        
        assert response.status_code == 200
        result = response.json()
        assert result["overall_status"] == "unhealthy"
        assert len(result["issues"]) > 0
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_database_health_error(self, mock_get_db, client, mock_vector_db):
        """Test database health check error handling."""
        mock_get_db.return_value = mock_vector_db
        mock_vector_db.health_check.side_effect = Exception("Health check failed")
        
        response = client.get("/api/v1/database/health")
        
        assert response.status_code == 200
        result = response.json()
        assert result["overall_status"] == "unhealthy"
        assert "Health check failed" in result["issues"][0]


class TestDatabaseValidation:
    """Test database integrity validation functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_vector_db(self):
        """Create mock vector database."""
        mock_db = Mock(spec=VectorDatabase)
        mock_db.validate_schema = AsyncMock()
        mock_db.export_database = AsyncMock()
        return mock_db
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_validate_database_integrity_success(self, mock_get_db, client, mock_vector_db):
        """Test successful database integrity validation."""
        mock_get_db.return_value = mock_vector_db
        
        mock_vector_db.validate_schema.return_value = {
            "schema_valid": True,
            "collection_exists": True
        }
        
        mock_vector_db.export_database.return_value = {
            "documents": [
                {
                    "id": "doc1",
                    "filename": "test.pdf",
                    "chunks": [
                        {
                            "id": "chunk1",
                            "content": "Test content",
                            "metadata": {
                                "document_id": "doc1",
                                "embedding_vector": [0.1, 0.2, 0.3]
                            }
                        }
                    ]
                }
            ]
        }
        
        response = client.post("/api/v1/database/validate")
        
        assert response.status_code == 200
        result = response.json()
        assert result["overall_status"] == "valid"
        assert "statistics" in result
        assert "validation_timestamp" in result
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_validate_database_integrity_with_issues(self, mock_get_db, client, mock_vector_db):
        """Test database validation with integrity issues."""
        mock_get_db.return_value = mock_vector_db
        
        mock_vector_db.validate_schema.return_value = {
            "schema_valid": False,
            "collection_exists": True
        }
        
        mock_vector_db.export_database.return_value = {
            "documents": [
                {
                    "id": "doc1",
                    "filename": "test.pdf",
                    "chunks": [
                        {
                            "id": "chunk1",
                            "content": "Test content",
                            "metadata": {
                                "document_id": "wrong_doc_id",  # Orphaned chunk
                                "embedding_vector": None  # Missing embedding
                            }
                        }
                    ]
                }
            ]
        }
        
        response = client.post("/api/v1/database/validate")
        
        assert response.status_code == 200
        result = response.json()
        assert result["overall_status"] in ["invalid", "degraded"]
        assert len(result["issues_found"]) > 0
    
    @patch('app.api.endpoints.database.get_vector_database')
    def test_validate_database_integrity_error(self, mock_get_db, client, mock_vector_db):
        """Test database validation error handling."""
        mock_get_db.return_value = mock_vector_db
        mock_vector_db.validate_schema.side_effect = Exception("Validation failed")
        
        response = client.post("/api/v1/database/validate")
        
        assert response.status_code == 500
        assert "Failed to validate database integrity" in response.json()["detail"]


class TestHelperFunctions:
    """Test helper functions for backup and import operations."""
    
    def test_calculate_export_checksum(self):
        """Test export checksum calculation."""
        from app.api.endpoints.database import _calculate_export_checksum
        
        test_data = {"test": "data", "number": 123}
        checksum1 = _calculate_export_checksum(test_data)
        checksum2 = _calculate_export_checksum(test_data)
        
        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA256 hex length
        
        # Different data should produce different checksum
        different_data = {"test": "different", "number": 456}
        checksum3 = _calculate_export_checksum(different_data)
        assert checksum1 != checksum3
    
    @pytest.mark.asyncio
    async def test_validate_export_data_valid(self):
        """Test export data validation with valid data."""
        from app.api.endpoints.database import _validate_export_data
        
        valid_data = {
            "documents": [
                {
                    "id": "doc1",
                    "filename": "test.pdf",
                    "chunks": [
                        {
                            "id": "chunk1",
                            "content": "Test content"
                        }
                    ]
                }
            ]
        }
        
        result = await _validate_export_data(valid_data)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_export_data_invalid(self):
        """Test export data validation with invalid data."""
        from app.api.endpoints.database import _validate_export_data
        
        invalid_data = {
            "documents": [
                {
                    # Missing id
                    "filename": "test.pdf",
                    "chunks": [
                        {
                            # Missing id
                            "content": ""  # Empty content
                        }
                    ]
                }
            ]
        }
        
        result = await _validate_export_data(invalid_data)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert len(result["warnings"]) > 0
    
    @pytest.mark.asyncio
    async def test_parse_import_file_json(self):
        """Test parsing JSON import file."""
        from app.api.endpoints.database import _parse_import_file
        
        test_data = {"test": "data"}
        json_data = json.dumps(test_data)
        encoded_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
        
        result = await _parse_import_file(encoded_data)
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_parse_import_file_gzipped(self):
        """Test parsing gzipped import file."""
        from app.api.endpoints.database import _parse_import_file
        
        test_data = {"test": "data"}
        json_data = json.dumps(test_data)
        gzipped_data = gzip.compress(json_data.encode('utf-8'))
        encoded_data = base64.b64encode(gzipped_data).decode('utf-8')
        
        result = await _parse_import_file(encoded_data)
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_parse_import_file_invalid(self):
        """Test parsing invalid import file."""
        from app.api.endpoints.database import _parse_import_file
        
        with pytest.raises(ValueError, match="Invalid base64 encoding"):
            await _parse_import_file("invalid_base64!")
        
        # Valid base64 but invalid JSON
        invalid_json = base64.b64encode(b"invalid json").decode('utf-8')
        with pytest.raises(ValueError, match="Invalid JSON format"):
            await _parse_import_file(invalid_json)


if __name__ == "__main__":
    pytest.main([__file__])