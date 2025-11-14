"""
Tests for search API endpoints.

This module tests all search-related API endpoints including semantic search,
hybrid search, search suggestions, context retrieval, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime
import json

from app.main import app
from app.models.search import (
    SearchQuery, SearchResponse, SearchResult, SearchType,
    SearchSuggestion, SearchSuggestionsResponse,
    ContextRetrievalRequest, ContextRetrievalResponse
)
from app.models.chunk import Chunk
from app.models.document import Document
from app.core.exceptions import SearchEngineError, ValidationError


class TestSearchAPI:
    """Test class for search API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_search_engine(self):
        """Create mock search engine."""
        return AsyncMock()
    
    def setup_search_engine_mock(self, mock_search_engine):
        """Helper to setup search engine dependency override."""
        from app.core.dependencies import get_search_engine
        from app.main import app
        
        def override_get_search_engine():
            return mock_search_engine
        
        app.dependency_overrides[get_search_engine] = override_get_search_engine
        return app
    
    def cleanup_dependency_overrides(self):
        """Helper to clean up dependency overrides."""
        from app.main import app
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def sample_chunk(self):
        """Create sample chunk for testing."""
        return Chunk(
            id="chunk_1",
            document_id="doc_1",
            content="This is a sample chunk about machine learning algorithms.",
            start_index=0,
            end_index=58,
            chunk_index=0,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            created_at=datetime.now(),
            section_title="Introduction to ML",
            page_number=1,
            language="en",
            token_count=12
        )
    
    @pytest.fixture
    def sample_document(self):
        """Create sample document for testing."""
        return Document(
            id="doc_1",
            filename="ml_guide.pdf",
            file_type="pdf",
            file_size=1024000,
            processing_status="completed"
        )
    
    @pytest.fixture
    def sample_search_result(self, sample_chunk, sample_document):
        """Create sample search result."""
        return SearchResult(
            chunk=sample_chunk,
            document=sample_document,
            similarity_score=0.85,
            highlighted_content="This is a sample chunk about <mark>machine learning</mark> algorithms.",
            rank=1
        )
    
    @pytest.fixture
    def sample_search_response(self, sample_search_result):
        """Create sample search response."""
        return SearchResponse(
            query="machine learning",
            search_type=SearchType.SEMANTIC,
            results=[sample_search_result],
            total_results=1,
            search_time=0.123,
            filters_applied=None
        )


