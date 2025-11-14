"""Integration tests for database management and backup functionality."""

import pytest
import json
import base64
import asyncio
import tempfile
import os
from datetime import datetime
from typing import Dict, Any

from fastapi.testclient import TestClient
from app.main import app
from app.services.vector_database import VectorDatabase
from app.models.document import Document, ProcessingStatus, DocumentType
from app.models.chunk import Chunk


class TestDatabaseManagementIntegration:
    """Integration tests for database management operations."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    async def vector_db(self):
        """Create and initialize vector database for testing."""
        db = VectorDatabase()
        await db.connect()
        
        # Clear any existing data
        await db.reset_collection()
        
        yield db
        
        # Cleanup
        await db.reset_collection()
        await db.disconnect()
    
    @pytest.fixture
    async def sample_documents(self, vector_db):
        """Create sample documents and chunks in the database."""
        # Create sample chunks
        chunks = [
            Chunk(
                id="chunk1",
                document_id="doc1",
                content="This is the first chunk of content from document 1.",
                start_index=0,
                end_index=50,
                chunk_index=0,
                section_title="Introduction",
                page_number=1,
                language="en",
                embedding_model="test-model",
                token_count=12
            ),
            Chunk(
                id="chunk2",
                document_id="doc1",
                content="This is the second chunk of content from document 1.",
                start_index=51,
                end_index=102,
                chunk_index=1,
                section_title="Main Content",
                page_number=1,
                language="en",
                embedding_model="test-model",
                token_count=12
            ),
            Chunk(
                id="chunk3",
                document_id="doc2",
                content="This is content from document 2.",
                start_index=0,
                end_index=32,
                chunk_index=0,
                section_title="Overview",
                page_number=1,
                language="en",
                embedding_model="test-model",
                token_count=8
            )
        ]
        
        # Generate dummy embeddings
        embeddings = [
            [0.1, 0.2, 0.3, 0.4, 0.5] * 64,  # 320 dimensions
            [0.2, 0.3, 0.4, 0.5, 0.6] * 64,
            [0.3, 0.4, 0.5, 0.6, 0.7] * 64
        ]
        
        # Store in vector database
        await vector_db.store_embeddings(chunks, embeddings)
        
        return {
            "doc1": {
                "id": "doc1",
                "filename": "test_document_1.pdf",
                "file_type": "pdf",
                "file_size": 2048,
                "processing_status": "completed",
                "chunk_count": 2
            },
            "doc2": {
                "id": "doc2",
                "filename": "test_document_2.txt",
                "file_type": "txt",
                "file_size": 1024,
                "processing_status": "completed",
                "chunk_count": 1
            }
        }
    
    @pytest.mark.asyncio
    async def test_export_import_roundtrip(self, client, vector_db, sample_documents):
        """Test complete export-import roundtrip."""
        # First, export the database
        export_response = client.get("/api/v1/database/export?format=json&compress=false")
        
        assert export_response.status_code == 200
        export_data = export_response.json()
        
        # Verify export structure
        assert "documents" in export_data
        assert "export_info" in export_data
        assert len(export_data["documents"]) == 2
        
        # Clear the database
        clear_response = client.delete("/api/v1/database/clear?confirm=true")
        assert clear_response.status_code == 200
        
        # Verify database is empty
        stats_response = client.get("/api/v1/database/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["total_documents"] == 0
        assert stats["total_chunks"] == 0
        
        # Import the data back
        encoded_data = base64.b64encode(
            json.dumps(export_data).encode('utf-8')
        ).decode('utf-8')
        
        import_response = client.post(
            f"/api/v1/database/import?import_file={encoded_data}"
        )
        
        assert import_response.status_code == 200
        import_result = import_response.json()
        assert "import_task_id" in import_result
        
        # Wait for import to complete (in a real scenario, you'd poll the status)
        import asyncio
        await asyncio.sleep(2)  # Give time for background task
        
        # Check import status
        task_id = import_result["import_task_id"]
        status_response = client.get(f"/api/v1/database/import/{task_id}/status")
        
        if status_response.status_code == 200:
            status = status_response.json()
            # Import might still be processing, that's okay for this test
            assert status["status"] in ["processing", "completed", "starting"]
    
    @pytest.mark.asyncio
    async def test_database_health_monitoring(self, client, vector_db, sample_documents):
        """Test database health monitoring functionality."""
        health_response = client.get("/api/v1/database/health")
        
        assert health_response.status_code == 200
        health_data = health_response.json()
        
        # Verify health structure
        assert "overall_status" in health_data
        assert "components" in health_data
        assert "statistics" in health_data
        assert "performance_metrics" in health_data
        
        # Should be healthy with sample data
        assert health_data["overall_status"] in ["healthy", "degraded"]
        
        # Verify statistics
        stats = health_data["statistics"]
        assert stats["total_documents"] >= 0
        assert stats["total_chunks"] >= 0
        
        # Verify performance metrics
        metrics = health_data["performance_metrics"]
        assert "documents_per_mb" in metrics
        assert "chunks_per_document" in metrics
        assert "avg_document_size_mb" in metrics
    
    @pytest.mark.asyncio
    async def test_database_integrity_validation(self, client, vector_db, sample_documents):
        """Test database integrity validation."""
        validation_response = client.post("/api/v1/database/validate")
        
        assert validation_response.status_code == 200
        validation_data = validation_response.json()
        
        # Verify validation structure
        assert "overall_status" in validation_data
        assert "validation_timestamp" in validation_data
        assert "statistics" in validation_data
        
        # With proper sample data, should be valid
        assert validation_data["overall_status"] in ["valid", "degraded"]
        
        # Verify statistics
        stats = validation_data["statistics"]
        assert "total_documents" in stats
        assert "total_chunks" in stats
        assert "orphaned_chunks" in stats
        assert "chunks_without_embeddings" in stats
    
    @pytest.mark.asyncio
    async def test_export_with_different_formats(self, client, vector_db, sample_documents):
        """Test export with different formats and options."""
        # Test JSON export
        json_response = client.get("/api/v1/database/export?format=json&compress=false")
        assert json_response.status_code == 200
        assert json_response.headers["content-type"] == "application/json"
        
        # Test compressed JSON export
        compressed_response = client.get("/api/v1/database/export?format=json&compress=true")
        assert compressed_response.status_code == 200
        assert compressed_response.headers["content-type"] == "application/gzip"
        
        # Test CSV export
        csv_response = client.get("/api/v1/database/export?format=csv")
        assert csv_response.status_code == 200
        assert csv_response.headers["content-type"] == "application/zip"
    
    @pytest.mark.asyncio
    async def test_import_validation_only(self, client, vector_db, sample_documents):
        """Test import validation-only mode."""
        # First export data
        export_response = client.get("/api/v1/database/export?format=json&compress=false")
        assert export_response.status_code == 200
        export_data = export_response.json()
        
        # Encode for import
        encoded_data = base64.b64encode(
            json.dumps(export_data).encode('utf-8')
        ).decode('utf-8')
        
        # Test validation-only import
        validation_response = client.post(
            f"/api/v1/database/import?validate_only=true&import_file={encoded_data}"
        )
        
        assert validation_response.status_code == 200
        validation_result = validation_response.json()
        
        assert "validation_result" in validation_result
        assert "import_preview" in validation_result
        
        preview = validation_result["import_preview"]
        assert "total_documents" in preview
        assert "total_chunks" in preview
        assert "conflicts" in preview
        assert "estimated_time_minutes" in preview
    
    @pytest.mark.asyncio
    async def test_import_conflict_detection(self, client, vector_db, sample_documents):
        """Test import conflict detection."""
        # Export current data
        export_response = client.get("/api/v1/database/export?format=json&compress=false")
        assert export_response.status_code == 200
        export_data = export_response.json()
        
        # Try to import the same data (should detect conflicts)
        encoded_data = base64.b64encode(
            json.dumps(export_data).encode('utf-8')
        ).decode('utf-8')
        
        # Import without overwrite should fail due to conflicts
        conflict_response = client.post(
            f"/api/v1/database/import?overwrite=false&import_file={encoded_data}"
        )
        
        assert conflict_response.status_code == 409
        conflict_result = conflict_response.json()
        assert "conflicts" in conflict_result["detail"]
    
    @pytest.mark.asyncio
    async def test_database_statistics_accuracy(self, client, vector_db, sample_documents):
        """Test accuracy of database statistics."""
        stats_response = client.get("/api/v1/database/stats")
        
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        # Verify basic counts
        assert stats["total_documents"] == 2
        assert stats["total_chunks"] == 3
        assert stats["total_size_mb"] >= 0
        
        # Verify breakdown statistics
        assert "by_type" in stats
        assert "by_status" in stats
        assert "by_language" in stats
        
        # Check specific breakdowns
        assert stats["by_type"].get("pdf", 0) >= 1
        assert stats["by_type"].get("txt", 0) >= 1
        assert stats["by_status"].get("completed", 0) >= 2
        assert stats["by_language"].get("en", 0) >= 3
    
    @pytest.mark.asyncio
    async def test_document_listing_and_management(self, client, vector_db, sample_documents):
        """Test document listing and management operations."""
        # Test document listing
        list_response = client.get("/api/v1/database/documents")
        
        assert list_response.status_code == 200
        list_result = list_response.json()
        
        assert "documents" in list_result
        assert "total" in list_result
        assert list_result["total"] == 2
        assert len(list_result["documents"]) == 2
        
        # Test document filtering
        pdf_response = client.get("/api/v1/database/documents?file_type=pdf")
        assert pdf_response.status_code == 200
        pdf_result = pdf_response.json()
        
        # Should have at least one PDF document
        pdf_docs = [doc for doc in pdf_result["documents"] if doc["file_type"] == "pdf"]
        assert len(pdf_docs) >= 1
        
        # Test document search
        search_response = client.get("/api/v1/database/documents?search=test")
        assert search_response.status_code == 200
        search_result = search_response.json()
        
        # Should find documents with "test" in filename
        assert search_result["total"] >= 1
    
    @pytest.mark.asyncio
    async def test_document_deletion_cascade(self, client, vector_db, sample_documents):
        """Test document deletion with cascade to chunks."""
        # Get initial stats
        initial_stats = client.get("/api/v1/database/stats").json()
        initial_chunks = initial_stats["total_chunks"]
        
        # Delete one document
        delete_response = client.delete("/api/v1/database/documents/doc1")
        
        assert delete_response.status_code == 200
        delete_result = delete_response.json()
        
        assert "chunks_deleted" in delete_result
        assert delete_result["chunks_deleted"] == 2  # doc1 had 2 chunks
        
        # Verify stats updated
        updated_stats = client.get("/api/v1/database/stats").json()
        assert updated_stats["total_documents"] == initial_stats["total_documents"] - 1
        assert updated_stats["total_chunks"] == initial_chunks - 2
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, client, vector_db):
        """Test error handling and recovery scenarios."""
        # Test export with empty database
        empty_export = client.get("/api/v1/database/export")
        assert empty_export.status_code == 200
        
        empty_data = empty_export.json()
        assert empty_data["export_info"]["total_documents"] == 0
        
        # Test import with malformed data
        invalid_data = base64.b64encode(b"invalid json").decode('utf-8')
        invalid_import = client.post(f"/api/v1/database/import?import_file={invalid_data}")
        assert invalid_import.status_code == 500
        
        # Test validation with empty database
        validation_response = client.post("/api/v1/database/validate")
        assert validation_response.status_code == 200
        
        validation_data = validation_response.json()
        assert validation_data["overall_status"] == "valid"  # Empty is valid
        
        # Test health check with empty database
        health_response = client.get("/api/v1/database/health")
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        # Should still be healthy even if empty
        assert health_data["overall_status"] in ["healthy", "degraded"]


class TestDatabaseBackupRestore:
    """Test complete backup and restore workflows."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_full_backup_restore_workflow(self, client):
        """Test complete backup and restore workflow."""
        # This test would require a more complex setup with actual documents
        # For now, we'll test the workflow structure
        
        # 1. Create some test data (would be done through document upload)
        # 2. Export the database
        export_response = client.get("/api/v1/database/export?format=json")
        assert export_response.status_code == 200
        
        # 3. Validate export data
        export_data = export_response.json()
        assert "export_info" in export_data
        assert "documents" in export_data
        
        # 4. Clear database
        clear_response = client.delete("/api/v1/database/clear?confirm=true")
        assert clear_response.status_code == 200
        
        # 5. Verify database is empty
        stats_response = client.get("/api/v1/database/stats")
        stats = stats_response.json()
        assert stats["total_documents"] == 0
        
        # 6. Import data back (validation only for this test)
        encoded_data = base64.b64encode(
            json.dumps(export_data).encode('utf-8')
        ).decode('utf-8')
        
        import_response = client.post(
            f"/api/v1/database/import?validate_only=true&import_file={encoded_data}"
        )
        assert import_response.status_code == 200
        
        # 7. Verify validation results
        import_result = import_response.json()
        assert "validation_result" in import_result
        assert import_result["validation_result"]["valid"] is True
    
    @pytest.mark.asyncio
    async def test_backup_integrity_verification(self, client):
        """Test backup integrity verification."""
        # Export database
        export_response = client.get("/api/v1/database/export?format=json")
        assert export_response.status_code == 200
        
        export_data = export_response.json()
        
        # Verify export has integrity information
        export_info = export_data["export_info"]
        assert "checksum" in export_info
        assert "version" in export_info
        assert "exported_at" in export_info
        
        # Verify checksum is valid format (64 character hex string)
        checksum = export_info["checksum"]
        assert len(checksum) == 64
        assert all(c in '0123456789abcdef' for c in checksum.lower())
    
    @pytest.mark.asyncio
    async def test_incremental_backup_simulation(self, client):
        """Test simulation of incremental backup workflow."""
        # This would test incremental backup functionality
        # For now, we test the basic structure
        
        # Get initial state
        initial_export = client.get("/api/v1/database/export?format=json")
        assert initial_export.status_code == 200
        
        initial_data = initial_export.json()
        initial_count = initial_data["export_info"]["total_documents"]
        
        # Simulate adding new documents (would be done through upload API)
        # For this test, we just verify the export structure supports it
        
        # Get updated state
        updated_export = client.get("/api/v1/database/export?format=json")
        assert updated_export.status_code == 200
        
        updated_data = updated_export.json()
        
        # Verify export structure supports incremental operations
        assert "export_info" in updated_data
        assert "exported_at" in updated_data["export_info"]
        
        # Timestamps should be different (if we waited between exports)
        # In a real scenario, we'd track changes and only export deltas


if __name__ == "__main__":
    pytest.main([__file__])