"""Tests for configuration management API endpoints."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.models.config import (
    EmbeddingModelInfo,
    ModelStatus,
    ModelType,
    ModelSwitchRequest,
    BenchmarkRequest,
    ConfigurationUpdateRequest
)
from app.services.embedding_service import EmbeddingService
from app.services.ollama_client import OllamaClient, OllamaModelInfo

# Base API path for config endpoints
CONFIG_API_BASE = "/api/v1/config"


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_embedding_service():
    """Create mock embedding service."""
    service = AsyncMock(spec=EmbeddingService)
    
    # Mock available models
    service.get_available_models.return_value = [
        EmbeddingModelInfo(
            key="all-minilm-l6-v2",
            name="All-MiniLM-L6-v2",
            description="Lightweight multilingual model",
            dimensions=384,
            model_size="80MB",
            max_sequence_length=256,
            supported_languages=["en", "fr", "de"],
            is_multilingual=True,
            is_active=True,
            status=ModelStatus.AVAILABLE,
            performance_score=0.85
        ),
        EmbeddingModelInfo(
            key="all-mpnet-base-v2",
            name="All-MPNet-base-v2",
            description="High-performance English model",
            dimensions=768,
            model_size="420MB",
            max_sequence_length=384,
            supported_languages=["en"],
            is_multilingual=False,
            is_active=False,
            status=ModelStatus.AVAILABLE,
            performance_score=0.92
        )
    ]
    
    # Mock active model
    service.get_active_model.return_value = EmbeddingModelInfo(
        key="all-minilm-l6-v2",
        name="All-MiniLM-L6-v2",
        description="Lightweight multilingual model",
        dimensions=384,
        model_size="80MB",
        max_sequence_length=256,
        supported_languages=["en", "fr", "de"],
        is_multilingual=True,
        is_active=True,
        status=ModelStatus.AVAILABLE,
        performance_score=0.85
    )
    
    # Mock model switching
    service.switch_model.return_value = EmbeddingModelInfo(
        key="all-mpnet-base-v2",
        name="All-MPNet-base-v2",
        description="High-performance English model",
        dimensions=768,
        model_size="420MB",
        max_sequence_length=384,
        supported_languages=["en"],
        is_multilingual=False,
        is_active=True,
        status=ModelStatus.AVAILABLE
    )
    
    # Mock benchmarking
    service.benchmark_models.return_value = {
        "all-minilm-l6-v2": {
            "model_info": {"key": "all-minilm-l6-v2", "performance_score": 0.85},
            "load_time": 2.5,
            "embedding_time": 0.8,
            "avg_time_per_text": 0.16,
            "throughput": 6.25,
            "dimensions": 384,
            "test_count": 5
        },
        "all-mpnet-base-v2": {
            "model_info": {"key": "all-mpnet-base-v2", "performance_score": 0.92},
            "load_time": 5.2,
            "embedding_time": 1.2,
            "avg_time_per_text": 0.24,
            "throughput": 4.17,
            "dimensions": 768,
            "test_count": 5
        }
    }
    
    return service


@pytest.fixture
def mock_ollama_client():
    """Create mock Ollama client."""
    client = AsyncMock(spec=OllamaClient)
    
    # Mock available models
    client.list_models.return_value = [
        OllamaModelInfo(
            name="llama2:7b",
            size="3.8GB",
            digest="sha256:abc123",
            modified_at=datetime.now(),
            details={"parameter_size": "7B", "quantization_level": "Q4_0"}
        ),
        OllamaModelInfo(
            name="mistral:7b",
            size="4.1GB", 
            digest="sha256:def456",
            modified_at=datetime.now(),
            details={"parameter_size": "7B", "quantization_level": "Q4_0"}
        )
    ]
    
    # Mock model info
    client.get_model_info.return_value = OllamaModelInfo(
        name="llama2:7b",
        size="3.8GB",
        digest="sha256:abc123",
        modified_at=datetime.now(),
        details={"parameter_size": "7B", "quantization_level": "Q4_0"}
    )
    
    # Mock model validation
    client.validate_model.return_value = {
        "valid": True,
        "available": True,
        "model_info": {
            "name": "llama2:7b",
            "size": "3.8GB",
            "is_available": True
        },
        "test_successful": True
    }
    
    # Mock generation for benchmarking
    async def mock_generate(model, prompt, **kwargs):
        yield {"response": "Test response", "done": True}
    
    client.generate = mock_generate
    
    return client


class TestEmbeddingModelsEndpoints:
    """Test embedding models endpoints."""
    
    @patch('app.api.endpoints.config.get_embedding_service')
    def test_get_embedding_models(self, mock_get_service, client, mock_embedding_service):
        """Test getting available embedding models."""
        mock_get_service.return_value = mock_embedding_service
        
        response = client.get("/api/v1/config/models/embeddings")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["key"] == "all-minilm-l6-v2"
        assert data[0]["is_active"] is True
        assert data[1]["key"] == "all-mpnet-base-v2"
        assert data[1]["is_active"] is False
    
    @patch('app.api.endpoints.config.get_embedding_service')
    def test_get_active_embedding_model(self, mock_get_service, client, mock_embedding_service):
        """Test getting active embedding model."""
        mock_get_service.return_value = mock_embedding_service
        
        response = client.get("/api/v1/config/models/embeddings/active")
        
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "all-minilm-l6-v2"
        assert data["is_active"] is True
    
    @patch('app.api.endpoints.config.get_embedding_service')
    def test_get_active_embedding_model_none(self, mock_get_service, client):
        """Test getting active embedding model when none is active."""
        mock_service = AsyncMock()
        mock_service.get_active_model.return_value = None
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/config/models/embeddings/active")
        
        assert response.status_code == 200
        assert response.json() is None


class TestOllamaModelsEndpoints:
    """Test Ollama models endpoints."""
    
    @patch('app.api.endpoints.config.get_ollama_client')
    @patch('app.api.endpoints.config.config_service')
    def test_get_ollama_models(self, mock_config_service, mock_get_client, client, mock_ollama_client):
        """Test getting available Ollama models."""
        mock_get_client.return_value = mock_ollama_client
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.ollama_model = "llama2:7b"
        mock_config_service.get_system_config.return_value = mock_config
        
        response = client.get("/api/v1/config/models/ollama")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "llama2:7b"
        assert data[0]["is_active"] is True
        assert data[1]["name"] == "mistral:7b"
        assert data[1]["is_active"] is False
    
    @patch('app.api.endpoints.config.get_ollama_client')
    def test_get_ollama_models_force_refresh(self, mock_get_client, client, mock_ollama_client):
        """Test getting Ollama models with force refresh."""
        mock_get_client.return_value = mock_ollama_client
        
        response = client.get("/api/v1/config/models/ollama?force_refresh=true")
        
        assert response.status_code == 200
        mock_ollama_client.list_models.assert_called_with(force_refresh=True)
    
    @patch('app.api.endpoints.config.get_ollama_client')
    @patch('app.api.endpoints.config.config_service')
    def test_get_active_ollama_model(self, mock_config_service, mock_get_client, client, mock_ollama_client):
        """Test getting active Ollama model."""
        mock_get_client.return_value = mock_ollama_client
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.ollama_model = "llama2:7b"
        mock_config_service.get_system_config.return_value = mock_config
        
        response = client.get("/api/v1/config/models/ollama/active")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "llama2:7b"
        assert data["is_active"] is True
    
    @patch('app.api.endpoints.config.get_ollama_client')
    @patch('app.api.endpoints.config.config_service')
    def test_get_active_ollama_model_not_found(self, mock_config_service, mock_get_client, client):
        """Test getting active Ollama model when not found."""
        mock_client = AsyncMock()
        mock_client.get_model_info.return_value = None
        mock_get_client.return_value = mock_client
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.ollama_model = "nonexistent:model"
        mock_config_service.get_system_config.return_value = mock_config
        
        response = client.get("/api/v1/config/models/ollama/active")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "nonexistent:model"
        assert data["status"] == "unavailable"
        assert "error" in data


class TestModelSwitching:
    """Test model switching endpoints."""
    
    @patch('app.api.endpoints.config.get_embedding_service')
    @patch('app.api.endpoints.config.config_service')
    def test_switch_embedding_model_success(self, mock_config_service, mock_get_service, client, mock_embedding_service):
        """Test successful embedding model switch."""
        mock_get_service.return_value = mock_embedding_service
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.embedding_model = "all-minilm-l6-v2"
        mock_config_service.get_system_config.return_value = mock_config
        
        request_data = {
            "model_type": "embedding",
            "model_key": "all-mpnet-base-v2",
            "force_reload": False
        }
        
        response = client.post("/api/v1/config/models/switch", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["model_type"] == "embedding"
        assert data["previous_model"] == "all-minilm-l6-v2"
        assert data["new_model"] == "all-mpnet-base-v2"
        assert "switch_time" in data
        assert "message" in data
    
    @patch('app.api.endpoints.config.get_ollama_client')
    @patch('app.api.endpoints.config.config_service')
    def test_switch_ollama_model_success(self, mock_config_service, mock_get_client, client, mock_ollama_client):
        """Test successful Ollama model switch."""
        mock_get_client.return_value = mock_ollama_client
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.ollama_model = "llama2:7b"
        mock_config_service.get_system_config.return_value = mock_config
        
        request_data = {
            "model_type": "llm",
            "model_key": "mistral:7b",
            "force_reload": False
        }
        
        response = client.post("/api/v1/config/models/switch", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["model_type"] == "llm"
        assert data["previous_model"] == "llama2:7b"
        assert data["new_model"] == "mistral:7b"
    
    @patch('app.api.endpoints.config.get_embedding_service')
    @patch('app.api.endpoints.config.config_service')
    def test_switch_embedding_model_not_found(self, mock_config_service, mock_get_service, client):
        """Test embedding model switch with non-existent model."""
        mock_service = AsyncMock()
        mock_service.switch_model.side_effect = Exception("Model 'nonexistent' not found")
        mock_get_service.return_value = mock_service
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.embedding_model = "all-minilm-l6-v2"
        mock_config_service.get_system_config.return_value = mock_config
        
        request_data = {
            "model_type": "embedding",
            "model_key": "nonexistent",
            "force_reload": False
        }
        
        response = client.post("/api/v1/config/models/switch", json=request_data)
        
        assert response.status_code == 500
    
    @patch('app.api.endpoints.config.get_ollama_client')
    @patch('app.api.endpoints.config.config_service')
    def test_switch_ollama_model_invalid(self, mock_config_service, mock_get_client, client):
        """Test Ollama model switch with invalid model."""
        mock_client = AsyncMock()
        mock_client.validate_model.return_value = {
            "valid": False,
            "error": "Model not available"
        }
        mock_get_client.return_value = mock_client
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.ollama_model = "llama2:7b"
        mock_config_service.get_system_config.return_value = mock_config
        
        request_data = {
            "model_type": "llm",
            "model_key": "invalid:model",
            "force_reload": False
        }
        
        response = client.post("/api/v1/config/models/switch", json=request_data)
        
        assert response.status_code == 400
        assert "not valid" in response.json()["detail"]
    
    def test_switch_model_invalid_type(self, client):
        """Test model switch with invalid model type."""
        request_data = {
            "model_type": "invalid_type",
            "model_key": "some-model",
            "force_reload": False
        }
        
        response = client.post("/api/v1/config/models/switch", json=request_data)
        
        assert response.status_code == 422  # Validation error


class TestBenchmarking:
    """Test benchmarking endpoints."""
    
    @patch('app.api.endpoints.config.get_embedding_service')
    def test_start_embedding_benchmark(self, mock_get_service, client, mock_embedding_service):
        """Test starting embedding model benchmark."""
        mock_get_service.return_value = mock_embedding_service
        
        request_data = {
            "model_type": "embedding",
            "model_keys": ["all-minilm-l6-v2", "all-mpnet-base-v2"],
            "iterations": 3
        }
        
        response = client.post("/api/v1/config/benchmark", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "benchmark_id" in data
        assert data["status"] == "started"
        assert data["model_type"] == "embedding"
    
    @patch('app.api.endpoints.config.get_ollama_client')
    def test_start_ollama_benchmark(self, mock_get_client, client, mock_ollama_client):
        """Test starting Ollama model benchmark."""
        mock_get_client.return_value = mock_ollama_client
        
        request_data = {
            "model_type": "llm",
            "model_keys": ["llama2:7b"],
            "test_queries": ["Test query"],
            "iterations": 2
        }
        
        response = client.post("/api/v1/config/benchmark", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "benchmark_id" in data
        assert data["status"] == "started"
        assert data["model_type"] == "llm"
    
    def test_start_benchmark_invalid_type(self, client):
        """Test starting benchmark with invalid model type."""
        request_data = {
            "model_type": "invalid_type",
            "iterations": 1
        }
        
        response = client.post("/api/v1/config/benchmark", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.endpoints.config.config_service')
    def test_get_benchmark_status_found(self, mock_config_service, client):
        """Test getting benchmark status for existing benchmark."""
        benchmark_id = "benchmark_123_embedding"
        
        # Mock benchmark task
        mock_config_service._benchmark_tasks = {
            benchmark_id: {
                "id": benchmark_id,
                "status": "completed",
                "model_type": "embedding",
                "started_at": datetime.now(),
                "progress": 1.0,
                "results": {"test": "results"},
                "error": None,
                "completed_at": datetime.now()
            }
        }
        
        response = client.get(f"/api/v1/config/benchmark/{benchmark_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["benchmark_id"] == benchmark_id
        assert data["status"] == "completed"
        assert data["progress"] == 1.0
        assert data["results"] == {"test": "results"}
    
    @patch('app.api.endpoints.config.config_service')
    def test_get_benchmark_status_not_found(self, mock_config_service, client):
        """Test getting benchmark status for non-existent benchmark."""
        mock_config_service._benchmark_tasks = {}
        
        response = client.get("/api/v1/config/benchmark/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestSystemConfiguration:
    """Test system configuration endpoints."""
    
    @patch('app.api.endpoints.config.config_service')
    def test_get_system_configuration(self, mock_config_service, client):
        """Test getting system configuration."""
        mock_config = MagicMock()
        mock_config.embedding_model = "all-minilm-l6-v2"
        mock_config.ollama_model = "llama2:7b"
        mock_config.chunk_size = 1000
        mock_config.chunk_overlap = 200
        mock_config_service.get_system_config.return_value = mock_config
        
        response = client.get("/api/v1/config/system")
        
        assert response.status_code == 200
        # Response will be the mock object, which is fine for testing
    
    @patch('app.api.endpoints.config.config_service')
    def test_update_system_configuration(self, mock_config_service, client):
        """Test updating system configuration."""
        mock_config = MagicMock()
        mock_config_service.update_system_config.return_value = mock_config
        
        update_data = {
            "chunk_size": 1200,
            "chunk_overlap": 250,
            "default_top_k": 15
        }
        
        response = client.put("/api/v1/config/system", json=update_data)
        
        assert response.status_code == 200
        mock_config_service.update_system_config.assert_called_once()
    
    def test_update_system_configuration_invalid_data(self, client):
        """Test updating system configuration with invalid data."""
        update_data = {
            "chunk_size": -100,  # Invalid negative value
            "min_similarity_score": 1.5  # Invalid value > 1.0
        }
        
        response = client.put("/api/v1/config/system", json=update_data)
        
        assert response.status_code == 422  # Validation error


class TestErrorHandling:
    """Test error handling in configuration endpoints."""
    
    @patch('app.api.endpoints.config.get_embedding_service')
    def test_embedding_service_error(self, mock_get_service, client):
        """Test handling of embedding service errors."""
        mock_service = AsyncMock()
        mock_service.get_available_models.side_effect = Exception("Service error")
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/config/models/embeddings")
        
        assert response.status_code == 500
        assert "Failed to retrieve embedding models" in response.json()["detail"]
    
    @patch('app.api.endpoints.config.get_ollama_client')
    def test_ollama_client_error(self, mock_get_client, client):
        """Test handling of Ollama client errors."""
        mock_client = AsyncMock()
        mock_client.list_models.side_effect = Exception("Connection error")
        mock_get_client.return_value = mock_client
        
        response = client.get("/api/v1/config/models/ollama")
        
        assert response.status_code == 500
        assert "Failed to retrieve Ollama models" in response.json()["detail"]


@pytest.mark.asyncio
class TestAsyncBenchmarkTasks:
    """Test async benchmark task functions."""
    
    async def test_embedding_benchmark_task(self, mock_embedding_service):
        """Test embedding benchmark background task."""
        from app.api.endpoints.config import _run_embedding_benchmark, config_service
        
        benchmark_id = "test_benchmark_embedding"
        request = BenchmarkRequest(
            model_type=ModelType.EMBEDDING,
            model_keys=["all-minilm-l6-v2"],
            iterations=1
        )
        
        # Initialize task
        config_service._benchmark_tasks[benchmark_id] = {
            "id": benchmark_id,
            "status": "started",
            "model_type": ModelType.EMBEDDING,
            "started_at": datetime.now(),
            "progress": 0.0,
            "results": None,
            "error": None
        }
        
        # Run benchmark task
        await _run_embedding_benchmark(benchmark_id, request, mock_embedding_service)
        
        # Check results
        task_info = config_service._benchmark_tasks[benchmark_id]
        assert task_info["status"] == "completed"
        assert task_info["progress"] == 1.0
        assert task_info["results"] is not None
    
    async def test_ollama_benchmark_task(self, mock_ollama_client):
        """Test Ollama benchmark background task."""
        from app.api.endpoints.config import _run_ollama_benchmark, config_service
        
        benchmark_id = "test_benchmark_ollama"
        request = BenchmarkRequest(
            model_type=ModelType.LLM,
            model_keys=["llama2:7b"],
            test_queries=["Test query"],
            iterations=1
        )
        
        # Initialize task
        config_service._benchmark_tasks[benchmark_id] = {
            "id": benchmark_id,
            "status": "started",
            "model_type": ModelType.LLM,
            "started_at": datetime.now(),
            "progress": 0.0,
            "results": None,
            "error": None
        }
        
        # Run benchmark task
        await _run_ollama_benchmark(benchmark_id, request, mock_ollama_client)
        
        # Check results
        task_info = config_service._benchmark_tasks[benchmark_id]
        assert task_info["status"] == "completed"
        assert task_info["progress"] == 1.0
        assert task_info["results"] is not None