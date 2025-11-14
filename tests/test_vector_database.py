"""Unit tests for ChromaDB vector database service."""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from app.services.vector_database import VectorDatabaseService
from app.models.chunk import Chunk
from app.models.document import Document, DocumentType, ProcessingStatus
from app.core.exceptions import VectorDatabaseError, ValidationError
from app.core.config import Settings
from chromadb.errors import NotFoundError


@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings(
        CHROMA_HOST="localhost",
        CHROMA_PORT=8001,
        CHROMA_COLLECTION_NAME="test_collection",
        ENVIRONMENT="test"
    )


@pytest.fixture
def vector_db_service(test_settings):
    """Create vector database service instance."""
    return VectorDatabaseService(test_settings)


@pytest.fixture
def sample_chunks():
    """Create sample chunks for testing."""
    chunks = []
    for i in range(3):
        chunk = Chunk(
            id=f"chunk_{i}",
            document_id="doc_1",
            content=f"This is test content for chunk {i}. It contains some meaningful text.",
            start_index=i * 100,
            end_index=(i + 1) * 100,
            chunk_index=i,
            embedding_model="test-model",
            section_title=f"Section {i}",
            page_number=1,
            language="en",
            token_count=20,
            metadata={"test_key": f"test_value_{i}"}
        )
        chunks.append(chunk)
    return chunks


@pytest.fixture
def sample_embeddings():
    """Create sample embeddings for testing."""
    return [
        [0.1, 0.2, 0.3, 0.4, 0.5] * 77,  # 385 dimensions
        [0.2, 0.3, 0.4, 0.5, 0.6] * 77,
        [0.3, 0.4, 0.5, 0.6, 0.7] * 77
    ]