class TestSemanticSearchEndpoint(TestSearchAPI):
    """Test semantic search endpoint."""
    
    def test_semantic_search_success(self, client, mock_search_engine, sample_search_response):
        """Test successful semantic search."""
        # Setup
        self.setup_search_engine_mock(mock_search_engine)
        mock_search_engine.semantic_search.return_value = sample_search_response
        
        try:
            # Test data
            search_data = {
                "query": "machine learning",
                "top_k": 10,
                "min_similarity": 0.5,
                "highlight": True
            }
            
            # Execute
            response = client.post("/api/v1/search/", json=search_data)
            
            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "machine learning"
            assert data["search_type"] == "semantic"
            assert len(data["results"]) == 1
            assert data["results"][0]["similarity_score"] == 0.85
            assert "machine learning" in data["results"][0]["highlighted_content"]
            
            # Verify search engine was called correctly
            mock_search_engine.semantic_search.assert_called_once()
            call_args = mock_search_engine.semantic_search.call_args[0][0]
            assert call_args.query == "machine learning"
            assert call_args.search_type == SearchType.SEMANTIC
        finally:
            self.cleanup_dependency_overrides()
    
    def test_semantic_search_with_filters(self, client, mock_search_engine, sample_search_response):
        """Test semantic search with filters."""
        # Setup
        self.setup_search_engine_mock(mock_search_engine)
        mock_search_engine.semantic_search.return_value = sample_search_response
        
        try:
            # Test data with filters
            search_data = {
                "query": "machine learning",
                "top_k": 5,
                "min_similarity": 0.7,
                "document_ids": ["doc_1", "doc_2"],
                "document_types": ["pdf"],
                "languages": ["en"],
                "filters": {"section_title": "Introduction"}
            }
            
            # Execute
            response = client.post("/api/v1/search/", json=search_data)
            
            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "machine learning"
            
            # Verify filters were passed correctly
            call_args = mock_search_engine.semantic_search.call_args[0][0]
            assert call_args.document_ids == ["doc_1", "doc_2"]
            assert call_args.document_types == ["pdf"]
            assert call_args.languages == ["en"]
            assert call_args.filters == {"section_title": "Introduction"}
        finally:
            self.cleanup_dependency_overrides()
    
    def test_semantic_search_validation_error(self, client, mock_search_engine):
        """Test semantic search with validation error."""
        # Test data with empty query (should trigger validation error)
        search_data = {"query": ""}
        
        # Execute
        response = client.post("/api/v1/search/", json=search_data)
        
        # Verify - FastAPI returns 422 for validation errors
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0
        assert "query" in str(data["detail"][0])
    
    def test_semantic_search_engine_error(self, client, mock_search_engine):
        """Test semantic search with search engine error."""
        # Setup
        self.setup_search_engine_mock(mock_search_engine)
        mock_search_engine.semantic_search.side_effect = SearchEngineError("Database connection failed")
        
        try:
            # Test data
            search_data = {"query": "test query"}
            
            # Execute
            response = client.post("/api/v1/search/", json=search_data)
            
            # Verify
            assert response.status_code == 500
            data = response.json()
            assert "Search failed" in data["message"]
            assert data["error_code"] == "HTTP_500"
        finally:
            self.cleanup_dependency_overrides()
    
    def test_semantic_search_invalid_json(self, client):
        """Test semantic search with invalid JSON."""
        # Execute
        response = client.post("/api/v1/search/", data="invalid json")
        
        # Verify
        assert response.status_code == 422  # Unprocessable Entity


class TestHybridSearchEndpoint(TestSearchAPI):
    """Test hybrid search endpoint."""
    
    @patch('app.core.dependencies.get_search_engine')
    def test_hybrid_search_success(self, mock_get_engine, client, mock_search_engine, sample_search_response):
        """Test successful hybrid search."""
        # Setup
        hybrid_response = sample_search_response.model_copy()
        hybrid_response.search_type = SearchType.HYBRID
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.hybrid_search.return_value = hybrid_response
        
        # Test data
        search_data = {
            "query": "machine learning algorithms",
            "top_k": 15,
            "min_similarity": 0.6
        }
        
        # Execute
        response = client.post("/api/v1/search/hybrid", json=search_data)
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "machine learning algorithms"
        assert data["search_type"] == "hybrid"
        assert len(data["results"]) == 1
        
        # Verify search engine was called correctly
        mock_search_engine.hybrid_search.assert_called_once()
        call_args = mock_search_engine.hybrid_search.call_args[0][0]
        assert call_args.query == "machine learning algorithms"
        assert call_args.search_type == SearchType.HYBRID
    
    @patch('app.core.dependencies.get_search_engine')
    def test_hybrid_search_empty_results(self, mock_get_engine, client, mock_search_engine):
        """Test hybrid search with no results."""
        # Setup
        empty_response = SearchResponse(
            query="nonexistent topic",
            search_type=SearchType.HYBRID,
            results=[],
            total_results=0,
            search_time=0.05,
            filters_applied=None
        )
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.hybrid_search.return_value = empty_response
        
        # Test data
        search_data = {"query": "nonexistent topic"}
        
        # Execute
        response = client.post("/api/v1/search/hybrid", json=search_data)
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "nonexistent topic"
        assert len(data["results"]) == 0
        assert data["total_results"] == 0


