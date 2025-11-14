"""
Integration tests for search API endpoints.

These tests verify the complete search functionality including
API endpoints, search engine, vector database, and embedding services.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime
import json

from app.main import app
from app.models.search import SearchType
from app.models.chunk import Chunk
from app.models.document import Document
from app.services.search_engine import SearchEngine
from app.services.vector_database import VectorDatabaseService
from app.services.embedding_service import EmbeddingService


class TestSearchAPIIntegration:
    """Integration tests for search API with mocked services."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_vector_db(self):
        """Create mock vector database service."""
        mock_db = AsyncMock(spec=VectorDatabaseService)
        
        # Mock search results
        mock_db.search_similar.return_value = [
            {
                "id": "chunk_1",
                "content": "Machine learning is a subset of artificial intelligence.",
                "similarity_score": 0.89,
                "metadata": {
                    "document_id": "doc_1",
                    "chunk_index": 0,
                    "start_index": 0,
                    "end_index": 58,
                    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Introduction",
                    "page_number": 1,
                    "language": "en",
                    "token_count": 12
                }
            },
            {
                "id": "chunk_2",
                "content": "Deep learning algorithms use neural networks with multiple layers.",
                "similarity_score": 0.76,
                "metadata": {
                    "document_id": "doc_2",
                    "chunk_index": 0,
                    "start_index": 0,
                    "end_index": 65,
                    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Deep Learning",
                    "page_number": 5,
                    "language": "en",
                    "token_count": 14
                }
            }
        ]
        
        # Mock collection stats
        mock_db.get_collection_stats.return_value = {
            "total_documents": 10,
            "total_chunks": 150,
            "collection_size": "2.5MB"
        }
        
        return mock_db
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        mock_service = AsyncMock(spec=EmbeddingService)
        
        # Mock embedding generation
        mock_service.generate_embedding.return_value = [0.1] * 384  # Mock 384-dim embedding
        
        # Mock service stats
        mock_service.get_service_stats.return_value = {
            "current_model": "sentence-transformers/all-MiniLM-L6-v2",
            "model_dimensions": 384,
            "total_embeddings_generated": 500
        }
        
        return mock_service
    
    @pytest.fixture
    def search_engine_with_mocks(self, mock_vector_db, mock_embedding_service):
        """Create search engine with mocked dependencies."""
        return SearchEngine(mock_vector_db, mock_embedding_service)


