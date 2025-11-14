"""Tests for configuration management API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.models.config import (
    EmbeddingModelInfo,
    ModelStatus,
    ModelType
)
from app.services.embedding_service import EmbeddingService
from app.services.ollama_client import OllamaClient, OllamaModelInfo


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
    
    return client


class TestConfigurationAPI:
    """Test configuration management API."""
    
    def test_get_embedding_models(self, client, mock_embedding_service):
        """Test getting available embedding models."""
        from app.core.dependencies import get_embedding_service
        
        # Override dependency
        app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service
        
        try:
            response = client.get("/api/v1/config/models/embeddings")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["key"] == "all-minilm-l6-v2"
            assert data[0]["is_active"] is True
            assert data[1]["key"] == "all-mpnet-base-v2"
            assert data[1]["is_active"] is False
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_get_active_embedding_model(self, client, mock_embedding_service):
        """Test getting active embedding model."""
        from app.core.dependencies import get_embedding_service
        
        # Override dependency
        app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service
        
        try:
            response = client.get("/api/v1/config/models/embeddings/active")
            
            assert response.status_code == 200
            data = response.json()
            assert data["key"] == "all-minilm-l6-v2"
            assert data["is_active"] is True
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_get_ollama_models(self, client, mock_ollama_client):
        """Test getting available Ollama models."""
        from app.core.dependencies import get_ollama_client
        from app.api.endpoints.config import config_service
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.ollama_model = "llama2:7b"
        config_service.get_system_config = AsyncMock(return_value=mock_config)
        
        # Override dependency
        app.dependency_overrides[get_ollama_client] = lambda: mock_ollama_client
        
        try:
            response = client.get("/api/v1/config/models/ollama")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            
            # Find active and inactive models
            active_models = [m for m in data if m["is_active"]]
            inactive_models = [m for m in data if not m["is_active"]]
            
            assert len(active_models) == 1
            assert len(inactive_models) == 1
            assert active_models[0]["name"] == "llama2:7b"
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_switch_embedding_model(self, client, mock_embedding_service):
        """Test switching embedding model."""
        from app.core.dependencies import get_embedding_service
        from app.api.endpoints.config import config_service
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.embedding_model = "all-minilm-l6-v2"
        config_service.get_system_config = AsyncMock(return_value=mock_config)
        
        # Mock model switching
        mock_embedding_service.switch_model.return_value = EmbeddingModelInfo(
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
        
        # Override dependency
        app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service
        
        try:
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
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_switch_ollama_model(self, client, mock_ollama_client):
        """Test switching Ollama model."""
        from app.core.dependencies import get_ollama_client
        from app.api.endpoints.config import config_service
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.ollama_model = "llama2:7b"
        config_service.get_system_config = AsyncMock(return_value=mock_config)
        
        # Mock model validation
        mock_ollama_client.validate_model.return_value = {
            "valid": True,
            "available": True,
            "test_successful": True
        }
        
        # Override dependency
        app.dependency_overrides[get_ollama_client] = lambda: mock_ollama_client
        
        try:
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
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_start_benchmark(self, client, mock_embedding_service):
        """Test starting benchmark."""
        from app.core.dependencies import get_embedding_service
        
        # Override dependency
        app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service
        
        try:
            request_data = {
                "model_type": "embedding",
                "model_keys": ["all-minilm-l6-v2"],
                "iterations": 1
            }
            
            response = client.post("/api/v1/config/benchmark", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "benchmark_id" in data
            assert data["status"] == "started"
            assert data["model_type"] == "embedding"
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_get_system_configuration(self, client):
        """Test getting system configuration."""
        from app.api.endpoints.config import config_service
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.embedding_model = "all-minilm-l6-v2"
        mock_config.ollama_model = "llama2:7b"
        mock_config.chunk_size = 1000
        mock_config.chunk_overlap = 200
        config_service.get_system_config = AsyncMock(return_value=mock_config)
        
        response = client.get("/api/v1/config/system")
        
        assert response.status_code == 200
    
    def test_update_system_configuration(self, client):
        """Test updating system configuration."""
        from app.api.endpoints.config import config_service
        
        # Mock system config with proper attributes
        mock_config = MagicMock()
        mock_config.embedding_model = "all-minilm-l6-v2"
        mock_config.ollama_model = "llama2:7b"
        mock_config.chunk_size = 1200
        mock_config.chunk_overlap = 250
        mock_config.default_top_k = 15
        mock_config.max_context_tokens = 4000
        mock_config.min_similarity_score = 0.5
        mock_config.created_at = datetime.now()
        mock_config.updated_at = datetime.now()
        config_service.update_system_config = AsyncMock(return_value=mock_config)
        
        update_data = {
            "chunk_size": 1200,
            "chunk_overlap": 250,
            "default_top_k": 15
        }
        
        response = client.put("/api/v1/config/system", json=update_data)
        
        assert response.status_code == 200
    
    def test_invalid_model_switch(self, client):
        """Test invalid model switch request."""
        request_data = {
            "model_type": "invalid_type",
            "model_key": "some-model"
        }
        
        response = client.post("/api/v1/config/models/switch", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_benchmark_request(self, client):
        """Test invalid benchmark request."""
        request_data = {
            "model_type": "embedding",
            "iterations": 0  # Invalid
        }
        
        response = client.post("/api/v1/config/benchmark", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_system_config_update(self, client):
        """Test invalid system configuration update."""
        update_data = {
            "chunk_size": -100,  # Invalid negative value
            "min_similarity_score": 1.5  # Invalid value > 1.0
        }
        
        response = client.put("/api/v1/config/system", json=update_data)
        
        assert response.status_code == 422  # Validation error