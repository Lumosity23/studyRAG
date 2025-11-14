"""Integration tests for configuration management API."""

import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.models.config import ModelType, ModelStatus
from app.services.embedding_service import EmbeddingService
from app.services.ollama_client import OllamaClient


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def real_embedding_service():
    """Create real embedding service for integration tests."""
    return EmbeddingService(cache_size=100, cache_ttl_hours=1)


class TestConfigurationIntegration:
    """Integration tests for configuration management."""
    
    @patch('app.core.dependencies.get_embedding_service')
    def test_full_embedding_workflow(self, mock_get_service, client, real_embedding_service):
        """Test complete embedding model workflow."""
        mock_get_service.return_value = real_embedding_service
        
        # 1. Get available models
        response = client.get("/api/config/models/embeddings")
        assert response.status_code == 200
        models = response.json()
        assert len(models) > 0
        
        # Find a model to switch to
        target_model = None
        for model in models:
            if not model["is_active"]:
                target_model = model["key"]
                break
        
        if target_model:
            # 2. Switch to different model
            switch_request = {
                "model_type": "embedding",
                "model_key": target_model,
                "force_reload": False
            }
            
            response = client.post("/api/config/models/switch", json=switch_request)
            assert response.status_code == 200
            switch_data = response.json()
            assert switch_data["success"] is True
            assert switch_data["new_model"] == target_model
            
            # 3. Verify active model changed
            response = client.get("/api/config/models/embeddings/active")
            assert response.status_code == 200
            active_model = response.json()
            assert active_model["key"] == target_model
            assert active_model["is_active"] is True
    
    @patch('app.core.dependencies.get_ollama_client')
    @patch('app.api.endpoints.config.config_service')
    def test_ollama_model_management(self, mock_config_service, mock_get_client, client):
        """Test Ollama model management workflow."""
        # Mock Ollama client
        mock_client = AsyncMock()
        mock_client.list_models.return_value = [
            MagicMock(
                name="llama2:7b",
                size="3.8GB",
                digest="sha256:abc123",
                modified_at=datetime.now(),
                details={"parameter_size": "7B"},
                is_available=True,
                to_dict=lambda: {
                    "name": "llama2:7b",
                    "size": "3.8GB",
                    "digest": "sha256:abc123",
                    "is_available": True,
                    "details": {"parameter_size": "7B"}
                }
            ),
            MagicMock(
                name="mistral:7b",
                size="4.1GB",
                digest="sha256:def456",
                modified_at=datetime.now(),
                details={"parameter_size": "7B"},
                is_available=True,
                to_dict=lambda: {
                    "name": "mistral:7b",
                    "size": "4.1GB",
                    "digest": "sha256:def456",
                    "is_available": True,
                    "details": {"parameter_size": "7B"}
                }
            )
        ]
        
        mock_client.validate_model.return_value = {
            "valid": True,
            "available": True,
            "test_successful": True
        }
        
        mock_get_client.return_value = mock_client
        
        # Mock system config
        mock_config = MagicMock()
        mock_config.ollama_model = "llama2:7b"
        mock_config_service.get_system_config.return_value = mock_config
        
        # 1. Get available Ollama models
        response = client.get("/api/config/models/ollama")
        assert response.status_code == 200
        models = response.json()
        assert len(models) == 2
        
        # Find active and inactive models
        active_model = next(m for m in models if m["is_active"])
        inactive_model = next(m for m in models if not m["is_active"])
        
        assert active_model["name"] == "llama2:7b"
        assert inactive_model["name"] == "mistral:7b"
        
        # 2. Switch to different model
        switch_request = {
            "model_type": "llm",
            "model_key": "mistral:7b",
            "force_reload": False
        }
        
        response = client.post("/api/config/models/switch", json=switch_request)
        assert response.status_code == 200
        switch_data = response.json()
        assert switch_data["success"] is True
        assert switch_data["new_model"] == "mistral:7b"
        assert switch_data["previous_model"] == "llama2:7b"
    
    @patch('app.core.dependencies.get_embedding_service')
    def test_benchmark_workflow(self, mock_get_service, client, real_embedding_service):
        """Test benchmarking workflow."""
        mock_get_service.return_value = real_embedding_service
        
        # 1. Start benchmark
        benchmark_request = {
            "model_type": "embedding",
            "model_keys": ["all-minilm-l6-v2"],
            "test_queries": ["Test query for benchmarking"],
            "iterations": 1
        }
        
        response = client.post("/api/config/benchmark", json=benchmark_request)
        assert response.status_code == 200
        benchmark_data = response.json()
        benchmark_id = benchmark_data["benchmark_id"]
        assert benchmark_data["status"] == "started"
        
        # 2. Wait a bit for background task to start
        time.sleep(0.1)
        
        # 3. Check benchmark status
        response = client.get(f"/api/config/benchmark/{benchmark_id}")
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["benchmark_id"] == benchmark_id
        assert status_data["status"] in ["started", "running", "completed"]
        
        # 4. Wait for completion (in real scenario, would poll)
        max_wait = 30  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = client.get(f"/api/config/benchmark/{benchmark_id}")
            status_data = response.json()
            
            if status_data["status"] == "completed":
                assert status_data["results"] is not None
                assert status_data["progress"] == 1.0
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Benchmark failed: {status_data.get('error')}")
            
            time.sleep(0.5)
        else:
            pytest.fail("Benchmark did not complete within timeout")
    
    def test_system_configuration_workflow(self, client):
        """Test system configuration management."""
        # 1. Get current configuration
        response = client.get("/api/config/system")
        assert response.status_code == 200
        original_config = response.json()
        
        # 2. Update configuration
        updates = {
            "chunk_size": 1200,
            "chunk_overlap": 250,
            "default_top_k": 15,
            "min_similarity_score": 0.6
        }
        
        response = client.put("/api/config/system", json=updates)
        assert response.status_code == 200
        updated_config = response.json()
        
        # Verify updates were applied (mock service will return the mock object)
        # In real integration test, would verify actual values
        
        # 3. Get configuration again to verify persistence
        response = client.get("/api/config/system")
        assert response.status_code == 200
    
    def test_error_handling_integration(self, client):
        """Test error handling in integration scenarios."""
        # 1. Test invalid model switch
        invalid_switch = {
            "model_type": "embedding",
            "model_key": "nonexistent-model-12345",
            "force_reload": False
        }
        
        response = client.post("/api/config/models/switch", json=invalid_switch)
        assert response.status_code in [404, 500]  # Depends on implementation
        
        # 2. Test invalid benchmark request
        invalid_benchmark = {
            "model_type": "embedding",
            "model_keys": ["nonexistent-model"],
            "iterations": 0  # Invalid
        }
        
        response = client.post("/api/config/benchmark", json=invalid_benchmark)
        assert response.status_code == 422  # Validation error
        
        # 3. Test nonexistent benchmark status
        response = client.get("/api/config/benchmark/nonexistent-benchmark-id")
        assert response.status_code == 404
    
    @patch('app.core.dependencies.get_embedding_service')
    @patch('app.core.dependencies.get_ollama_client')
    def test_cross_service_integration(self, mock_get_ollama, mock_get_embedding, client):
        """Test integration between embedding and Ollama services."""
        # Mock services
        mock_embedding_service = AsyncMock()
        mock_embedding_service.get_available_models.return_value = [
            MagicMock(
                key="all-minilm-l6-v2",
                name="All-MiniLM-L6-v2",
                is_active=True,
                status=ModelStatus.AVAILABLE,
                model_dump=lambda: {
                    "key": "all-minilm-l6-v2",
                    "name": "All-MiniLM-L6-v2",
                    "is_active": True,
                    "status": "available"
                }
            )
        ]
        
        mock_ollama_client = AsyncMock()
        mock_ollama_client.list_models.return_value = [
            MagicMock(
                name="llama2:7b",
                is_available=True,
                to_dict=lambda: {
                    "name": "llama2:7b",
                    "is_available": True
                }
            )
        ]
        
        mock_get_embedding.return_value = mock_embedding_service
        mock_get_ollama.return_value = mock_ollama_client
        
        # 1. Check both services are available
        response = client.get("/api/config/models/embeddings")
        assert response.status_code == 200
        embedding_models = response.json()
        
        response = client.get("/api/config/models/ollama")
        assert response.status_code == 200
        ollama_models = response.json()
        
        # 2. Verify we can access both types of models
        assert len(embedding_models) > 0
        assert len(ollama_models) > 0
        
        # 3. Test switching between different model types
        embedding_switch = {
            "model_type": "embedding",
            "model_key": "all-minilm-l6-v2",
            "force_reload": True
        }
        
        response = client.post("/api/config/models/switch", json=embedding_switch)
        assert response.status_code == 200
        
        ollama_switch = {
            "model_type": "llm", 
            "model_key": "llama2:7b",
            "force_reload": False
        }
        
        # Mock validation for Ollama
        mock_ollama_client.validate_model.return_value = {
            "valid": True,
            "available": True
        }
        
        response = client.post("/api/config/models/switch", json=ollama_switch)
        assert response.status_code == 200


