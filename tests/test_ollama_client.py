"""Tests for Ollama client wrapper."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json

from app.services.ollama_client import (
    OllamaClient, OllamaModelInfo, OllamaConnectionError, 
    OllamaModelError, OllamaGenerationError
)
from app.core.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.ollama_url = "http://localhost:11434"
    settings.OLLAMA_TIMEOUT = 30
    return settings


@pytest.fixture
def ollama_client(mock_settings):
    """Create Ollama client for testing."""
    return OllamaClient(mock_settings)


@pytest.fixture
def mock_session():
    """Mock aiohttp session."""
    session = AsyncMock()
    return session


class TestOllamaModelInfo:
    """Test OllamaModelInfo class."""
    
    def test_model_info_creation(self):
        """Test creating model info."""
        model = OllamaModelInfo(
            name="llama2",
            size="3.8GB",
            digest="sha256:abc123",
            modified_at=datetime.now()
        )
        
        assert model.name == "llama2"
        assert model.size == "3.8GB"
        assert model.is_available is True
    
    def test_model_info_unavailable(self):
        """Test model info without digest (unavailable)."""
        model = OllamaModelInfo(name="llama2")
        assert model.is_available is False
    
    def test_model_info_to_dict(self):
        """Test converting model info to dictionary."""
        now = datetime.now()
        model = OllamaModelInfo(
            name="llama2",
            size="3.8GB",
            digest="sha256:abc123",
            modified_at=now
        )
        
        result = model.to_dict()
        
        assert result["name"] == "llama2"
        assert result["size"] == "3.8GB"
        assert result["digest"] == "sha256:abc123"
        assert result["is_available"] is True
        assert result["modified_at"] == now.isoformat()


class TestOllamaClient:
    """Test OllamaClient class."""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, ollama_client):
        """Test client initialization."""
        assert ollama_client.base_url == "http://localhost:11434"
        assert ollama_client.timeout == 30
        assert ollama_client.session is None
    
    @pytest.mark.asyncio
    async def test_ensure_session(self, ollama_client):
        """Test session creation."""
        await ollama_client._ensure_session()
        assert ollama_client.session is not None
        
        # Clean up
        await ollama_client.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, ollama_client):
        """Test async context manager."""
        async with ollama_client as client:
            assert client.session is not None
        
        # Session should be closed after context
        assert ollama_client.session.closed
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_client, mock_session):
        """Test successful health check."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        ollama_client.session = mock_session
        
        result = await ollama_client.health_check()
        assert result is True
        
        mock_session.get.assert_called_once_with("http://localhost:11434/api/tags")
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama_client, mock_session):
        """Test failed health check."""
        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        ollama_client.session = mock_session
        
        result = await ollama_client.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_models_success(self, ollama_client, mock_session):
        """Test successful model listing."""
        # Mock response data
        mock_data = {
            "models": [
                {
                    "name": "llama2",
                    "size": "3.8GB",
                    "digest": "sha256:abc123",
                    "modified_at": "2024-01-01T12:00:00Z",
                    "details": {"family": "llama"}
                },
                {
                    "name": "codellama",
                    "size": "7.3GB",
                    "digest": "sha256:def456",
                    "modified_at": "2024-01-02T12:00:00Z"
                }
            ]
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_data
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        ollama_client.session = mock_session
        
        models = await ollama_client.list_models()
        
        assert len(models) == 2
        assert models[0].name == "llama2"
        assert models[0].size == "3.8GB"
        assert models[0].is_available is True
        assert models[1].name == "codellama"
    
    @pytest.mark.asyncio
    async def test_list_models_cache(self, ollama_client, mock_session):
        """Test model listing with cache."""
        # Mock response
        mock_data = {"models": [{"name": "llama2", "digest": "abc123"}]}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_data
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        ollama_client.session = mock_session
        
        # First call should hit the API
        models1 = await ollama_client.list_models()
        assert len(models1) == 1
        
        # Second call should use cache
        models2 = await ollama_client.list_models()
        assert len(models2) == 1
        
        # Should only call API once
        assert mock_session.get.call_count == 1
        
        # Force refresh should call API again
        models3 = await ollama_client.list_models(force_refresh=True)
        assert len(models3) == 1
        assert mock_session.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_list_models_error(self, ollama_client, mock_session):
        """Test model listing error."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        ollama_client.session = mock_session
        
        with pytest.raises(OllamaConnectionError) as exc_info:
            await ollama_client.list_models()
        
        assert "Failed to list models" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_model_exists(self, ollama_client):
        """Test model existence check."""
        # Mock list_models to return test models
        test_models = [
            OllamaModelInfo("llama2", digest="abc123"),
            OllamaModelInfo("codellama", digest="def456")
        ]
        
        with patch.object(ollama_client, 'list_models', return_value=test_models):
            assert await ollama_client.model_exists("llama2") is True
            assert await ollama_client.model_exists("nonexistent") is False
    
    @pytest.mark.asyncio
    async def test_generate_success(self, ollama_client, mock_session):
        """Test successful text generation."""
        # Mock model exists
        with patch.object(ollama_client, 'model_exists', return_value=True):
            # Mock response
            mock_data = {
                "response": "Hello! How can I help you?",
                "done": True,
                "context": [1, 2, 3],
                "total_duration": 1000000,
                "eval_count": 10
            }
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_data
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            ollama_client.session = mock_session
            
            # Test non-streaming generation
            responses = []
            async for response in ollama_client.generate(
                model="llama2",
                prompt="Hello",
                stream=False
            ):
                responses.append(response)
            
            assert len(responses) == 1
            assert responses[0]["response"] == "Hello! How can I help you?"
            assert responses[0]["done"] is True
    
    @pytest.mark.asyncio
    async def test_generate_model_not_found(self, ollama_client):
        """Test generation with non-existent model."""
        with patch.object(ollama_client, 'model_exists', return_value=False):
            with pytest.raises(OllamaModelError) as exc_info:
                async for _ in ollama_client.generate("nonexistent", "Hello"):
                    pass
            
            assert "not available locally" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_streaming(self, ollama_client, mock_session):
        """Test streaming text generation."""
        with patch.object(ollama_client, 'model_exists', return_value=True):
            # Mock streaming response
            stream_data = [
                b'{"response": "Hello", "done": false}\n',
                b'{"response": " there", "done": false}\n',
                b'{"response": "!", "done": true}\n'
            ]
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.content.__aiter__.return_value = stream_data
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            ollama_client.session = mock_session
            
            responses = []
            async for response in ollama_client.generate(
                model="llama2",
                prompt="Hello",
                stream=True
            ):
                responses.append(response)
            
            assert len(responses) == 3
            assert responses[0]["response"] == "Hello"
            assert responses[1]["response"] == " there"
            assert responses[2]["done"] is True
    
    @pytest.mark.asyncio
    async def test_chat_success(self, ollama_client, mock_session):
        """Test successful chat."""
        with patch.object(ollama_client, 'model_exists', return_value=True):
            mock_data = {
                "message": {"role": "assistant", "content": "Hello! How can I help?"},
                "done": True
            }
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_data
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            ollama_client.session = mock_session
            
            messages = [{"role": "user", "content": "Hello"}]
            
            responses = []
            async for response in ollama_client.chat("llama2", messages):
                responses.append(response)
            
            assert len(responses) == 1
            assert responses[0]["message"]["content"] == "Hello! How can I help?"
    
    @pytest.mark.asyncio
    async def test_pull_model(self, ollama_client, mock_session):
        """Test model pulling."""
        # Mock streaming pull response
        pull_data = [
            b'{"status": "downloading", "completed": 1024, "total": 2048}\n',
            b'{"status": "verifying sha256"}\n',
            b'{"status": "success"}\n'
        ]
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content.__aiter__.return_value = pull_data
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        ollama_client.session = mock_session
        
        responses = []
        async for response in ollama_client.pull_model("llama2"):
            responses.append(response)
        
        assert len(responses) == 3
        assert responses[0]["status"] == "downloading"
        assert responses[2]["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_get_model_info(self, ollama_client):
        """Test getting specific model info."""
        test_models = [
            OllamaModelInfo("llama2", size="3.8GB", digest="abc123"),
            OllamaModelInfo("codellama", size="7.3GB", digest="def456")
        ]
        
        with patch.object(ollama_client, 'list_models', return_value=test_models):
            model_info = await ollama_client.get_model_info("llama2")
            assert model_info is not None
            assert model_info.name == "llama2"
            assert model_info.size == "3.8GB"
            
            # Test non-existent model
            model_info = await ollama_client.get_model_info("nonexistent")
            assert model_info is None
    
    def test_estimate_tokens(self, ollama_client):
        """Test token estimation."""
        text = "Hello world, this is a test message."
        tokens = ollama_client.estimate_tokens(text)
        
        # Should be roughly len(text) / 4
        expected = len(text) // 4
        assert tokens == expected
    
    @pytest.mark.asyncio
    async def test_validate_model_success(self, ollama_client):
        """Test successful model validation."""
        test_model = OllamaModelInfo("llama2", size="3.8GB", digest="abc123")
        
        with patch.object(ollama_client, 'get_model_info', return_value=test_model):
            # Mock successful generation
            async def mock_generate(*args, **kwargs):
                yield {"response": "test", "done": True}
            
            with patch.object(ollama_client, 'generate', mock_generate):
                result = await ollama_client.validate_model("llama2")
                
                assert result["valid"] is True
                assert result["available"] is True
                assert result["test_successful"] is True
                assert "model_info" in result
    
    @pytest.mark.asyncio
    async def test_validate_model_not_found(self, ollama_client):
        """Test validation of non-existent model."""
        with patch.object(ollama_client, 'get_model_info', return_value=None):
            result = await ollama_client.validate_model("nonexistent")
            
            assert result["valid"] is False
            assert result["available"] is False
            assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_model_generation_fails(self, ollama_client):
        """Test validation when model generation fails."""
        test_model = OllamaModelInfo("llama2", size="3.8GB", digest="abc123")
        
        with patch.object(ollama_client, 'get_model_info', return_value=test_model):
            # Mock failed generation
            async def mock_generate(*args, **kwargs):
                raise Exception("Generation failed")
            
            with patch.object(ollama_client, 'generate', mock_generate):
                result = await ollama_client.validate_model("llama2")
                
                assert result["valid"] is False
                assert result["available"] is True
                assert "test failed" in result["error"]