class TestSearchSuggestionsEndpoint(TestSearchAPI):
    """Test search suggestions endpoint."""
    
    @patch('app.core.dependencies.get_search_engine')
    def test_get_suggestions_success(self, mock_get_engine, client, mock_search_engine):
        """Test successful search suggestions."""
        # Setup
        suggestions = [
            SearchSuggestion(suggestion="machine learning basics", frequency=10, category="pattern"),
            SearchSuggestion(suggestion="machine learning algorithms", frequency=8, category="pattern"),
            SearchSuggestion(suggestion="machine learning tutorial", frequency=5, category="pattern")
        ]
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.get_search_suggestions.return_value = suggestions
        
        # Execute
        response = client.get("/api/v1/search/suggestions?q=machine&max_suggestions=5")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "machine"
        assert len(data["suggestions"]) == 3
        assert data["total_suggestions"] == 3
        assert data["suggestions"][0]["suggestion"] == "machine learning basics"
        assert data["suggestions"][0]["frequency"] == 10
        
        # Verify search engine was called correctly
        mock_search_engine.get_search_suggestions.assert_called_once_with(
            partial_query="machine",
            max_suggestions=5
        )
    
    @patch('app.core.dependencies.get_search_engine')
    def test_get_suggestions_empty_query(self, mock_get_engine, client, mock_search_engine):
        """Test suggestions with empty query."""
        # Execute
        response = client.get("/api/v1/search/suggestions?q=")
        
        # Verify
        assert response.status_code == 400
        assert "at least 1 character" in response.json()["detail"]
    
    @patch('app.core.dependencies.get_search_engine')
    def test_get_suggestions_no_results(self, mock_get_engine, client, mock_search_engine):
        """Test suggestions with no results."""
        # Setup
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.get_search_suggestions.return_value = []
        
        # Execute
        response = client.get("/api/v1/search/suggestions?q=xyz")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "xyz"
        assert len(data["suggestions"]) == 0
        assert data["total_suggestions"] == 0
    
    def test_get_suggestions_invalid_params(self, client):
        """Test suggestions with invalid parameters."""
        # Test max_suggestions too high
        response = client.get("/api/v1/search/suggestions?q=test&max_suggestions=100")
        assert response.status_code == 422
        
        # Test max_suggestions too low
        response = client.get("/api/v1/search/suggestions?q=test&max_suggestions=0")
        assert response.status_code == 422


class TestContextRetrievalEndpoint(TestSearchAPI):
    """Test context retrieval endpoint."""
    
    @patch('app.core.dependencies.get_search_engine')
    def test_retrieve_context_success(self, mock_get_engine, client, mock_search_engine, sample_search_result):
        """Test successful context retrieval."""
        # Setup
        context_response = ContextRetrievalResponse(
            context="[Section: Introduction to ML | Page: 1 | Source: ml_guide.pdf]\nThis is a sample chunk about machine learning algorithms.",
            chunks_used=[sample_search_result],
            total_tokens=150,
            retrieval_time=0.089,
            truncated=False
        )
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.retrieve_context_for_rag.return_value = context_response
        
        # Test data
        context_data = {
            "query": "machine learning",
            "max_tokens": 4000,
            "max_chunks": 10,
            "min_similarity": 0.6
        }
        
        # Execute
        response = client.post("/api/v1/search/context", json=context_data)
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert "machine learning algorithms" in data["context"]
        assert len(data["chunks_used"]) == 1
        assert data["total_tokens"] == 150
        assert data["truncated"] is False
        
        # Verify search engine was called correctly
        mock_search_engine.retrieve_context_for_rag.assert_called_once()
        call_args = mock_search_engine.retrieve_context_for_rag.call_args[0][0]
        assert call_args.query == "machine learning"
        assert call_args.max_tokens == 4000
        assert call_args.max_chunks == 10
    
    @patch('app.core.dependencies.get_search_engine')
    def test_retrieve_context_truncated(self, mock_get_engine, client, mock_search_engine, sample_search_result):
        """Test context retrieval with truncation."""
        # Setup
        context_response = ContextRetrievalResponse(
            context="Truncated context...",
            chunks_used=[sample_search_result],
            total_tokens=100,
            retrieval_time=0.045,
            truncated=True
        )
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.retrieve_context_for_rag.return_value = context_response
        
        # Test data with small token limit
        context_data = {
            "query": "machine learning",
            "max_tokens": 100,
            "max_chunks": 5
        }
        
        # Execute
        response = client.post("/api/v1/search/context", json=context_data)
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["truncated"] is True
        assert data["total_tokens"] == 100
    
    @patch('app.core.dependencies.get_search_engine')
    def test_retrieve_context_validation_error(self, mock_get_engine, client, mock_search_engine):
        """Test context retrieval with validation error."""
        # Setup
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.retrieve_context_for_rag.side_effect = ValidationError("Invalid parameters")
        
        # Test data
        context_data = {"query": ""}
        
        # Execute
        response = client.post("/api/v1/search/context", json=context_data)
        
        # Verify
        assert response.status_code == 400
        assert "Invalid context retrieval parameters" in response.json()["detail"]
    
    def test_retrieve_context_invalid_params(self, client):
        """Test context retrieval with invalid parameters."""
        # Test max_tokens too high
        context_data = {
            "query": "test",
            "max_tokens": 10000
        }
        response = client.post("/api/v1/search/context", json=context_data)
        assert response.status_code == 422
        
        # Test max_chunks too high
        context_data = {
            "query": "test",
            "max_chunks": 100
        }
        response = client.post("/api/v1/search/context", json=context_data)
        assert response.status_code == 422


