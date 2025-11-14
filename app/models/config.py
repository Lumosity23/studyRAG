"""Configuration-related data models."""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import Field, field_validator
from datetime import datetime

from .common import BaseModel, TimestampMixin


class ModelStatus(str, Enum):
    """Model availability status."""
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class ModelType(str, Enum):
    """Types of models."""
    EMBEDDING = "embedding"
    LLM = "llm"


class EmbeddingModelInfo(BaseModel):
    """Information about an embedding model."""
    
    key: str = Field(
        ...,
        description="Unique key identifier for the model"
    )
    
    name: str = Field(
        ...,
        description="Human-readable name of the model"
    )
    
    description: Optional[str] = Field(
        None,
        description="Description of the model and its capabilities"
    )
    
    dimensions: int = Field(
        ...,
        ge=1,
        description="Number of dimensions in the embedding vectors"
    )
    
    model_size: str = Field(
        ...,
        description="Size of the model (e.g., '22MB', '420MB')"
    )
    
    max_sequence_length: int = Field(
        ...,
        ge=1,
        description="Maximum sequence length the model can handle"
    )
    
    supported_languages: List[str] = Field(
        default_factory=list,
        description="List of supported language codes"
    )
    
    is_multilingual: bool = Field(
        default=False,
        description="Whether the model supports multiple languages"
    )
    
    is_active: bool = Field(
        default=False,
        description="Whether this model is currently active"
    )
    
    status: ModelStatus = Field(
        default=ModelStatus.AVAILABLE,
        description="Current status of the model"
    )
    
    performance_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Performance score from benchmarking (0-1)"
    )
    
    benchmark_date: Optional[datetime] = Field(
        None,
        description="Date when the model was last benchmarked"
    )
    
    load_time: Optional[float] = Field(
        None,
        ge=0.0,
        description="Time taken to load the model in seconds"
    )
    
    memory_usage: Optional[int] = Field(
        None,
        ge=0,
        description="Memory usage in bytes when loaded"
    )
    
    @field_validator("key")
    @classmethod
    def validate_key(cls, v):
        """Validate model key format."""
        if not v or v.isspace():
            raise ValueError("Model key cannot be empty")
        # Key should be alphanumeric with hyphens/underscores
        if not all(c.isalnum() or c in '-_' for c in v):
            raise ValueError("Model key can only contain alphanumeric characters, hyphens, and underscores")
        return v.lower()
    
    @property
    def memory_usage_mb(self) -> Optional[float]:
        """Get memory usage in megabytes."""
        if self.memory_usage is None:
            return None
        return self.memory_usage / (1024 * 1024)
    
    def to_summary(self) -> Dict[str, Any]:
        """Get a summary representation of the model."""
        return {
            "key": self.key,
            "name": self.name,
            "dimensions": self.dimensions,
            "model_size": self.model_size,
            "is_active": self.is_active,
            "status": self.status,
            "performance_score": self.performance_score,
            "is_multilingual": self.is_multilingual,
            "supported_languages": self.supported_languages[:5]  # Limit for summary
        }


