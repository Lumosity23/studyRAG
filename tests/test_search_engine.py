"""
Unit tests for SearchEngine service.

Tests search accuracy, performance, ranking, filtering, and context retrieval.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.services.search_engine import SearchEngine
from app.services.vector_database import VectorDatabaseService
from app.services.embedding_service import EmbeddingService
from app.models.search import (
    SearchQuery, SearchResult, SearchType, ContextRetrievalRequest
)
from app.models.chunk import Chunk
from app.models.document import Document, DocumentType, ProcessingStatus
from app.core.exceptions import SearchEngineError


class TestSearchEngine:
    """Test cases for SearchEngine service."""
    
    @pytest.fixture
    def mock_vector_db(self):
        """Mock vector database service."""
        mock_db = Mock(spec=VectorDatabaseService)
        mock_db.search_similar = AsyncMock()
        mock_db.get_collection_stats = AsyncMock(return_value={
            "total_chunks": 100,
            "documents_count": 10,
            "embedding_models": ["test-model"],
            "languages": ["en", "fr"]
        })
        return mock_db
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        mock_service = Mock(spec=EmbeddingService)
        mock_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
        mock_service.get_service_stats = AsyncMock(return_value={
            "active_model": "test-model",
            "loaded_models": ["test-model"],
            "cache_stats": {"size": 10, "hit_rate": 0.8}
        })
        return mock_service
    
    @pytest.fixture
    def search_engine(self, mock_vector_db, mock_embedding_service):
        """Create SearchEngine instance with mocked dependencies."""
        return SearchEngine(
            vector_db=mock_vector_db,
            embedding_service=mock_embedding_service,
            max_context_tokens=4000,
            default_chunk_overlap=50
        )
    
    @pytest.fixture
    def sample_vector_results(self):
        """Sample vector database results."""
        return [
            {
                "id": "chunk_1",
                "content": "This is a test document about machine learning algorithms.",
                "similarity_score": 0.95,
                "metadata": {
                    "document_id": "doc_1",
                    "chunk_index": 0,
                    "start_index": 0,
                    "end_index": 58,
                    "embedding_model": "test-model",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Introduction",
                    "page_number": 1,
                    "language": "en",
                    "token_count": 12
                }
            },
            {
                "id": "chunk_2", 
                "content": "Machine learning is a subset of artificial intelligence.",
                "similarity_score": 0.87,
                "metadata": {
                    "document_id": "doc_1",
                    "chunk_index": 1,
                    "start_index": 58,
                    "end_index": 113,
                    "embedding_model": "test-model",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Definition",
                    "page_number": 1,
                    "language": "en",
                    "token_count": 10
                }
            },
            {
                "id": "chunk_3",
                "content": "Deep learning uses neural networks with multiple layers.",
                "similarity_score": 0.82,
                "metadata": {
                    "document_id": "doc_2",
                    "chunk_index": 0,
                    "start_index": 0,
                    "end_index": 55,
                    "embedding_model": "test-model",
                    "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
                    "section_title": "Deep Learning",
                    "page_number": 2,
                    "language": "en",
                    "token_count": 11
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_semantic_search_basic(self, search_engine, mock_vector_db, sample_vector_results):
        """Test basic semantic search functionality."""
        # Setup
        mock_vector_db.search_similar.return_value = sample_vector_results
        
        query = SearchQuery(
            query="machine learning algorithms",
            search_type=SearchType.SEMANTIC,
            top_k=10,
            min_similarity=0.5
        )
        
        # Execute
        response = await search_engine.semantic_search(query)
        
        # Verify
        assert response.query == "machine learning algorithms"
        assert response.search_type == SearchType.SEMANTIC
        assert len(response.results) == 3
        assert response.total_results == 3
        assert response.search_time > 0
        
        # Check results are properly ranked (highest similarity first)
        assert response.results[0].similarity_score >= response.results[1].similarity_score
        assert response.results[1].similarity_score >= response.results[2].similarity_score
        
        # Check rank assignment
        assert response.results[0].rank == 1
        assert response.results[1].rank == 2
        assert response.results[2].rank == 3
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_filters(self, search_engine, mock_vector_db, sample_vector_results):
        """Test semantic search with various filters."""
        mock_vector_db.search_similar.return_value = sample_vector_results
        
        query = SearchQuery(
            query="machine learning",
            document_ids=["doc_1"],
            languages=["en"],
            min_similarity=0.8,
            top_k=5
        )
        
        response = await search_engine.semantic_search(query)
        
        # Verify filters were applied
        assert response.filters_applied is not None
        assert "document_ids" in response.filters_applied
        assert response.filters_applied["document_ids"] == ["doc_1"]
        
        # Verify vector database was called with correct parameters
        mock_vector_db.search_similar.assert_called_once()
        call_args = mock_vector_db.search_similar.call_args
        assert call_args[1]["min_similarity"] == 0.8
        assert call_args[1]["top_k"] == 10  # Should be doubled for better ranking
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_highlighting(self, search_engine, mock_vector_db, sample_vector_results):
        """Test semantic search with content highlighting."""
        mock_vector_db.search_similar.return_value = sample_vector_results
        
        query = SearchQuery(
            query="machine learning",
            highlight=True,
            top_k=3
        )
        
        response = await search_engine.semantic_search(query)
        
        # Verify highlighting was applied
        for result in response.results:
            assert result.highlighted_content is not None
            if "machine" in result.chunk.content.lower():
                assert "<mark>" in result.highlighted_content
    
    @pytest.mark.asyncio
    async def test_semantic_search_date_filtering(self, search_engine, mock_vector_db, sample_vector_results):
        """Test semantic search with date range filtering."""
        mock_vector_db.search_similar.return_value = sample_vector_results
        
        # Filter to only recent documents (last 3 days)
        date_from = datetime.now() - timedelta(days=3)
        
        query = SearchQuery(
            query="machine learning",
            date_from=date_from,
            top_k=10
        )
        
        response = await search_engine.semantic_search(query)
        
        # Should filter out chunk_3 which is 5 days old
        assert len(response.results) == 2
        for result in response.results:
            assert result.chunk.created_at >= date_from
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, search_engine, mock_vector_db, sample_vector_results):
        """Test hybrid search combining semantic and lexical matching."""
        mock_vector_db.search_similar.return_value = sample_vector_results
        
        query = SearchQuery(
            query="machine learning algorithms",
            search_type=SearchType.HYBRID,
            top_k=5
        )
        
        response = await search_engine.hybrid_search(query)
        
        # Verify
        assert response.search_type == SearchType.HYBRID
        assert len(response.results) <= 5
        assert response.search_time > 0
        
        # Should have called vector database twice (semantic + lexical base)
        assert mock_vector_db.search_similar.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_context_retrieval_for_rag(self, search_engine, mock_vector_db, sample_vector_results):
        """Test context retrieval optimized for RAG."""
        mock_vector_db.search_similar.return_value = sample_vector_results
        
        request = ContextRetrievalRequest(
            query="machine learning",
            max_tokens=1000,
            max_chunks=5,
            min_similarity=0.7
        )
        
        response = await search_engine.retrieve_context_for_rag(request)
        
        # Verify
        assert response.context is not None
        assert len(response.context) > 0
        assert response.total_tokens <= request.max_tokens
        assert len(response.chunks_used) <= request.max_chunks
        assert response.retrieval_time > 0
        
        # Verify context formatting
        assert "Source:" in response.context  # Should include source information
        assert "Section:" in response.context  # Should include section titles
    
    @pytest.mark.asyncio
    async def test_context_retrieval_token_limit(self, search_engine, mock_vector_db):
        """Test context retrieval respects token limits."""
        # Create large chunks that would exceed token limit
        large_results = [
            {
                "id": f"chunk_{i}",
                "content": "This is a very long chunk of text. " * 100,  # ~3400 chars ≈ 850 tokens
                "similarity_score": 0.9 - (i * 0.1),
                "metadata": {
                    "document_id": f"doc_{i}",
                    "chunk_index": i,
                    "start_index": 0,
                    "end_index": 3400,
                    "embedding_model": "test-model",
                    "created_at": datetime.now().isoformat(),
                    "section_title": f"Section {i}",
                    "language": "en"
                }
            }
            for i in range(10)
        ]
        
        mock_vector_db.search_similar.return_value = large_results
        
        request = ContextRetrievalRequest(
            query="test query",
            max_tokens=2000,  # Should fit about 2-3 chunks
            max_chunks=10
        )
        
        response = await search_engine.retrieve_context_for_rag(request)
        
        # Verify token limit is respected
        assert response.total_tokens <= request.max_tokens
        assert response.truncated  # Should be truncated due to token limit
    
    @pytest.mark.asyncio
    async def test_search_suggestions(self, search_engine, mock_vector_db):
        """Test search suggestions functionality."""
        suggestions = await search_engine.get_search_suggestions("machine", max_suggestions=5)
        
        assert len(suggestions) <= 5
        for suggestion in suggestions:
            assert "machine" in suggestion.suggestion.lower()
            assert suggestion.frequency > 0
    
    @pytest.mark.asyncio
    async def test_search_stats(self, search_engine, mock_vector_db, sample_vector_results):
        """Test search statistics tracking."""
        # Perform some searches to generate stats
        mock_vector_db.search_similar.return_value = sample_vector_results
        
        query = SearchQuery(query="test query", top_k=5)
        
        await search_engine.semantic_search(query)
        await search_engine.hybrid_search(query)
        
        stats = await search_engine.get_search_stats()
        
        # Verify stats (hybrid search calls semantic search internally, so we get 3 total)
        assert stats["total_searches"] == 3
        assert stats["avg_search_time"] > 0
        assert SearchType.SEMANTIC in stats["search_types_distribution"]
        assert SearchType.HYBRID in stats["search_types_distribution"]
        assert "vector_db_stats" in stats
        assert "embedding_service_stats" in stats
    
    @pytest.mark.asyncio
    async def test_result_ranking_content_boost(self, search_engine, mock_vector_db):
        """Test result ranking with content quality boosts."""
        # Create results with different content characteristics
        results_with_variations = [
            {
                "id": "chunk_exact",
                "content": "This document contains machine learning algorithms exactly.",
                "similarity_score": 0.8,
                "metadata": {
                    "document_id": "doc_1",
                    "chunk_index": 0,
                    "start_index": 0,
                    "end_index": 60,
                    "embedding_model": "test-model",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Machine Learning Algorithms",  # Title match
                    "language": "en"
                }
            },
            {
                "id": "chunk_similar",
                "content": "This text discusses ML and AI concepts in detail.",
                "similarity_score": 0.85,  # Higher base similarity
                "metadata": {
                    "document_id": "doc_2",
                    "chunk_index": 0,
                    "start_index": 0,
                    "end_index": 45,
                    "embedding_model": "test-model",
                    "created_at": datetime.now().isoformat(),
                    "language": "en"
                }
            }
        ]
        
        mock_vector_db.search_similar.return_value = results_with_variations
        
        query = SearchQuery(query="machine learning algorithms", top_k=5)
        response = await search_engine.semantic_search(query)
        
        # The first result should be boosted due to exact match and title match
        # even though it had lower base similarity
        assert response.results[0].chunk.id == "chunk_exact"
        assert response.results[0].similarity_score > 0.8  # Should be boosted
    
    @pytest.mark.asyncio
    async def test_lexical_scoring(self, search_engine):
        """Test lexical scoring algorithm."""
        # Test the private method directly
        query_terms = ["machine", "learning", "algorithms"]
        
        # Content with all terms
        content1 = "Machine learning algorithms are powerful tools for data analysis."
        score1 = search_engine._calculate_lexical_score(content1, query_terms)
        
        # Content with some terms
        content2 = "Machine learning is a subset of AI."
        score2 = search_engine._calculate_lexical_score(content2, query_terms)
        
        # Content with no terms
        content3 = "This is about something completely different."
        score3 = search_engine._calculate_lexical_score(content3, query_terms)
        
        # Verify scoring
        assert score1 > score2 > score3
        assert 0 <= score1 <= 1
        assert 0 <= score2 <= 1
        assert score3 == 0
    
    @pytest.mark.asyncio
    async def test_query_term_extraction(self, search_engine):
        """Test query term extraction."""
        # Test the private method directly
        query = "What are machine learning algorithms?"
        terms = search_engine._extract_query_terms(query)
        
        # Should extract meaningful terms and filter stop words
        assert "machine" in terms
        assert "learning" in terms
        assert "algorithms" in terms
        assert "what" not in terms  # Stop word
        assert "are" not in terms   # Stop word
    
    @pytest.mark.asyncio
    async def test_error_handling_vector_db_failure(self, search_engine, mock_vector_db):
        """Test error handling when vector database fails."""
        mock_vector_db.search_similar.side_effect = Exception("Database connection failed")
        
        query = SearchQuery(query="test query", top_k=5)
        
        with pytest.raises(SearchEngineError) as exc_info:
            await search_engine.semantic_search(query)
        
        assert "Semantic search failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_error_handling_embedding_failure(self, search_engine, mock_embedding_service):
        """Test error handling when embedding generation fails."""
        mock_embedding_service.generate_embedding.side_effect = Exception("Embedding model failed")
        
        query = SearchQuery(query="test query", top_k=5)
        
        with pytest.raises(SearchEngineError) as exc_info:
            await search_engine.semantic_search(query)
        
        assert "Semantic search failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_empty_results_handling(self, search_engine, mock_vector_db):
        """Test handling of empty search results."""
        mock_vector_db.search_similar.return_value = []
        
        query = SearchQuery(query="nonexistent query", top_k=5)
        response = await search_engine.semantic_search(query)
        
        assert len(response.results) == 0
        assert response.total_results == 0
        assert response.search_time > 0
    
    @pytest.mark.asyncio
    async def test_malformed_vector_results_handling(self, search_engine, mock_vector_db):
        """Test handling of malformed vector database results."""
        # Malformed results missing required fields
        malformed_results = [
            {
                "id": "chunk_1",
                "content": "Valid content",
                "similarity_score": 0.9,
                "metadata": {
                    "document_id": "doc_1",
                    # Missing required fields
                }
            },
            {
                # Missing content field
                "id": "chunk_2",
                "similarity_score": 0.8,
                "metadata": {}
            }
        ]
        
        mock_vector_db.search_similar.return_value = malformed_results
        
        query = SearchQuery(query="test query", top_k=5)
        response = await search_engine.semantic_search(query)
        
        # Should handle malformed results gracefully
        # Only valid results should be included
        assert len(response.results) <= len(malformed_results)
    
    def test_date_range_validation(self, search_engine):
        """Test date range validation logic."""
        now = datetime.now()
        past = now - timedelta(days=5)
        future = now + timedelta(days=5)
        
        # Test within range
        assert search_engine._is_in_date_range(now, past, future)
        
        # Test before range
        assert not search_engine._is_in_date_range(past - timedelta(days=1), past, future)
        
        # Test after range
        assert not search_engine._is_in_date_range(future + timedelta(days=1), past, future)
        
        # Test with None boundaries
        assert search_engine._is_in_date_range(now, None, None)
        assert search_engine._is_in_date_range(now, past, None)
        assert search_engine._is_in_date_range(now, None, future)


class TestSearchEnginePerformance:
    """Performance tests for SearchEngine."""
    
    @pytest.fixture
    def mock_vector_db(self):
        """Mock vector database service."""
        mock_db = Mock(spec=VectorDatabaseService)
        mock_db.search_similar = AsyncMock()
        mock_db.get_collection_stats = AsyncMock(return_value={
            "total_chunks": 100,
            "documents_count": 10,
            "embedding_models": ["test-model"],
            "languages": ["en", "fr"]
        })
        return mock_db
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        mock_service = Mock(spec=EmbeddingService)
        mock_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
        mock_service.get_service_stats = AsyncMock(return_value={
            "active_model": "test-model",
            "loaded_models": ["test-model"],
            "cache_stats": {"size": 10, "hit_rate": 0.8}
        })
        return mock_service
    
    @pytest.fixture
    def search_engine(self, mock_vector_db, mock_embedding_service):
        """Create SearchEngine instance with mocked dependencies."""
        return SearchEngine(
            vector_db=mock_vector_db,
            embedding_service=mock_embedding_service,
            max_context_tokens=4000,
            default_chunk_overlap=50
        )
    
    @pytest.fixture
    def large_result_set(self):
        """Generate large result set for performance testing."""
        return [
            {
                "id": f"chunk_{i}",
                "content": f"This is test content number {i} about various topics.",
                "similarity_score": 0.9 - (i * 0.001),  # Decreasing similarity
                "metadata": {
                    "document_id": f"doc_{i // 10}",
                    "chunk_index": i % 10,
                    "start_index": i * 100,
                    "end_index": (i + 1) * 100,
                    "embedding_model": "test-model",
                    "created_at": datetime.now().isoformat(),
                    "language": "en"
                }
            }
            for i in range(1000)  # Large dataset
        ]
    
    @pytest.mark.asyncio
    async def test_search_performance_large_dataset(self, search_engine, mock_vector_db, large_result_set):
        """Test search performance with large dataset."""
        mock_vector_db.search_similar.return_value = large_result_set
        
        query = SearchQuery(query="test query", top_k=50)
        
        start_time = asyncio.get_event_loop().time()
        response = await search_engine.semantic_search(query)
        end_time = asyncio.get_event_loop().time()
        
        search_time = end_time - start_time
        
        # Performance assertions
        assert search_time < 5.0  # Should complete within 5 seconds
        assert len(response.results) == 50
        assert response.search_time > 0
        
        # Results should be properly ranked
        for i in range(len(response.results) - 1):
            assert response.results[i].similarity_score >= response.results[i + 1].similarity_score
    
    @pytest.mark.asyncio
    async def test_context_retrieval_performance(self, search_engine, mock_vector_db, large_result_set):
        """Test context retrieval performance."""
        mock_vector_db.search_similar.return_value = large_result_set[:100]  # Reasonable subset
        
        request = ContextRetrievalRequest(
            query="test query",
            max_tokens=4000,
            max_chunks=20
        )
        
        start_time = asyncio.get_event_loop().time()
        response = await search_engine.retrieve_context_for_rag(request)
        end_time = asyncio.get_event_loop().time()
        
        retrieval_time = end_time - start_time
        
        # Performance assertions
        assert retrieval_time < 2.0  # Should complete within 2 seconds
        assert response.total_tokens <= request.max_tokens
        assert len(response.chunks_used) <= request.max_chunks


class TestSearchEngineIntegration:
    """Integration tests for SearchEngine with real-like scenarios."""
    
    @pytest.fixture
    def mock_vector_db(self):
        """Mock vector database service."""
        mock_db = Mock(spec=VectorDatabaseService)
        mock_db.search_similar = AsyncMock()
        mock_db.get_collection_stats = AsyncMock(return_value={
            "total_chunks": 100,
            "documents_count": 10,
            "embedding_models": ["test-model"],
            "languages": ["en", "fr"]
        })
        return mock_db
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        mock_service = Mock(spec=EmbeddingService)
        mock_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
        mock_service.get_service_stats = AsyncMock(return_value={
            "active_model": "test-model",
            "loaded_models": ["test-model"],
            "cache_stats": {"size": 10, "hit_rate": 0.8}
        })
        return mock_service
    
    @pytest.fixture
    def search_engine(self, mock_vector_db, mock_embedding_service):
        """Create SearchEngine instance with mocked dependencies."""
        return SearchEngine(
            vector_db=mock_vector_db,
            embedding_service=mock_embedding_service,
            max_context_tokens=4000,
            default_chunk_overlap=50
        )
    
    @pytest.mark.asyncio
    async def test_end_to_end_search_workflow(self, search_engine, mock_vector_db, mock_embedding_service):
        """Test complete search workflow from query to results."""
        # Setup realistic scenario
        mock_embedding_service.generate_embedding.return_value = [0.1] * 384
        
        realistic_results = [
            {
                "id": "chunk_intro",
                "content": "Introduction to machine learning: Machine learning is a method of data analysis that automates analytical model building.",
                "similarity_score": 0.92,
                "metadata": {
                    "document_id": "ml_guide",
                    "chunk_index": 0,
                    "start_index": 0,
                    "end_index": 120,
                    "embedding_model": "all-minilm-l6-v2",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Introduction",
                    "page_number": 1,
                    "language": "en",
                    "token_count": 25
                }
            },
            {
                "id": "chunk_algorithms",
                "content": "Common machine learning algorithms include linear regression, decision trees, random forests, and neural networks.",
                "similarity_score": 0.88,
                "metadata": {
                    "document_id": "ml_guide",
                    "chunk_index": 5,
                    "start_index": 500,
                    "end_index": 615,
                    "embedding_model": "all-minilm-l6-v2",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Algorithms",
                    "page_number": 3,
                    "language": "en",
                    "token_count": 22
                }
            }
        ]
        
        mock_vector_db.search_similar.return_value = realistic_results
        
        # Test semantic search
        query = SearchQuery(
            query="What are machine learning algorithms?",
            search_type=SearchType.SEMANTIC,
            top_k=10,
            min_similarity=0.7,
            highlight=True
        )
        
        response = await search_engine.semantic_search(query)
        
        # Verify complete workflow
        assert len(response.results) == 2
        assert response.results[0].similarity_score > response.results[1].similarity_score
        assert all(result.highlighted_content is not None for result in response.results)
        assert all(result.rank is not None for result in response.results)
        
        # Test context retrieval
        context_request = ContextRetrievalRequest(
            query="machine learning algorithms",
            max_tokens=1000,
            max_chunks=5
        )
        
        context_response = await search_engine.retrieve_context_for_rag(context_request)
        
        # Verify context is properly formatted
        assert "Introduction" in context_response.context
        assert "Algorithms" in context_response.context
        assert "Source:" in context_response.context
        assert len(context_response.chunks_used) <= 2
        assert context_response.total_tokens <= 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])