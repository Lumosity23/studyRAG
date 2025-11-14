"""
Unit tests for the EmbeddingService class.

Tests cover model management, caching, batch processing, and error handling.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any
import numpy as np

from app.services.embedding_service import (
    EmbeddingService,
    EmbeddingCache,
    EmbeddingRequest,
    EmbeddingResponse,
    get_embedding_service,
    initialize_embedding_service
)
from app.models.config import EmbeddingModelInfo, ModelStatus
from app.core.exceptions import (
    EmbeddingServiceError,
    ModelNotFoundError,
    ModelLoadError
)


class TestEmbeddingCache:
    """Test cases for EmbeddingCache."""
    
    def test_cache_initialization(self):
        """Test cache initialization with default parameters."""
        cache = EmbeddingCache()
        assert cache.max_size == 10000
        assert cache.ttl.total_seconds() == 24 * 3600  # 24 hours
        assert len(cache._cache) == 0
    
    def test_cache_initialization_custom(self):
        """Test cache initialization with custom parameters."""
        cache = EmbeddingCache(max_size=5000, ttl_hours=12)
        assert cache.max_size == 5000
        assert cache.ttl.total_seconds() == 12 * 3600  # 12 hours
    
    def test_cache_put_and_get(self):
        """Test basic cache put and get operations."""
        cache = EmbeddingCache()
        text = "test text"
        model_key = "test-model"
        embedding = [0.1, 0.2, 0.3]
        
        # Put embedding in cache
        cache.put(text, model_key, embedding)
        
        # Get embedding from cache
        retrieved = cache.get(text, model_key)
        assert retrieved == embedding
    
    def test_cache_miss(self):
        """Test cache miss for non-existent entries."""
        cache = EmbeddingCache()
        
        # Try to get non-existent embedding
        result = cache.get("non-existent", "test-model")
        assert result is None
    
    def test_cache_different_models(self):
        """Test that cache distinguishes between different models."""
        cache = EmbeddingCache()
        text = "same text"
        embedding1 = [0.1, 0.2, 0.3]
        embedding2 = [0.4, 0.5, 0.6]
        
        # Store same text with different models
        cache.put(text, "model1", embedding1)
        cache.put(text, "model2", embedding2)
        
        # Verify different embeddings are returned
        assert cache.get(text, "model1") == embedding1
        assert cache.get(text, "model2") == embedding2
    
    def test_cache_eviction(self):
        """Test cache eviction when max size is reached."""
        cache = EmbeddingCache(max_size=2)
        
        # Fill cache to capacity
        cache.put("text1", "model", [0.1])
        cache.put("text2", "model", [0.2])
        
        # Add one more item (should evict oldest)
        cache.put("text3", "model", [0.3])
        
        # First item should be evicted
        assert cache.get("text1", "model") is None
        assert cache.get("text2", "model") == [0.2]
        assert cache.get("text3", "model") == [0.3]
    
    def test_cache_clear(self):
        """Test cache clearing."""
        cache = EmbeddingCache()
        
        # Add some items
        cache.put("text1", "model", [0.1])
        cache.put("text2", "model", [0.2])
        
        # Clear cache
        cache.clear()
        
        # Verify cache is empty
        assert cache.get("text1", "model") is None
        assert cache.get("text2", "model") is None
        assert len(cache._cache) == 0
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = EmbeddingCache(max_size=100)
        
        # Add some items
        cache.put("text1", "model", [0.1])
        cache.put("text2", "model", [0.2])
        
        stats = cache.get_stats()
        assert stats["size"] == 2
        assert stats["max_size"] == 100
        assert "hit_rate" in stats
        assert "ttl_hours" in stats


class TestEmbeddingService:
    """Test cases for EmbeddingService."""
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer for testing."""
        mock_model = Mock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3, 0.4])
        return mock_model
    
    @pytest.fixture
    def embedding_service(self):
        """Create EmbeddingService instance for testing."""
        return EmbeddingService(cache_size=100, cache_ttl_hours=1, max_workers=2)
    
    def test_service_initialization(self, embedding_service):
        """Test service initialization."""
        assert embedding_service.cache.max_size == 100
        assert embedding_service.default_batch_size == 32
        assert len(embedding_service._model_info) == len(EmbeddingService.DEFAULT_MODELS)
        assert embedding_service._active_model_key is None
    
    @pytest.mark.asyncio
    async def test_get_available_models(self, embedding_service):
        """Test getting available models."""
        models = await embedding_service.get_available_models()
        
        assert len(models) == len(EmbeddingService.DEFAULT_MODELS)
        assert all(isinstance(model, EmbeddingModelInfo) for model in models)
        assert all(model.status == ModelStatus.AVAILABLE for model in models)
    
    @pytest.mark.asyncio
    async def test_get_active_model_none(self, embedding_service):
        """Test getting active model when none is set."""
        active_model = await embedding_service.get_active_model()
        assert active_model is None
    
    @pytest.mark.asyncio
    async def test_load_model_not_found(self, embedding_service):
        """Test loading a non-existent model."""
        with pytest.raises(ModelNotFoundError):
            await embedding_service.load_model("non-existent-model")
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_load_model_success(self, mock_st_class, embedding_service, mock_sentence_transformer):
        """Test successful model loading."""
        mock_st_class.return_value = mock_sentence_transformer
        
        model_info = await embedding_service.load_model("all-minilm-l6-v2")
        
        assert model_info.key == "all-minilm-l6-v2"
        assert model_info.status == ModelStatus.AVAILABLE
        assert model_info.dimensions == 4  # From mock embedding
        assert model_info.load_time is not None
        assert "all-minilm-l6-v2" in embedding_service._models
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_load_model_failure(self, mock_st_class, embedding_service):
        """Test model loading failure."""
        mock_st_class.side_effect = Exception("Model loading failed")
        
        with pytest.raises(ModelLoadError):
            await embedding_service.load_model("all-minilm-l6-v2")
        
        # Check that model status is set to error
        model_info = embedding_service._model_info["all-minilm-l6-v2"]
        assert model_info.status == ModelStatus.ERROR
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_switch_model(self, mock_st_class, embedding_service, mock_sentence_transformer):
        """Test model switching."""
        mock_st_class.return_value = mock_sentence_transformer
        
        # Switch to a model
        model_info = await embedding_service.switch_model("all-minilm-l6-v2")
        
        assert embedding_service._active_model_key == "all-minilm-l6-v2"
        assert model_info.is_active is True
        
        # Verify other models are not active
        for key, info in embedding_service._model_info.items():
            if key != "all-minilm-l6-v2":
                assert info.is_active is False
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_generate_embedding(self, mock_st_class, embedding_service, mock_sentence_transformer):
        """Test single embedding generation."""
        mock_st_class.return_value = mock_sentence_transformer
        
        # Load model first
        await embedding_service.load_model("all-minilm-l6-v2")
        
        # Generate embedding
        embedding = await embedding_service.generate_embedding(
            "test text",
            model_key="all-minilm-l6-v2"
        )
        
        assert embedding == [0.1, 0.2, 0.3, 0.4]
        # Model should be called twice: once for dimensions during load, once for actual embedding
        assert mock_sentence_transformer.encode.call_count == 2
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_generate_embedding_with_cache(self, mock_st_class, embedding_service, mock_sentence_transformer):
        """Test embedding generation with caching."""
        mock_st_class.return_value = mock_sentence_transformer
        
        # Load model
        await embedding_service.load_model("all-minilm-l6-v2")
        
        text = "test text"
        model_key = "all-minilm-l6-v2"
        
        # Generate embedding first time
        embedding1 = await embedding_service.generate_embedding(text, model_key)
        
        # Generate same embedding second time (should use cache)
        embedding2 = await embedding_service.generate_embedding(text, model_key)
        
        assert embedding1 == embedding2
        # Model should be called twice: once for dimensions during load, once for first embedding
        # Second call should use cache
        assert mock_sentence_transformer.encode.call_count == 2
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_generate_embedding_auto_load_default(self, mock_st_class, embedding_service, mock_sentence_transformer):
        """Test embedding generation with automatic default model loading."""
        mock_st_class.return_value = mock_sentence_transformer
        
        # Generate embedding without explicitly loading model
        embedding = await embedding_service.generate_embedding("test text")
        
        # Should auto-load default model
        assert embedding_service._active_model_key == "all-minilm-l6-v2"
        assert embedding == [0.1, 0.2, 0.3, 0.4]
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_generate_embeddings_batch(self, mock_st_class, embedding_service, mock_sentence_transformer):
        """Test batch embedding generation."""
        # Mock batch encoding - first call for dimensions, second for batch
        mock_sentence_transformer.encode.side_effect = [
            np.array([0.1, 0.2, 0.3, 0.4]),  # For dimensions during load
            np.array([
                [0.1, 0.2, 0.3, 0.4],
                [0.5, 0.6, 0.7, 0.8],
                [0.9, 1.0, 1.1, 1.2]
            ])  # For batch processing
        ]
        mock_st_class.return_value = mock_sentence_transformer
        
        # Load model
        await embedding_service.load_model("all-minilm-l6-v2")
        
        texts = ["text1", "text2", "text3"]
        response = await embedding_service.generate_embeddings_batch(
            texts,
            model_key="all-minilm-l6-v2"
        )
        
        assert isinstance(response, EmbeddingResponse)
        assert len(response.embeddings) == 3
        assert response.model_key == "all-minilm-l6-v2"
        assert response.dimensions == 4
        assert response.processing_time > 0
        assert response.cached_count == 0  # First time, nothing cached
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_generate_embeddings_batch_with_cache(self, mock_st_class, embedding_service, mock_sentence_transformer):
        """Test batch embedding generation with partial caching."""
        mock_sentence_transformer.encode.side_effect = [
            np.array([0.1, 0.2, 0.3, 0.4]),  # For dimensions during load
            np.array([0.1, 0.2, 0.3, 0.4]),  # First call for single embedding
            np.array([[0.5, 0.6, 0.7, 0.8]])  # Second call for batch (only uncached)
        ]
        mock_st_class.return_value = mock_sentence_transformer
        
        # Load model
        await embedding_service.load_model("all-minilm-l6-v2")
        
        # Generate single embedding first (will be cached)
        await embedding_service.generate_embedding("text1", "all-minilm-l6-v2")
        
        # Generate batch including cached text
        texts = ["text1", "text2"]  # text1 should be cached
        response = await embedding_service.generate_embeddings_batch(
            texts,
            model_key="all-minilm-l6-v2"
        )
        
        assert len(response.embeddings) == 2
        assert response.cached_count == 1  # text1 was cached
        assert response.embeddings[0] == [0.1, 0.2, 0.3, 0.4]  # From cache
        assert response.embeddings[1] == [0.5, 0.6, 0.7, 0.8]  # Newly generated
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_benchmark_models(self, mock_st_class, embedding_service, mock_sentence_transformer):
        """Test model benchmarking."""
        mock_sentence_transformer.encode.return_value = np.array([
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8]
        ])
        mock_st_class.return_value = mock_sentence_transformer
        
        test_texts = ["text1", "text2"]
        model_keys = ["all-minilm-l6-v2"]
        
        results = await embedding_service.benchmark_models(test_texts, model_keys)
        
        assert "all-minilm-l6-v2" in results
        result = results["all-minilm-l6-v2"]
        
        assert "model_info" in result
        assert "load_time" in result
        assert "embedding_time" in result
        assert "throughput" in result
        assert "dimensions" in result
        assert result["test_count"] == 2
        
        # Check that performance score was updated
        model_info = embedding_service._model_info["all-minilm-l6-v2"]
        assert model_info.performance_score is not None
        assert model_info.benchmark_date is not None
    
    @pytest.mark.asyncio
    async def test_get_service_stats(self, embedding_service):
        """Test getting service statistics."""
        stats = await embedding_service.get_service_stats()
        
        assert "active_model" in stats
        assert "loaded_models" in stats
        assert "available_models" in stats
        assert "cache_stats" in stats
        assert "thread_pool_size" in stats
        
        assert stats["active_model"] is None  # No model loaded yet
        assert stats["loaded_models"] == []
        assert stats["available_models"] == len(EmbeddingService.DEFAULT_MODELS)
    
    @pytest.mark.asyncio
    async def test_cleanup(self, embedding_service):
        """Test service cleanup."""
        # Add some data to cache
        embedding_service.cache.put("test", "model", [0.1, 0.2])
        
        await embedding_service.cleanup()
        
        # Cache should be cleared
        assert len(embedding_service.cache._cache) == 0
        assert len(embedding_service._models) == 0


