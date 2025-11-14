"""Tests for health service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from app.services.health_service import HealthService, HealthStatus


class TestHealthService:
    """Test health service functionality."""
    
    @pytest.fixture
    def health_service(self):
        """Create health service instance."""
        return HealthService()
    
    @pytest.mark.asyncio
    async def test_get_health_status_caching(self, health_service):
        """Test that health status is cached."""
        # Mock all health check methods
        with patch.object(health_service, '_check_chroma_health', new_callable=AsyncMock) as mock_chroma, \
             patch.object(health_service, '_check_ollama_health', new_callable=AsyncMock) as mock_ollama, \
             patch.object(health_service, '_check_embedding_service_health', new_callable=AsyncMock) as mock_embedding, \
             patch.object(health_service, '_check_system_resources', new_callable=AsyncMock) as mock_system:
            
            # Setup mock returns
            mock_chroma.return_value = {"status": HealthStatus.HEALTHY}
            mock_ollama.return_value = {"status": HealthStatus.HEALTHY}
            mock_embedding.return_value = {"status": HealthStatus.HEALTHY}
            mock_system.return_value = {"status": HealthStatus.HEALTHY}
            
            # First call
            status1 = await health_service.get_health_status()
            
            # Second call (should use cache)
            status2 = await health_service.get_health_status()
            
            # Should be the same object (cached)
            assert status1 is status2
            
            # Health checks should only be called once
            mock_chroma.assert_called_once()
            mock_ollama.assert_called_once()
            mock_embedding.assert_called_once()
            mock_system.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_health_status_force_refresh(self, health_service):
        """Test force refresh bypasses cache."""
        with patch.object(health_service, '_check_chroma_health', new_callable=AsyncMock) as mock_chroma, \
             patch.object(health_service, '_check_ollama_health', new_callable=AsyncMock) as mock_ollama, \
             patch.object(health_service, '_check_embedding_service_health', new_callable=AsyncMock) as mock_embedding, \
             patch.object(health_service, '_check_system_resources', new_callable=AsyncMock) as mock_system:
            
            # Setup mock returns
            mock_chroma.return_value = {"status": HealthStatus.HEALTHY}
            mock_ollama.return_value = {"status": HealthStatus.HEALTHY}
            mock_embedding.return_value = {"status": HealthStatus.HEALTHY}
            mock_system.return_value = {"status": HealthStatus.HEALTHY}
            
            # First call
            await health_service.get_health_status()
            
            # Force refresh
            await health_service.get_health_status(force_refresh=True)
            
            # Health checks should be called twice
            assert mock_chroma.call_count == 2
            assert mock_ollama.call_count == 2
            assert mock_embedding.call_count == 2
            assert mock_system.call_count == 2
    
    @pytest.mark.asyncio
    async def test_overall_status_calculation(self, health_service):
        """Test overall status calculation logic."""
        with patch.object(health_service, '_check_chroma_health', new_callable=AsyncMock) as mock_chroma, \
             patch.object(health_service, '_check_ollama_health', new_callable=AsyncMock) as mock_ollama, \
             patch.object(health_service, '_check_embedding_service_health', new_callable=AsyncMock) as mock_embedding, \
             patch.object(health_service, '_check_system_resources', new_callable=AsyncMock) as mock_system:
            
            # Test all healthy
            mock_chroma.return_value = {"status": HealthStatus.HEALTHY}
            mock_ollama.return_value = {"status": HealthStatus.HEALTHY}
            mock_embedding.return_value = {"status": HealthStatus.HEALTHY}
            mock_system.return_value = {"status": HealthStatus.HEALTHY}
            
            status = await health_service.get_health_status(force_refresh=True)
            assert status["status"] == HealthStatus.HEALTHY
            
            # Test degraded (some healthy, some not)
            mock_ollama.return_value = {"status": HealthStatus.UNHEALTHY}
            
            status = await health_service.get_health_status(force_refresh=True)
            assert status["status"] == HealthStatus.DEGRADED
            
            # Test all unhealthy
            mock_chroma.return_value = {"status": HealthStatus.UNHEALTHY}
            mock_embedding.return_value = {"status": HealthStatus.UNHEALTHY}
            
            status = await health_service.get_health_status(force_refresh=True)
            assert status["status"] == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_check_chroma_health_success(self, health_service):
        """Test successful ChromaDB health check."""
        mock_vector_db = AsyncMock()
        mock_vector_db.initialize = AsyncMock()
        mock_vector_db.list_collections = AsyncMock(return_value=["collection1", "collection2"])
        
        with patch('app.services.health_service.VectorDatabase', return_value=mock_vector_db):
            result = await health_service._check_chroma_health()
            
            assert result["status"] == HealthStatus.HEALTHY
            assert "response_time" in result
            assert result["collections_count"] == 2
            assert "url" in result
    
    @pytest.mark.asyncio
    async def test_check_chroma_health_failure(self, health_service):
        """Test ChromaDB health check failure."""
        mock_vector_db = AsyncMock()
        mock_vector_db.initialize = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('app.services.health_service.VectorDatabase', return_value=mock_vector_db):
            result = await health_service._check_chroma_health()
            
            assert result["status"] == HealthStatus.UNHEALTHY
            assert "error" in result
            assert "Connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_check_ollama_health_success(self, health_service):
        """Test successful Ollama health check."""
        mock_ollama = AsyncMock()
        mock_ollama.is_available = AsyncMock(return_value=True)
        mock_ollama.list_models = AsyncMock(return_value=[
            {"name": "llama2"},
            {"name": "codellama"}
        ])
        
        with patch('app.services.health_service.OllamaClient', return_value=mock_ollama), \
             patch('app.services.health_service.get_settings') as mock_settings:
            
            mock_settings.return_value.OLLAMA_MODEL = "llama2"
            mock_settings.return_value.ollama_url = "http://localhost:11434"
            
            result = await health_service._check_ollama_health()
            
            assert result["status"] == HealthStatus.HEALTHY
            assert result["model_available"] is True
            assert result["configured_model"] == "llama2"
            assert len(result["available_models"]) == 2
    
    @pytest.mark.asyncio
    async def test_check_ollama_health_model_not_available(self, health_service):
        """Test Ollama health check when configured model is not available."""
        mock_ollama = AsyncMock()
        mock_ollama.is_available = AsyncMock(return_value=True)
        mock_ollama.list_models = AsyncMock(return_value=[
            {"name": "codellama"}
        ])
        
        with patch('app.services.health_service.OllamaClient', return_value=mock_ollama), \
             patch('app.services.health_service.get_settings') as mock_settings:
            
            mock_settings.return_value.OLLAMA_MODEL = "llama2"
            mock_settings.return_value.ollama_url = "http://localhost:11434"
            
            result = await health_service._check_ollama_health()
            
            assert result["status"] == HealthStatus.DEGRADED
            assert result["model_available"] is False
            assert result["configured_model"] == "llama2"
    
    @pytest.mark.asyncio
    async def test_check_ollama_health_service_unavailable(self, health_service):
        """Test Ollama health check when service is unavailable."""
        mock_ollama = AsyncMock()
        mock_ollama.is_available = AsyncMock(return_value=False)
        
        with patch('app.services.health_service.OllamaClient', return_value=mock_ollama), \
             patch('app.services.health_service.get_settings') as mock_settings:
            
            mock_settings.return_value.ollama_url = "http://localhost:11434"
            
            result = await health_service._check_ollama_health()
            
            assert result["status"] == HealthStatus.UNHEALTHY
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_check_embedding_service_health_success(self, health_service):
        """Test successful embedding service health check."""
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_embedding_service.current_model_key = "test-model"
        mock_embedding_service.available_models = {"test-model": {}, "other-model": {}}
        mock_embedding_service.device = "cpu"
        
        with patch('app.services.health_service.EmbeddingService', return_value=mock_embedding_service):
            result = await health_service._check_embedding_service_health()
            
            assert result["status"] == HealthStatus.HEALTHY
            assert result["current_model"] == "test-model"
            assert result["embedding_dimension"] == 3
            assert len(result["available_models"]) == 2
            assert result["device"] == "cpu"
    
    @pytest.mark.asyncio
    async def test_check_embedding_service_health_failure(self, health_service):
        """Test embedding service health check failure."""
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(side_effect=Exception("Model load failed"))
        
        with patch('app.services.health_service.EmbeddingService', return_value=mock_embedding_service):
            result = await health_service._check_embedding_service_health()
            
            assert result["status"] == HealthStatus.UNHEALTHY
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_check_system_resources_success(self, health_service):
        """Test successful system resources check."""
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.available = 8 * 1024**3  # 8GB
        
        mock_disk = MagicMock()
        mock_disk.percent = 60.0
        mock_disk.free = 100 * 1024**3  # 100GB
        
        with patch('app.services.health_service.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 30.0
            mock_psutil.virtual_memory.return_value = mock_memory
            mock_psutil.disk_usage.return_value = mock_disk
            
            result = await health_service._check_system_resources()
            
            assert result["status"] == HealthStatus.HEALTHY
            assert result["cpu_percent"] == 30.0
            assert result["memory_percent"] == 50.0
            assert result["disk_percent"] == 60.0
            assert len(result["warnings"]) == 0
    
    @pytest.mark.asyncio
    async def test_check_system_resources_high_usage(self, health_service):
        """Test system resources check with high usage."""
        mock_memory = MagicMock()
        mock_memory.percent = 95.0
        mock_memory.available = 1 * 1024**3  # 1GB
        
        mock_disk = MagicMock()
        mock_disk.percent = 95.0
        mock_disk.free = 5 * 1024**3  # 5GB
        
        with patch('app.services.health_service.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 95.0
            mock_psutil.virtual_memory.return_value = mock_memory
            mock_psutil.disk_usage.return_value = mock_disk
            
            result = await health_service._check_system_resources()
            
            assert result["status"] == HealthStatus.DEGRADED
            assert len(result["warnings"]) == 3  # CPU, memory, and disk warnings
    
    @pytest.mark.asyncio
    async def test_check_system_resources_psutil_not_available(self, health_service):
        """Test system resources check when psutil is not available."""
        with patch('app.services.health_service.psutil', side_effect=ImportError):
            result = await health_service._check_system_resources()
            
            assert result["status"] == HealthStatus.UNKNOWN
            assert "psutil not available" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_readiness_status_ready(self, health_service):
        """Test readiness status when services are ready."""
        with patch.object(health_service, '_quick_chroma_check', new_callable=AsyncMock, return_value=True), \
             patch.object(health_service, '_quick_embedding_check', new_callable=AsyncMock, return_value=True):
            
            result = await health_service.get_readiness_status()
            
            assert result["ready"] is True
            assert result["services"]["chroma"] is True
            assert result["services"]["embeddings"] is True
    
    @pytest.mark.asyncio
    async def test_get_readiness_status_not_ready(self, health_service):
        """Test readiness status when services are not ready."""
        with patch.object(health_service, '_quick_chroma_check', new_callable=AsyncMock, return_value=False), \
             patch.object(health_service, '_quick_embedding_check', new_callable=AsyncMock, return_value=True):
            
            result = await health_service.get_readiness_status()
            
            assert result["ready"] is False
            assert result["services"]["chroma"] is False
            assert result["services"]["embeddings"] is True
    
    @pytest.mark.asyncio
    async def test_check_service_connectivity_chroma(self, health_service):
        """Test checking specific service connectivity."""
        with patch.object(health_service, '_check_chroma_health', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {"status": HealthStatus.HEALTHY}
            
            result = await health_service.check_service_connectivity("chroma")
            
            assert result["status"] == HealthStatus.HEALTHY
            mock_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_service_connectivity_unknown_service(self, health_service):
        """Test checking unknown service connectivity."""
        result = await health_service.check_service_connectivity("unknown")
        
        assert result["status"] == HealthStatus.UNKNOWN
        assert "Unknown service" in result["error"]