class TestSearchStatisticsEndpoint(TestSearchAPI):
    """Test search statistics endpoint."""
    
    @patch('app.core.dependencies.get_search_engine')
    def test_get_search_stats_success(self, mock_get_engine, client, mock_search_engine):
        """Test successful search statistics retrieval."""
        # Setup
        stats = {
            "total_searches": 150,
            "avg_search_time": 0.234,
            "search_types_distribution": {
                "semantic": 100,
                "hybrid": 50
            },
            "vector_db_stats": {
                "total_documents": 25,
                "total_chunks": 500
            },
            "embedding_service_stats": {
                "current_model": "sentence-transformers/all-MiniLM-L6-v2",
                "total_embeddings_generated": 1000
            }
        }
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.get_search_stats.return_value = stats
        
        # Execute
        response = client.get("/api/v1/search/stats")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["total_searches"] == 150
        assert data["avg_search_time"] == 0.234
        assert "search_types_distribution" in data
        assert "vector_db_stats" in data
        assert "embedding_service_stats" in data
    
    @patch('app.core.dependencies.get_search_engine')
    def test_get_search_stats_error(self, mock_get_engine, client, mock_search_engine):
        """Test search statistics with error."""
        # Setup
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.get_search_stats.side_effect = Exception("Database error")
        
        # Execute
        response = client.get("/api/v1/search/stats")
        
        # Verify
        assert response.status_code == 500
        assert "Failed to retrieve search statistics" in response.json()["detail"]


class TestSearchHealthEndpoint(TestSearchAPI):
    """Test search health check endpoint."""
    
    @patch('app.core.dependencies.get_search_engine')
    def test_search_health_success(self, mock_get_engine, client, mock_search_engine, sample_search_response):
        """Test successful search health check."""
        # Setup
        stats = {"total_searches": 100, "avg_search_time": 0.15}
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.get_search_stats.return_value = stats
        mock_search_engine.semantic_search.return_value = sample_search_response
        
        # Execute
        response = client.get("/api/v1/search/health")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["search_engine"] == "operational"
        assert data["total_searches_performed"] == 100
        assert data["vector_db_status"] == "connected"
        assert data["embedding_service_status"] == "operational"
    
    @patch('app.core.dependencies.get_search_engine')
    def test_search_health_failure(self, mock_get_engine, client, mock_search_engine):
        """Test search health check failure."""
        # Setup
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.get_search_stats.side_effect = Exception("Service unavailable")
        
        # Execute
        response = client.get("/api/v1/search/health")
        
        # Verify
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data