class OllamaModelInfo(BaseModel):
    """Information about an Ollama model."""
    
    name: str = Field(
        ...,
        description="Name of the Ollama model"
    )
    
    display_name: Optional[str] = Field(
        None,
        description="Human-readable display name"
    )
    
    description: Optional[str] = Field(
        None,
        description="Description of the model"
    )
    
    size: str = Field(
        ...,
        description="Size of the model (e.g., '7B', '13B', '70B')"
    )
    
    family: Optional[str] = Field(
        None,
        description="Model family (e.g., 'llama', 'mistral', 'codellama')"
    )
    
    parameter_count: Optional[str] = Field(
        None,
        description="Number of parameters (e.g., '7B', '13B')"
    )
    
    quantization: Optional[str] = Field(
        None,
        description="Quantization level (e.g., 'Q4_0', 'Q8_0')"
    )
    
    is_available: bool = Field(
        default=False,
        description="Whether the model is available locally"
    )
    
    is_active: bool = Field(
        default=False,
        description="Whether this model is currently active"
    )
    
    status: ModelStatus = Field(
        default=ModelStatus.UNAVAILABLE,
        description="Current status of the model"
    )
    
    download_progress: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Download progress (0-1) if model is being downloaded"
    )
    
    file_size: Optional[int] = Field(
        None,
        ge=0,
        description="File size in bytes"
    )
    
    modified_at: Optional[datetime] = Field(
        None,
        description="When the model was last modified"
    )
    
    performance_metrics: Optional[Dict[str, float]] = Field(
        None,
        description="Performance metrics (tokens/sec, etc.)"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate model name format."""
        if not v or v.isspace():
            raise ValueError("Model name cannot be empty")
        return v.strip()
    
    @property
    def file_size_gb(self) -> Optional[float]:
        """Get file size in gigabytes."""
        if self.file_size is None:
            return None
        return self.file_size / (1024 ** 3)
    
    def to_summary(self) -> Dict[str, Any]:
        """Get a summary representation of the model."""
        return {
            "name": self.name,
            "display_name": self.display_name or self.name,
            "size": self.size,
            "family": self.family,
            "is_available": self.is_available,
            "is_active": self.is_active,
            "status": self.status,
            "file_size_gb": self.file_size_gb
        }


class ModelSwitchRequest(BaseModel):
    """Request model for switching models."""
    
    model_type: ModelType = Field(..., description="Type of model to switch")
    model_key: str = Field(..., description="Key/name of the model to switch to")
    force_reload: bool = Field(default=False, description="Whether to force reload the model")


class ModelSwitchResponse(BaseModel):
    """Response model for model switching."""
    
    success: bool = Field(..., description="Whether the switch was successful")
    model_type: ModelType = Field(..., description="Type of model that was switched")
    previous_model: str = Field(..., description="Previous model key/name")
    new_model: str = Field(..., description="New model key/name")
    switch_time: float = Field(..., description="Time taken to switch models in seconds")
    message: str = Field(..., description="Status message")


class BenchmarkRequest(BaseModel):
    """Request model for benchmarking models."""
    
    model_type: ModelType = Field(..., description="Type of models to benchmark")
    model_keys: Optional[List[str]] = Field(
        None,
        description="Specific models to benchmark (all if not specified)"
    )
    test_queries: Optional[List[str]] = Field(
        None,
        description="Custom test queries for benchmarking"
    )
    iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of iterations for each test"
    )


class BenchmarkResult(BaseModel):
    """Result of a single benchmark test."""
    
    model_key: str = Field(..., description="Model that was benchmarked")
    test_name: str = Field(..., description="Name of the test")
    avg_time: float = Field(..., description="Average execution time in seconds")
    min_time: float = Field(..., description="Minimum execution time in seconds")
    max_time: float = Field(..., description="Maximum execution time in seconds")
    throughput: Optional[float] = Field(None, description="Throughput (items/second)")
    accuracy_score: Optional[float] = Field(None, description="Accuracy score (0-1)")
    memory_usage: Optional[int] = Field(None, description="Memory usage in bytes")


class BenchmarkResponse(BaseModel):
    """Response model for benchmarking."""
    
    benchmark_id: str = Field(..., description="Unique ID for this benchmark run")
    model_type: ModelType = Field(..., description="Type of models benchmarked")
    results: List[BenchmarkResult] = Field(..., description="Benchmark results")
    total_time: float = Field(..., description="Total benchmarking time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Benchmark timestamp")
    
    @property
    def best_model(self) -> Optional[str]:
        """Get the best performing model based on average time."""
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.avg_time).model_key


class SystemConfiguration(TimestampMixin):
    """System configuration model."""
    
    embedding_model: str = Field(..., description="Currently active embedding model")
    ollama_model: str = Field(..., description="Currently active Ollama model")
    chunk_size: int = Field(..., description="Default chunk size for document processing")
    chunk_overlap: int = Field(..., description="Default chunk overlap")
    max_context_tokens: int = Field(..., description="Maximum context tokens for RAG")
    default_top_k: int = Field(..., description="Default number of search results")
    min_similarity_score: float = Field(..., description="Default minimum similarity score")
    
    
class ConfigurationUpdateRequest(BaseModel):
    """Request model for updating system configuration."""
    
    embedding_model: Optional[str] = Field(None, description="Embedding model to set as active")
    ollama_model: Optional[str] = Field(None, description="Ollama model to set as active")
    chunk_size: Optional[int] = Field(None, ge=100, le=5000, description="Chunk size")
    chunk_overlap: Optional[int] = Field(None, ge=0, le=1000, description="Chunk overlap")
    max_context_tokens: Optional[int] = Field(None, ge=100, le=8000, description="Max context tokens")
    default_top_k: Optional[int] = Field(None, ge=1, le=100, description="Default top K")
    min_similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Min similarity score")


class HealthCheckResponse(BaseModel):
    """Response model for health checks."""
    
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    services: Dict[str, Dict[str, Any]] = Field(..., description="Status of individual services")
    version: str = Field(..., description="Application version")
    uptime: float = Field(..., description="System uptime in seconds")