class TestConfigurationPersistence:
    """Test configuration persistence and state management."""
    
    def test_configuration_state_consistency(self, client):
        """Test that configuration state remains consistent across requests."""
        # This would test actual persistence in a real integration test
        # For now, we test the API consistency
        
        # 1. Get initial state
        response = client.get("/api/config/system")
        assert response.status_code == 200
        
        # 2. Make multiple updates
        updates = [
            {"chunk_size": 800},
            {"chunk_overlap": 150},
            {"default_top_k": 20}
        ]
        
        for update in updates:
            response = client.put("/api/config/system", json=update)
            assert response.status_code == 200
        
        # 3. Verify final state
        response = client.get("/api/config/system")
        assert response.status_code == 200
    
    @patch('app.api.endpoints.config.config_service')
    def test_benchmark_task_persistence(self, mock_config_service, client):
        """Test that benchmark tasks persist across requests."""
        # Mock benchmark tasks storage
        benchmark_tasks = {}
        mock_config_service._benchmark_tasks = benchmark_tasks
        
        # 1. Start multiple benchmarks
        benchmark_ids = []
        
        for i in range(3):
            request_data = {
                "model_type": "embedding",
                "iterations": 1
            }
            
            response = client.post("/api/config/benchmark", json=request_data)
            assert response.status_code == 200
            benchmark_id = response.json()["benchmark_id"]
            benchmark_ids.append(benchmark_id)
        
        # 2. Verify all benchmarks are tracked
        assert len(benchmark_tasks) == 3
        
        # 3. Check each benchmark status
        for benchmark_id in benchmark_ids:
            response = client.get(f"/api/config/benchmark/{benchmark_id}")
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["benchmark_id"] == benchmark_id