class TestVectorDatabaseService:
    """Test cases for VectorDatabaseService."""
    
    @pytest.mark.asyncio
    async def test_connect_success(self, vector_db_service):
        """Test successful connection to ChromaDB."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            
            assert vector_db_service._is_connected is True
            assert vector_db_service._client is not None
            assert vector_db_service._collection is not None
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, vector_db_service):
        """Test connection failure handling."""
        with patch('chromadb.PersistentClient', side_effect=Exception("Connection failed")):
            with pytest.raises(VectorDatabaseError, match="Connection failed"):
                await vector_db_service.connect()
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, vector_db_service):
        """Test health check when service is healthy."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_collection.count.return_value = 10
            mock_client.return_value.get_collection.side_effect = NotFoundError("Collection not found")
            mock_client.return_value.create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            
            # Mock the _get_collection_count method directly
            with patch.object(vector_db_service, '_get_collection_count', return_value=10):
                health = await vector_db_service.health_check()
            
            assert health["status"] == "healthy"
            assert health["document_count"] == 10
            assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, vector_db_service):
        """Test health check when service is unhealthy."""
        health = await vector_db_service.health_check()
        
        assert health["status"] == "unhealthy"
        assert "Not connected" in health["message"]
        assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_store_embeddings_success(self, vector_db_service, sample_chunks, sample_embeddings):
        """Test successful embedding storage."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_collection.side_effect = NotFoundError("Collection not found")
            mock_client.return_value.create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            result = await vector_db_service.store_embeddings(sample_chunks, sample_embeddings)
            
            assert len(result) == 3
            assert all(chunk_id.startswith("chunk_") for chunk_id in result)
            mock_collection.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_embeddings_validation_error(self, vector_db_service, sample_chunks):
        """Test embedding storage with validation error."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_collection.side_effect = NotFoundError("Collection not found")
            mock_client.return_value.create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            
            # Mismatched lengths
            with pytest.raises(VectorDatabaseError, match="Storage failed"):
                await vector_db_service.store_embeddings(sample_chunks, [[0.1, 0.2]])
    
    @pytest.mark.asyncio
    async def test_store_embeddings_empty_list(self, vector_db_service):
        """Test embedding storage with empty lists."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            result = await vector_db_service.store_embeddings([], [])
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_search_similar_success(self, vector_db_service):
        """Test successful similarity search."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_collection.query.return_value = {
                "documents": [["Test content 1", "Test content 2"]],
                "distances": [[0.1, 0.3]],
                "ids": [["id1", "id2"]],
                "metadatas": [[{"document_id": "doc1"}, {"document_id": "doc2"}]]
            }
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            query_embedding = [0.1, 0.2, 0.3] * 128
            results = await vector_db_service.search_similar(query_embedding, top_k=5)
            
            assert len(results) == 2
            assert results[0]["similarity_score"] == 0.9  # 1 - 0.1
            assert results[1]["similarity_score"] == 0.7  # 1 - 0.3
            assert results[0]["content"] == "Test content 1"
    
    @pytest.mark.asyncio
    async def test_search_similar_with_filters(self, vector_db_service):
        """Test similarity search with filters."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_collection.query.return_value = {
                "documents": [["Filtered content"]],
                "distances": [[0.2]],
                "ids": [["filtered_id"]],
                "metadatas": [[{"document_id": "doc1"}]]
            }
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            query_embedding = [0.1, 0.2, 0.3] * 128
            filters = {"document_id": "doc1", "embedding_model": "test-model"}
            
            results = await vector_db_service.search_similar(
                query_embedding, 
                top_k=5, 
                filters=filters
            )
            
            assert len(results) == 1
            mock_collection.query.assert_called_once()
            call_args = mock_collection.query.call_args[1]
            assert "where" in call_args
    
    @pytest.mark.asyncio
    async def test_search_similar_min_similarity_filter(self, vector_db_service):
        """Test similarity search with minimum similarity threshold."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_collection.query.return_value = {
                "documents": [["Content 1", "Content 2"]],
                "distances": [[0.1, 0.8]],  # similarities: 0.9, 0.2
                "ids": [["id1", "id2"]],
                "metadatas": [[{"document_id": "doc1"}, {"document_id": "doc2"}]]
            }
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            query_embedding = [0.1, 0.2, 0.3] * 128
            
            results = await vector_db_service.search_similar(
                query_embedding, 
                top_k=5, 
                min_similarity=0.5
            )
            
            # Only first result should pass the 0.5 threshold
            assert len(results) == 1
            assert results[0]["similarity_score"] == 0.9
    
    @pytest.mark.asyncio
    async def test_search_similar_validation_error(self, vector_db_service):
        """Test search with invalid query embedding."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_collection.side_effect = NotFoundError("Collection not found")
            mock_client.return_value.create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            
            with pytest.raises(VectorDatabaseError, match="Search failed"):
                await vector_db_service.search_similar(None)
            
            with pytest.raises(VectorDatabaseError, match="Search failed"):
                await vector_db_service.search_similar([])
    
    @pytest.mark.asyncio
    async def test_delete_by_document_id_success(self, vector_db_service):
        """Test successful deletion by document ID."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_collection.get.return_value = {"ids": ["id1", "id2", "id3"]}
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            deleted_count = await vector_db_service.delete_by_document_id("doc1")
            
            assert deleted_count == 3
            mock_collection.delete.assert_called_once_with(where={"document_id": "doc1"})
    
    @pytest.mark.asyncio
    async def test_delete_by_document_id_no_chunks(self, vector_db_service):
        """Test deletion when no chunks exist for document."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_collection.get.return_value = {"ids": []}
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            deleted_count = await vector_db_service.delete_by_document_id("nonexistent_doc")
            
            assert deleted_count == 0
            mock_collection.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delete_by_ids_success(self, vector_db_service):
        """Test successful deletion by chunk IDs."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            chunk_ids = ["id1", "id2", "id3"]
            deleted_count = await vector_db_service.delete_by_ids(chunk_ids)
            
            assert deleted_count == 3
            mock_collection.delete.assert_called_once_with(ids=chunk_ids)
    
    @pytest.mark.asyncio
    async def test_delete_by_ids_empty_list(self, vector_db_service):
        """Test deletion with empty ID list."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            deleted_count = await vector_db_service.delete_by_ids([])
            
            assert deleted_count == 0
            mock_collection.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_collection_stats(self, vector_db_service):
        """Test collection statistics retrieval."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_collection.count.return_value = 100
            mock_collection.get.return_value = {
                "metadatas": [
                    {"document_id": "doc1", "embedding_model": "model1", "language": "en"},
                    {"document_id": "doc2", "embedding_model": "model1", "language": "fr"},
                    {"document_id": "doc1", "embedding_model": "model2", "language": "en"}
                ]
            }
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            stats = await vector_db_service.get_collection_stats()
            
            assert stats["total_chunks"] == 100
            assert stats["documents_count"] == 2  # doc1, doc2
            assert "model1" in stats["embedding_models"]
            assert "model2" in stats["embedding_models"]
            assert "en" in stats["languages"]
            assert "fr" in stats["languages"]
    
    @pytest.mark.asyncio
    async def test_reset_collection_success(self, vector_db_service):
        """Test successful collection reset."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            mock_client.return_value.delete_collection.return_value = None
            
            await vector_db_service.connect()
            result = await vector_db_service.reset_collection()
            
            assert result is True
            mock_client.return_value.delete_collection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_schema_success(self, vector_db_service):
        """Test successful schema validation."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_collection.get.return_value = {
                "metadatas": [{
                    "document_id": "doc1",
                    "chunk_index": 0,
                    "start_index": 0,
                    "end_index": 100,
                    "content_length": 100,
                    "embedding_model": "test-model",
                    "created_at": "2023-01-01T00:00:00"
                }]
            }
            
            mock_client.return_value.list_collections.return_value = [
                Mock(name="test_collection")
            ]
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            validation = await vector_db_service.validate_schema()
            
            assert validation["collection_exists"] is True
            assert validation["schema_valid"] is True
            assert "sample_metadata_keys" in validation
    
    @pytest.mark.asyncio
    async def test_validate_schema_collection_not_exists(self, vector_db_service):
        """Test schema validation when collection doesn't exist."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_client.return_value.list_collections.return_value = []
            
            await vector_db_service.connect()
            validation = await vector_db_service.validate_schema()
            
            assert validation["collection_exists"] is False
    
    @pytest.mark.asyncio
    async def test_build_where_clause(self, vector_db_service):
        """Test where clause building for filters."""
        # Test with various filter types
        filters = {
            "document_id": "doc1",
            "embedding_model": "test-model",
            "language": "en",
            "min_chunk_index": 5,
            "max_chunk_index": 10,
            "invalid_filter": "should_be_ignored"
        }
        
        where_clause = vector_db_service._build_where_clause(filters)
        
        assert where_clause["document_id"] == "doc1"
        assert where_clause["embedding_model"] == "test-model"
        assert where_clause["language"] == "en"
        assert where_clause["chunk_index"]["$gte"] == 5
        assert where_clause["chunk_index"]["$lte"] == 10
        assert "invalid_filter" not in where_clause
    
    @pytest.mark.asyncio
    async def test_build_where_clause_empty(self, vector_db_service):
        """Test where clause building with empty filters."""
        where_clause = vector_db_service._build_where_clause({})
        assert where_clause is None
        
        where_clause = vector_db_service._build_where_clause(None)
        assert where_clause is None
    
    @pytest.mark.asyncio
    async def test_ensure_connected_auto_connect(self, vector_db_service):
        """Test automatic connection when not connected."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            # Service is not connected initially
            assert vector_db_service._is_connected is False
            
            # This should trigger auto-connection
            await vector_db_service._ensure_connected()
            
            assert vector_db_service._is_connected is True
    
    @pytest.mark.asyncio
    async def test_disconnect(self, vector_db_service):
        """Test disconnection from ChromaDB."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            await vector_db_service.connect()
            assert vector_db_service._is_connected is True
            
            await vector_db_service.disconnect()
            assert vector_db_service._is_connected is False
            assert vector_db_service._client is None
            assert vector_db_service._collection is None


class TestVectorDatabaseServiceIntegration:
    """Integration tests for VectorDatabaseService with real ChromaDB."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary directory for test database."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def integration_service(self, temp_db_path):
        """Create service instance for integration testing."""
        settings = Settings(
            CHROMA_HOST="localhost",
            CHROMA_PORT=8001,
            CHROMA_COLLECTION_NAME="integration_test_collection",
            ENVIRONMENT="test"
        )
        
        service = VectorDatabaseService(settings)
        # Override to use temporary directory
        service._temp_path = temp_db_path
        return service
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_workflow_integration(self, integration_service, sample_chunks, sample_embeddings):
        """Test complete workflow with real ChromaDB operations."""
        try:
            # Connect
            await integration_service.connect()
            
            # Health check
            health = await integration_service.health_check()
            assert health["status"] == "healthy"
            
            # Store embeddings
            stored_ids = await integration_service.store_embeddings(sample_chunks, sample_embeddings)
            assert len(stored_ids) == 3
            
            # Search
            query_embedding = [0.15, 0.25, 0.35] * 128
            results = await integration_service.search_similar(query_embedding, top_k=2)
            assert len(results) <= 2
            
            # Get stats
            stats = await integration_service.get_collection_stats()
            assert stats["total_chunks"] >= 3
            
            # Delete by document ID
            deleted_count = await integration_service.delete_by_document_id("doc_1")
            assert deleted_count == 3
            
            # Verify deletion
            results_after_delete = await integration_service.search_similar(query_embedding, top_k=10)
            assert len(results_after_delete) == 0
            
        finally:
            await integration_service.disconnect()


# Test fixtures and utilities
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def test_get_vector_database_service():
    """Test factory function for vector database service."""
    from app.services.vector_database import get_vector_database_service
    
    service = get_vector_database_service()
    assert isinstance(service, VectorDatabaseService)
    assert service.settings is not None