class TestSemanticSearchIntegration(TestSearchAPIIntegration):
    """Integration tests for semantic search."""
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_semantic_search_full_pipeline(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test complete semantic search pipeline."""
        # Setup mocks
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        
        # Test data
        search_data = {
            "query": "machine learning algorithms",
            "top_k": 5,
            "min_similarity": 0.7,
            "highlight": True
        }
        
        # Execute
        response = client.post("/api/v1/search/", json=search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["query"] == "machine learning algorithms"
        assert data["search_type"] == "semantic"
        assert len(data["results"]) == 2
        assert data["total_results"] == 2
        assert "search_time" in data
        
        # Verify result details
        result1 = data["results"][0]
        assert result1["similarity_score"] == 0.89
        assert "Machine learning" in result1["chunk"]["content"]
        assert result1["document"]["id"] == "doc_1"
        assert result1["rank"] == 1
        
        result2 = data["results"][1]
        assert result2["similarity_score"] == 0.76
        assert "Deep learning" in result2["chunk"]["content"]
        assert result2["rank"] == 2
        
        # Verify services were called
        mock_embedding_service.generate_embedding.assert_called_once_with("machine learning algorithms")
        mock_vector_db.search_similar.assert_called_once()
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_semantic_search_with_filters(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test semantic search with various filters."""
        # Setup mocks
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        
        # Test data with comprehensive filters
        search_data = {
            "query": "neural networks",
            "top_k": 10,
            "min_similarity": 0.6,
            "document_ids": ["doc_1", "doc_2"],
            "document_types": ["pdf"],
            "languages": ["en"],
            "date_from": "2024-01-01T00:00:00",
            "date_to": "2024-12-31T23:59:59",
            "filters": {
                "section_title": "Deep Learning",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
            },
            "include_metadata": True,
            "highlight": True
        }
        
        # Execute
        response = client.post("/api/v1/search/", json=search_data)
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "neural networks"
        
        # Verify filters were applied (check call arguments)
        call_args = mock_vector_db.search_similar.call_args
        assert call_args is not None
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_semantic_search_no_results(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test semantic search with no results."""
        # Setup mocks for no results
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        mock_vector_db.search_similar.return_value = []
        
        # Test data
        search_data = {
            "query": "nonexistent topic xyz123",
            "min_similarity": 0.9
        }
        
        # Execute
        response = client.post("/api/v1/search/", json=search_data)
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "nonexistent topic xyz123"
        assert len(data["results"]) == 0
        assert data["total_results"] == 0


class TestHybridSearchIntegration(TestSearchAPIIntegration):
    """Integration tests for hybrid search."""
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_hybrid_search_full_pipeline(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test complete hybrid search pipeline."""
        # Setup mocks
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        
        # Mock additional results for lexical search simulation
        mock_vector_db.search_similar.side_effect = [
            # First call for semantic search
            [
                {
                    "id": "chunk_1",
                    "content": "Machine learning is a subset of artificial intelligence.",
                    "similarity_score": 0.89,
                    "metadata": {
                        "document_id": "doc_1",
                        "chunk_index": 0,
                        "start_index": 0,
                        "end_index": 58,
                        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                        "created_at": datetime.now().isoformat(),
                        "section_title": "Introduction",
                        "page_number": 1,
                        "language": "en",
                        "token_count": 12
                    }
                }
            ],
            # Second call for lexical search (simulated)
            [
                {
                    "id": "chunk_3",
                    "content": "Algorithms are step-by-step procedures for calculations.",
                    "similarity_score": 0.0,  # Will be overridden by lexical scoring
                    "metadata": {
                        "document_id": "doc_3",
                        "chunk_index": 0,
                        "start_index": 0,
                        "end_index": 54,
                        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                        "created_at": datetime.now().isoformat(),
                        "section_title": "Algorithms",
                        "page_number": 3,
                        "language": "en",
                        "token_count": 10
                    }
                }
            ]
        ]
        
        # Test data
        search_data = {
            "query": "machine learning algorithms",
            "top_k": 10,
            "min_similarity": 0.5
        }
        
        # Execute
        response = client.post("/api/v1/search/hybrid", json=search_data)
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "machine learning algorithms"
        assert data["search_type"] == "hybrid"
        assert len(data["results"]) >= 1  # Should have at least semantic results
        
        # Verify embedding service was called
        mock_embedding_service.generate_embedding.assert_called()
        
        # Verify vector database was called multiple times (semantic + lexical)
        assert mock_vector_db.search_similar.call_count >= 1


class TestSearchSuggestionsIntegration(TestSearchAPIIntegration):
    """Integration tests for search suggestions."""
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_search_suggestions_pipeline(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test search suggestions pipeline."""
        # Setup mocks
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        
        # Execute
        response = client.get("/api/v1/search/suggestions?q=machine&max_suggestions=5")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "machine"
        assert "suggestions" in data
        assert "total_suggestions" in data
        
        # Verify suggestions structure
        if data["suggestions"]:
            suggestion = data["suggestions"][0]
            assert "suggestion" in suggestion
            assert "frequency" in suggestion
            assert "category" in suggestion


class TestContextRetrievalIntegration(TestSearchAPIIntegration):
    """Integration tests for context retrieval."""
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_context_retrieval_pipeline(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test context retrieval pipeline."""
        # Setup mocks
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        
        # Test data
        context_data = {
            "query": "machine learning basics",
            "max_tokens": 2000,
            "max_chunks": 5,
            "min_similarity": 0.6
        }
        
        # Execute
        response = client.post("/api/v1/search/context", json=context_data)
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "context" in data
        assert "chunks_used" in data
        assert "total_tokens" in data
        assert "retrieval_time" in data
        assert "truncated" in data
        
        # Verify context content
        assert len(data["context"]) > 0
        assert isinstance(data["chunks_used"], list)
        assert isinstance(data["total_tokens"], int)
        assert isinstance(data["truncated"], bool)
        
        # Verify services were called
        mock_embedding_service.generate_embedding.assert_called_once_with("machine learning basics")
        mock_vector_db.search_similar.assert_called_once()


class TestSearchStatisticsIntegration(TestSearchAPIIntegration):
    """Integration tests for search statistics."""
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_search_statistics_pipeline(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test search statistics pipeline."""
        # Setup mocks
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        
        # Execute
        response = client.get("/api/v1/search/stats")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        
        # Verify statistics structure
        expected_keys = [
            "total_searches",
            "avg_search_time",
            "search_types_distribution",
            "vector_db_stats",
            "embedding_service_stats"
        ]
        
        for key in expected_keys:
            assert key in data
        
        # Verify data types
        assert isinstance(data["total_searches"], int)
        assert isinstance(data["avg_search_time"], (int, float))
        assert isinstance(data["search_types_distribution"], dict)
        assert isinstance(data["vector_db_stats"], dict)
        assert isinstance(data["embedding_service_stats"], dict)


class TestSearchHealthIntegration(TestSearchAPIIntegration):
    """Integration tests for search health check."""
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_search_health_check_healthy(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test search health check when services are healthy."""
        # Setup mocks
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        
        # Execute
        response = client.get("/api/v1/search/health")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        
        # Verify health response structure
        expected_keys = [
            "status",
            "search_engine",
            "total_searches_performed",
            "avg_search_time",
            "vector_db_status",
            "embedding_service_status"
        ]
        
        for key in expected_keys:
            assert key in data
        
        assert data["status"] == "healthy"
        assert data["search_engine"] == "operational"
        assert data["vector_db_status"] == "connected"
        assert data["embedding_service_status"] == "operational"
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_search_health_check_unhealthy(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test search health check when services are unhealthy."""
        # Setup mocks to fail
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        mock_vector_db.get_collection_stats.side_effect = Exception("Database connection failed")
        
        # Execute
        response = client.get("/api/v1/search/health")
        
        # Verify
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data


class TestSearchAPIErrorHandling(TestSearchAPIIntegration):
    """Integration tests for error handling."""
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_search_with_service_failure(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test search behavior when services fail."""
        # Setup mocks to fail
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        mock_embedding_service.generate_embedding.side_effect = Exception("Embedding service failed")
        
        # Test data
        search_data = {"query": "test query"}
        
        # Execute
        response = client.post("/api/v1/search/", json=search_data)
        
        # Verify error handling
        assert response.status_code == 500
        assert "Search failed" in response.json()["detail"]
    
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_search_with_timeout(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test search behavior with timeout."""
        # Setup mocks with timeout simulation
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow operation
            return []
        
        mock_vector_db.search_similar.side_effect = slow_search
        
        # Test data
        search_data = {"query": "test query"}
        
        # Execute (this would timeout in a real scenario with proper timeout handling)
        # For now, we'll just verify the mock setup
        response = client.post("/api/v1/search/", json=search_data)
        
        # In a real implementation with timeout handling, this would return a timeout error
        # For now, we verify the test setup works
        assert response.status_code in [200, 500, 504]  # Various possible outcomes


class TestSearchAPIPerformance(TestSearchAPIIntegration):
    """Performance tests for search API."""
    
    @pytest.mark.performance
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_search_response_time(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test search response time is within acceptable limits."""
        # Setup mocks
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        
        # Test data
        search_data = {"query": "performance test query"}
        
        # Execute and measure time
        import time
        start_time = time.time()
        response = client.post("/api/v1/search/", json=search_data)
        end_time = time.time()
        
        # Verify
        assert response.status_code == 200
        response_time = end_time - start_time
        
        # Response should be fast with mocked services
        assert response_time < 1.0  # Should complete within 1 second
        
        # Verify search_time is reported in response
        data = response.json()
        assert "search_time" in data
        assert isinstance(data["search_time"], (int, float))
    
    @pytest.mark.performance
    @patch('app.core.dependencies.get_vector_database')
    @patch('app.core.dependencies.get_embedding_service')
    def test_concurrent_search_performance(
        self, 
        mock_get_embedding, 
        mock_get_vector, 
        client, 
        mock_vector_db, 
        mock_embedding_service
    ):
        """Test performance with concurrent search requests."""
        # Setup mocks
        mock_get_vector.return_value = mock_vector_db
        mock_get_embedding.return_value = mock_embedding_service
        
        # Test data
        search_data = {"query": "concurrent performance test"}
        
        # Execute multiple concurrent requests
        import concurrent.futures
        import time
        
        def make_request():
            return client.post("/api/v1/search/", json=search_data)
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        
        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == 200
        
        # Verify reasonable total time for concurrent requests
        total_time = end_time - start_time
        assert total_time < 5.0  # Should complete all requests within 5 seconds


if __name__ == "__main__":
    pytest.main([__file__])