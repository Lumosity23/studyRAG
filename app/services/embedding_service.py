"""
Embedding service with multi-model support for StudyRAG application.

This service integrates the existing embedding system into the FastAPI application,
providing model management, caching, and batch processing capabilities.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor
import threading

from sentence_transformers import SentenceTransformer
import numpy as np
from pydantic import BaseModel

from ..models.config import EmbeddingModelInfo, ModelStatus
from ..core.exceptions import EmbeddingServiceError, ModelNotFoundError, ModelLoadError

logger = logging.getLogger(__name__)


class EmbeddingRequest(BaseModel):
    """Request model for embedding generation."""
    texts: List[str]
    model_key: Optional[str] = None
    batch_size: Optional[int] = None


class EmbeddingResponse(BaseModel):
    """Response model for embedding generation."""
    embeddings: List[List[float]]
    model_key: str
    dimensions: int
    processing_time: float
    cached_count: int = 0


class EmbeddingCache:
    """Thread-safe in-memory cache for embeddings with TTL support."""
    
    def __init__(self, max_size: int = 10000, ttl_hours: int = 24):
        """
        Initialize embedding cache.
        
        Args:
            max_size: Maximum number of cached embeddings
            ttl_hours: Time-to-live for cached embeddings in hours
        """
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self._cache: Dict[str, Tuple[List[float], datetime]] = {}
        self._access_times: Dict[str, datetime] = {}
        self._lock = threading.RLock()
        
        logger.info(f"Initialized embedding cache with max_size={max_size}, ttl={ttl_hours}h")
    
    def _generate_key(self, text: str, model_key: str) -> str:
        """Generate cache key for text and model combination."""
        content = f"{model_key}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, text: str, model_key: str) -> Optional[List[float]]:
        """Get embedding from cache if available and not expired."""
        cache_key = self._generate_key(text, model_key)
        
        with self._lock:
            if cache_key not in self._cache:
                return None
            
            embedding, created_at = self._cache[cache_key]
            
            # Check if expired
            if datetime.now() - created_at > self.ttl:
                del self._cache[cache_key]
                if cache_key in self._access_times:
                    del self._access_times[cache_key]
                return None
            
            # Update access time
            self._access_times[cache_key] = datetime.now()
            return embedding
    
    def put(self, text: str, model_key: str, embedding: List[float]):
        """Store embedding in cache with eviction if necessary."""
        cache_key = self._generate_key(text, model_key)
        now = datetime.now()
        
        with self._lock:
            # Evict expired entries
            self._evict_expired()
            
            # Evict oldest entries if cache is full
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                self._evict_oldest()
            
            self._cache[cache_key] = (embedding, now)
            self._access_times[cache_key] = now
    
    def _evict_expired(self):
        """Remove expired entries from cache."""
        now = datetime.now()
        expired_keys = []
        
        for key, (_, created_at) in self._cache.items():
            if now - created_at > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            if key in self._access_times:
                del self._access_times[key]
    
    def _evict_oldest(self):
        """Remove oldest accessed entry from cache."""
        if not self._access_times:
            return
        
        oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        del self._cache[oldest_key]
        del self._access_times[oldest_key]
    
    def clear(self):
        """Clear all cached embeddings."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": getattr(self, "_hit_count", 0) / max(getattr(self, "_total_requests", 1), 1),
                "ttl_hours": self.ttl.total_seconds() / 3600
            }