class TestEmbeddingServiceIntegration:
    """Integration tests for EmbeddingService."""
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_full_workflow(self, mock_st_class):
        """Test complete workflow from initialization to embedding generation."""
        # Mock model
        mock_model = Mock()
        mock_model.encode.side_effect = [
            np.array([0.1, 0.2, 0.3, 0.4]),  # Test embedding for dimensions
            np.array([[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]])  # Batch embeddings
        ]
        mock_st_class.return_value = mock_model
        
        # Initialize service
        service = EmbeddingService()
        
        # Switch to a model
        model_info = await service.switch_model("all-minilm-l6-v2")
        assert model_info.is_active is True
        
        # Generate batch embeddings
        texts = ["Hello world", "How are you?"]
        response = await service.generate_embeddings_batch(texts)
        
        assert len(response.embeddings) == 2
        assert response.model_key == "all-minilm-l6-v2"
        assert response.dimensions == 4
        
        # Get service stats
        stats = await service.get_service_stats()
        assert stats["active_model"] == "all-minilm-l6-v2"
        assert len(stats["loaded_models"]) == 1
        
        # Cleanup
        await service.cleanup()


class TestFactoryFunctions:
    """Test factory functions and dependency injection."""
    
    def test_get_embedding_service_singleton(self):
        """Test that get_embedding_service returns singleton."""
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        assert service1 is service2
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_initialize_embedding_service(self, mock_st_class):
        """Test embedding service initialization with default model."""
        mock_model = Mock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3, 0.4])
        mock_st_class.return_value = mock_model
        
        service = await initialize_embedding_service("all-minilm-l6-v2")
        
        assert service._active_model_key == "all-minilm-l6-v2"
        active_model = await service.get_active_model()
        assert active_model.is_active is True