class TestSearchAPIEdgeCases(TestSearchAPI):
    """Test edge cases and error scenarios."""
    
    def test_search_with_special_characters(self, client):
        """Test search with special characters in query."""
        with patch('app.api.endpoints.search.get_search_engine') as mock_get_engine:
            mock_search_engine = AsyncMock()
            mock_get_engine.return_value = mock_search_engine
            
            # Create a response for special character query
            response_obj = SearchResponse(
                query="test@#$%^&*()",
                search_type=SearchType.SEMANTIC,
                results=[],
                total_results=0,
                search_time=0.1,
                filters_applied=None
            )
            mock_search_engine.semantic_search.return_value = response_obj
            
            # Test data with special characters
            search_data = {"query": "test@#$%^&*()"}
            
            # Execute
            response = client.post("/api/v1/search/", json=search_data)
            
            # Verify
            assert response.status_code == 200
    
    def test_search_with_unicode_characters(self, client):
        """Test search with Unicode characters."""
        with patch('app.api.endpoints.search.get_search_engine') as mock_get_engine:
            mock_search_engine = AsyncMock()
            mock_get_engine.return_value = mock_search_engine
            
            # Create a response for Unicode query
            response_obj = SearchResponse(
                query="机器学习",
                search_type=SearchType.SEMANTIC,
                results=[],
                total_results=0,
                search_time=0.1,
                filters_applied=None
            )
            mock_search_engine.semantic_search.return_value = response_obj
            
            # Test data with Unicode characters
            search_data = {"query": "机器学习"}
            
            # Execute
            response = client.post("/api/v1/search/", json=search_data)
            
            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "机器学习"
    
    def test_search_with_very_long_query(self, client):
        """Test search with very long query."""
        # Create a query that's exactly at the limit
        long_query = "a" * 1000
        
        with patch('app.api.endpoints.search.get_search_engine') as mock_get_engine:
            mock_search_engine = AsyncMock()
            mock_get_engine.return_value = mock_search_engine
            
            response_obj = SearchResponse(
                query=long_query,
                search_type=SearchType.SEMANTIC,
                results=[],
                total_results=0,
                search_time=0.1,
                filters_applied=None
            )
            mock_search_engine.semantic_search.return_value = response_obj
            
            # Test data with long query
            search_data = {"query": long_query}
            
            # Execute
            response = client.post("/api/v1/search/", json=search_data)
            
            # Verify
            assert response.status_code == 200
    
    def test_search_with_too_long_query(self, client):
        """Test search with query exceeding limit."""
        # Create a query that exceeds the limit
        too_long_query = "a" * 1001
        
        # Test data with too long query
        search_data = {"query": too_long_query}
        
        # Execute
        response = client.post("/api/v1/search/", json=search_data)
        
        # Verify
        assert response.status_code == 422  # Validation error
    
    @patch('app.core.dependencies.get_search_engine')
    def test_concurrent_search_requests(self, mock_get_engine, client, mock_search_engine, sample_search_response):
        """Test handling of concurrent search requests."""
        # Setup
        mock_get_engine.return_value = mock_search_engine
        mock_search_engine.semantic_search.return_value = sample_search_response
        
        # Test data
        search_data = {"query": "concurrent test"}
        
        # Execute multiple concurrent requests (simulated)
        responses = []
        for i in range(5):
            response = client.post("/api/v1/search/", json=search_data)
            responses.append(response)
        
        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "concurrent test"
        
        # Verify search engine was called for each request
        assert mock_search_engine.semantic_search.call_count == 5


# Integration tests (these would require actual services running)
class TestSearchAPIIntegration:
    """Integration tests for search API (require actual services)."""
    
    @pytest.mark.integration
    def test_full_search_workflow(self, client):
        """Test complete search workflow with real services."""
        # This test would require actual ChromaDB and embedding services
        # Skip in unit tests, run only in integration test environment
        pytest.skip("Integration test - requires actual services")
    
    @pytest.mark.integration
    def test_search_performance(self, client):
        """Test search performance with real data."""
        # This test would measure actual search performance
        pytest.skip("Integration test - requires actual services and data")


if __name__ == "__main__":
    pytest.main([__file__])