class EmbeddingService:
    """
    Service for managing embedding models and generating embeddings.
    
    Provides multi-model support, caching, batch processing, and model switching.
    """
    
    # Default embedding models configuration
    DEFAULT_MODELS = {
        "all-minilm-l6-v2": {
            "name": "All-MiniLM-L6-v2",
            "description": "Lightweight multilingual model (384 dimensions)",
            "model_size": "80MB",
            "max_sequence_length": 256,
            "supported_languages": ["en", "fr", "de", "es", "it", "pt", "nl"],
            "is_multilingual": True
        },
        "all-minilm-l12-v2": {
            "name": "All-MiniLM-L12-v2", 
            "description": "Balanced multilingual model (384 dimensions)",
            "model_size": "120MB",
            "max_sequence_length": 256,
            "supported_languages": ["en", "fr", "de", "es", "it", "pt", "nl"],
            "is_multilingual": True
        },
        "paraphrase-multilingual-minilm-l12-v2": {
            "name": "Paraphrase Multilingual MiniLM L12 v2",
            "description": "High-quality multilingual model (384 dimensions)",
            "model_size": "120MB",
            "max_sequence_length": 128,
            "supported_languages": ["en", "fr", "de", "es", "it", "pt", "nl", "pl", "ru"],
            "is_multilingual": True
        },
        "all-mpnet-base-v2": {
            "name": "All-MPNet-base-v2",
            "description": "High-performance English model (768 dimensions)",
            "model_size": "420MB",
            "max_sequence_length": 384,
            "supported_languages": ["en"],
            "is_multilingual": False
        },
        "sentence-camembert-large": {
            "name": "Sentence CamemBERT Large",
            "description": "French specialized model (1024 dimensions)",
            "model_size": "440MB",
            "max_sequence_length": 512,
            "supported_languages": ["fr"],
            "is_multilingual": False
        }
    }
    
    def __init__(
        self,
        cache_size: int = 10000,
        cache_ttl_hours: int = 24,
        max_workers: int = 4,
        default_batch_size: int = 32
    ):
        """
        Initialize embedding service.
        
        Args:
            cache_size: Maximum number of cached embeddings
            cache_ttl_hours: Cache time-to-live in hours
            max_workers: Maximum number of worker threads
            default_batch_size: Default batch size for processing
        """
        self.cache = EmbeddingCache(max_size=cache_size, ttl_hours=cache_ttl_hours)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.default_batch_size = default_batch_size
        
        # Model management
        self._models: Dict[str, SentenceTransformer] = {}
        self._model_info: Dict[str, EmbeddingModelInfo] = {}
        self._active_model_key: Optional[str] = None
        self._model_lock = threading.RLock()
        
        # Initialize model info
        self._initialize_model_info()
        
        logger.info(f"Initialized EmbeddingService with {len(self.DEFAULT_MODELS)} available models")
    
    def _initialize_model_info(self):
        """Initialize model information from defaults."""
        # Default dimensions for each model (will be updated when loaded)
        default_dimensions = {
            "all-minilm-l6-v2": 384,
            "all-minilm-l12-v2": 384,
            "paraphrase-multilingual-minilm-l12-v2": 384,
            "all-mpnet-base-v2": 768,
            "sentence-camembert-large": 1024
        }
        
        for key, config in self.DEFAULT_MODELS.items():
            self._model_info[key] = EmbeddingModelInfo(
                key=key,
                name=config["name"],
                description=config["description"],
                dimensions=default_dimensions.get(key, 384),  # Use known dimensions or default
                model_size=config["model_size"],
                max_sequence_length=config["max_sequence_length"],
                supported_languages=config["supported_languages"],
                is_multilingual=config["is_multilingual"],
                status=ModelStatus.AVAILABLE
            )
    
    async def get_available_models(self) -> List[EmbeddingModelInfo]:
        """Get list of available embedding models."""
        return list(self._model_info.values())
    
    async def get_active_model(self) -> Optional[EmbeddingModelInfo]:
        """Get currently active model information."""
        if self._active_model_key is None:
            return None
        return self._model_info.get(self._active_model_key)
    
    async def load_model(self, model_key: str, force_reload: bool = False) -> EmbeddingModelInfo:
        """
        Load an embedding model.
        
        Args:
            model_key: Key of the model to load
            force_reload: Whether to force reload if already loaded
            
        Returns:
            Model information
            
        Raises:
            ModelNotFoundError: If model key is not found
            ModelLoadError: If model fails to load
        """
        if model_key not in self._model_info:
            raise ModelNotFoundError(f"Model '{model_key}' not found")
        
        with self._model_lock:
            # Check if already loaded
            if model_key in self._models and not force_reload:
                logger.info(f"Model '{model_key}' already loaded")
                return self._model_info[model_key]
            
            model_info = self._model_info[model_key]
            model_info.status = ModelStatus.DOWNLOADING
            
            try:
                logger.info(f"Loading embedding model: {model_key}")
                start_time = time.time()
                
                # Load model in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                model = await loop.run_in_executor(
                    self.executor,
                    self._load_sentence_transformer,
                    model_key
                )
                
                load_time = time.time() - start_time
                
                # Get model dimensions
                test_embedding = await loop.run_in_executor(
                    self.executor,
                    lambda: model.encode("test", convert_to_numpy=True)
                )
                dimensions = len(test_embedding)
                
                # Store model and update info
                self._models[model_key] = model
                model_info.dimensions = dimensions
                model_info.load_time = load_time
                model_info.status = ModelStatus.AVAILABLE
                
                logger.info(f"Successfully loaded model '{model_key}' ({dimensions}D, {load_time:.2f}s)")
                return model_info
                
            except Exception as e:
                model_info.status = ModelStatus.ERROR
                logger.error(f"Failed to load model '{model_key}': {e}")
                raise ModelLoadError(f"Failed to load model '{model_key}': {e}")
    
    def _load_sentence_transformer(self, model_key: str) -> SentenceTransformer:
        """Load SentenceTransformer model (runs in thread pool)."""
        # Map our keys to actual model names
        model_name_map = {
            "all-minilm-l6-v2": "all-MiniLM-L6-v2",
            "all-minilm-l12-v2": "all-MiniLM-L12-v2",
            "paraphrase-multilingual-minilm-l12-v2": "paraphrase-multilingual-MiniLM-L12-v2",
            "all-mpnet-base-v2": "all-mpnet-base-v2",
            "sentence-camembert-large": "dangvantuan/sentence-camembert-large"
        }
        
        model_name = model_name_map.get(model_key, model_key)
        return SentenceTransformer(model_name)
    
    async def switch_model(self, model_key: str) -> EmbeddingModelInfo:
        """
        Switch to a different embedding model.
        
        Args:
            model_key: Key of the model to switch to
            
        Returns:
            New active model information
        """
        # Load the model if not already loaded
        model_info = await self.load_model(model_key)
        
        # Update active model
        old_active = self._active_model_key
        self._active_model_key = model_key
        
        # Update model status
        for key, info in self._model_info.items():
            info.is_active = (key == model_key)
        
        # Clear cache when switching models
        self.cache.clear()
        
        logger.info(f"Switched embedding model from '{old_active}' to '{model_key}'")
        return model_info
    
    async def generate_embedding(
        self,
        text: str,
        model_key: Optional[str] = None
    ) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            model_key: Model to use (uses active model if None)
            
        Returns:
            Embedding vector
        """
        # Use active model if none specified
        if model_key is None:
            model_key = self._active_model_key
            if model_key is None:
                # Load default model
                model_key = "all-minilm-l6-v2"
                await self.switch_model(model_key)
        
        # Check cache first
        cached_embedding = self.cache.get(text, model_key)
        if cached_embedding is not None:
            return cached_embedding
        
        # Ensure model is loaded
        if model_key not in self._models:
            await self.load_model(model_key)
        
        model = self._models[model_key]
        
        try:
            # Generate embedding in thread pool
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                self.executor,
                lambda: model.encode(text, convert_to_numpy=True)
            )
            
            embedding_list = embedding.tolist()
            
            # Cache the result
            self.cache.put(text, model_key, embedding_list)
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise EmbeddingServiceError(f"Failed to generate embedding: {e}")
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model_key: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> EmbeddingResponse:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to embed
            model_key: Model to use (uses active model if None)
            batch_size: Batch size for processing
            
        Returns:
            Embedding response with results and metadata
        """
        start_time = time.time()
        
        # Use active model if none specified
        if model_key is None:
            model_key = self._active_model_key
            if model_key is None:
                # Load default model
                model_key = "all-minilm-l6-v2"
                await self.switch_model(model_key)
        
        # Use default batch size if none specified
        if batch_size is None:
            batch_size = self.default_batch_size
        
        # Ensure model is loaded
        if model_key not in self._models:
            await self.load_model(model_key)
        
        model = self._models[model_key]
        model_info = self._model_info[model_key]
        
        # Check cache for existing embeddings
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        cached_count = 0
        
        for i, text in enumerate(texts):
            cached_embedding = self.cache.get(text, model_key)
            if cached_embedding is not None:
                embeddings.append(cached_embedding)
                cached_count += 1
            else:
                embeddings.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                loop = asyncio.get_event_loop()
                new_embeddings = await loop.run_in_executor(
                    self.executor,
                    lambda: model.encode(
                        uncached_texts,
                        convert_to_numpy=True,
                        batch_size=batch_size,
                        show_progress_bar=False
                    )
                )
                
                # Store results and cache them
                for i, (idx, embedding) in enumerate(zip(uncached_indices, new_embeddings)):
                    embedding_list = embedding.tolist()
                    embeddings[idx] = embedding_list
                    self.cache.put(uncached_texts[i], model_key, embedding_list)
                    
            except Exception as e:
                logger.error(f"Error in batch embedding generation: {e}")
                raise EmbeddingServiceError(f"Failed to generate batch embeddings: {e}")
        
        processing_time = time.time() - start_time
        
        return EmbeddingResponse(
            embeddings=embeddings,
            model_key=model_key,
            dimensions=model_info.dimensions,
            processing_time=processing_time,
            cached_count=cached_count
        )
    
    async def benchmark_models(
        self,
        test_texts: Optional[List[str]] = None,
        model_keys: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Benchmark embedding models for performance comparison.
        
        Args:
            test_texts: Custom test texts (uses defaults if None)
            model_keys: Models to benchmark (benchmarks all if None)
            
        Returns:
            Benchmark results for each model
        """
        if test_texts is None:
            test_texts = [
                "What are the technical specifications of the ESP32 microcontroller?",
                "How to implement machine learning algorithms in Python?",
                "Explain the architecture of neural networks and deep learning.",
                "Database design principles and normalization techniques.",
                "Web development with JavaScript and modern frameworks."
            ]
        
        if model_keys is None:
            model_keys = list(self.DEFAULT_MODELS.keys())
        
        results = {}
        
        for model_key in model_keys:
            try:
                logger.info(f"Benchmarking model: {model_key}")
                
                # Load model and measure load time
                load_start = time.time()
                model_info = await self.load_model(model_key)
                load_time = time.time() - load_start
                
                # Benchmark embedding generation
                embed_start = time.time()
                response = await self.generate_embeddings_batch(
                    test_texts,
                    model_key=model_key
                )
                embed_time = time.time() - embed_start
                
                # Calculate metrics
                throughput = len(test_texts) / embed_time
                avg_time_per_text = embed_time / len(test_texts)
                
                results[model_key] = {
                    "model_info": model_info.model_dump(),
                    "load_time": load_time,
                    "embedding_time": embed_time,
                    "avg_time_per_text": avg_time_per_text,
                    "throughput": throughput,
                    "dimensions": response.dimensions,
                    "test_count": len(test_texts)
                }
                
                # Update model performance score
                # Score based on speed and dimensions (higher dimensions = better quality)
                speed_score = min(1.0, 1.0 / max(avg_time_per_text, 0.001))
                dimension_score = min(1.0, response.dimensions / 1000.0)
                performance_score = (speed_score * 0.6) + (dimension_score * 0.4)
                
                model_info.performance_score = performance_score
                model_info.benchmark_date = datetime.now()
                
                logger.info(f"Benchmarked {model_key}: {throughput:.2f} texts/sec, score: {performance_score:.3f}")
                
            except Exception as e:
                logger.error(f"Failed to benchmark model {model_key}: {e}")
                results[model_key] = {
                    "error": str(e),
                    "status": "failed"
                }
        
        return results
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics and health information."""
        return {
            "active_model": self._active_model_key,
            "loaded_models": list(self._models.keys()),
            "available_models": len(self._model_info),
            "cache_stats": self.cache.get_stats(),
            "thread_pool_size": self.executor._max_workers
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up EmbeddingService")
        self.cache.clear()
        self.executor.shutdown(wait=True)
        self._models.clear()


# Factory function for dependency injection
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


async def initialize_embedding_service(
    default_model: str = "all-minilm-l6-v2"
) -> EmbeddingService:
    """
    Initialize embedding service with default model.
    
    Args:
        default_model: Default model to load
        
    Returns:
        Initialized embedding service
    """
    service = get_embedding_service()
    await service.switch_model(default_model)
    logger.info(f"Initialized embedding service with model: {default_model}")
    return service