class TestErrorHandling:
    """Test error handling in EmbeddingService."""
    
    @pytest.mark.asyncio
    async def test_generate_embedding_model_not_loaded(self):
        """Test error when trying to generate embedding with unloaded model."""
        service = EmbeddingService()
        
        with pytest.raises(ModelNotFoundError):
            await service.generate_embedding("test", model_key="non-existent")
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_generate_embedding_model_error(self, mock_st_class):
        """Test error handling during embedding generation."""
        mock_model = Mock()
        # First call succeeds (for dimensions), second fails (for actual embedding)
        mock_model.encode.side_effect = [
            np.array([0.1, 0.2, 0.3, 0.4]),  # Success for dimensions
            Exception("Encoding failed")      # Failure for actual embedding
        ]
        mock_st_class.return_value = mock_model
        
        service = EmbeddingService()
        await service.load_model("all-minilm-l6-v2")
        
        with pytest.raises(EmbeddingServiceError):
            await service.generate_embedding("test", model_key="all-minilm-l6-v2")
    
    @pytest.mark.asyncio
    @patch('app.services.embedding_service.SentenceTransformer')
    async def test_benchmark_model_error(self, mock_st_class):
        """Test error handling during model benchmarking."""
        mock_st_class.side_effect = Exception("Model loading failed")
        
        service = EmbeddingService()
        results = await service.benchmark_models(model_keys=["all-minilm-l6-v2"])
        
        assert "all-minilm-l6-v2" in results
        assert results["all-minilm-l6-v2"]["status"] == "failed"
        assert "error" in results["all-minilm-l6-v2"]


if __name__ == "__main__":
    pytest.main([__file__])