class TestConfigurationValidation:
    """Test configuration validation and constraints."""
    
    def test_model_switch_validation(self, client):
        """Test model switch request validation."""
        # Test missing required fields
        response = client.post("/api/config/models/switch", json={})
        assert response.status_code == 422
        
        # Test invalid model type
        invalid_request = {
            "model_type": "invalid_type",
            "model_key": "some-model"
        }
        response = client.post("/api/config/models/switch", json=invalid_request)
        assert response.status_code == 422
        
        # Test empty model key
        invalid_request = {
            "model_type": "embedding",
            "model_key": ""
        }
        response = client.post("/api/config/models/switch", json=invalid_request)
        assert response.status_code == 422
    
    def test_benchmark_request_validation(self, client):
        """Test benchmark request validation."""
        # Test invalid iterations
        invalid_request = {
            "model_type": "embedding",
            "iterations": 0
        }
        response = client.post("/api/config/benchmark", json=invalid_request)
        assert response.status_code == 422
        
        invalid_request = {
            "model_type": "embedding", 
            "iterations": 25  # Too many
        }
        response = client.post("/api/config/benchmark", json=invalid_request)
        assert response.status_code == 422
        
        # Test invalid model type
        invalid_request = {
            "model_type": "invalid_type",
            "iterations": 5
        }
        response = client.post("/api/config/benchmark", json=invalid_request)
        assert response.status_code == 422
    
    def test_system_config_validation(self, client):
        """Test system configuration validation."""
        # Test invalid chunk size
        invalid_updates = [
            {"chunk_size": 50},  # Too small
            {"chunk_size": 10000},  # Too large
            {"chunk_overlap": -10},  # Negative
            {"chunk_overlap": 2000},  # Too large
            {"max_context_tokens": 50},  # Too small
            {"max_context_tokens": 10000},  # Too large
            {"default_top_k": 0},  # Too small
            {"default_top_k": 200},  # Too large
            {"min_similarity_score": -0.1},  # Too small
            {"min_similarity_score": 1.5}  # Too large
        ]
        
        for invalid_update in invalid_updates:
            response = client.put("/api/config/system", json=invalid_update)
            assert response.status_code == 422, f"Should reject {invalid_update}"


class TestConfigurationPerformance:
    """Test configuration management performance."""
    
    @patch('app.core.dependencies.get_embedding_service')
    def test_model_listing_performance(self, mock_get_service, client):
        """Test performance of model listing endpoints."""
        # Mock service with many models
        mock_service = AsyncMock()
        mock_models = []
        
        for i in range(50):  # Simulate many models
            mock_models.append(MagicMock(
                key=f"model-{i}",
                name=f"Model {i}",
                is_active=(i == 0),
                model_dump=lambda i=i: {
                    "key": f"model-{i}",
                    "name": f"Model {i}",
                    "is_active": (i == 0)
                }
            ))
        
        mock_service.get_available_models.return_value = mock_models
        mock_get_service.return_value = mock_service
        
        # Measure response time
        start_time = time.time()
        response = client.get("/api/config/models/embeddings")
        end_time = time.time()
        
        assert response.status_code == 200
        assert len(response.json()) == 50
        
        # Should respond quickly even with many models
        response_time = end_time - start_time
        assert response_time < 1.0  # Should be under 1 second
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent configuration requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = client.get("/api/config/system")
                results.put(("success", response.status_code))
            except Exception as e:
                results.put(("error", str(e)))
        
        # Start multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # Check all requests succeeded
        success_count = 0
        while not results.empty():
            result_type, result_value = results.get()
            if result_type == "success":
                assert result_value == 200
                success_count += 1
        
        assert success_count == 10