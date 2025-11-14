"""Configuration management API endpoints."""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.core.dependencies import get_embedding_service, get_ollama_client
from app.services.embedding_service import EmbeddingService
from app.services.ollama_client import OllamaClient
from app.models.config import (
    EmbeddingModelInfo,
    OllamaModelInfo,
    ModelSwitchRequest,
    ModelSwitchResponse,
    BenchmarkRequest,
    BenchmarkResponse,
    BenchmarkResult,
    ModelType,
    ModelStatus,
    SystemConfiguration,
    ConfigurationUpdateRequest
)
from app.core.exceptions import (
    APIException,
    ModelNotFoundError,
    ModelLoadError,
    ConfigurationError
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfigurationService:
    """Service for managing system configuration."""
    
    def __init__(self):
        self._config_cache: Optional[SystemConfiguration] = None
        self._benchmark_tasks: Dict[str, Dict[str, Any]] = {}
    
    async def get_system_config(self) -> SystemConfiguration:
        """Get current system configuration."""
        if self._config_cache is None:
            # Initialize with defaults - in production this would come from database/file
            self._config_cache = SystemConfiguration(
                embedding_model="all-minilm-l6-v2",
                ollama_model="llama3.2",
                chunk_size=1000,
                chunk_overlap=200,
                max_context_tokens=4000,
                default_top_k=10,
                min_similarity_score=0.5
            )
        return self._config_cache
    
    async def update_system_config(self, updates: ConfigurationUpdateRequest) -> SystemConfiguration:
        """Update system configuration."""
        config = await self.get_system_config()
        
        # Update only provided fields
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(config, field):
                setattr(config, field, value)
        
        # Update timestamps
        config.updated_at = datetime.now()
        
        # In production, persist to database/file here
        self._config_cache = config
        
        logger.info(f"Updated system configuration: {update_data}")
        return config


# Global configuration service instance
config_service = ConfigurationService()


@router.get("/models/embeddings", response_model=List[EmbeddingModelInfo])
async def get_embedding_models(
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> List[EmbeddingModelInfo]:
    """
    Get list of available embedding models.
    
    Returns information about all available embedding models including:
    - Model specifications (dimensions, size, languages)
    - Current status and availability
    - Performance metrics if available
    """
    try:
        models = await embedding_service.get_available_models()
        logger.info(f"Retrieved {len(models)} embedding models")
        return models
    
    except Exception as e:
        logger.error(f"Error retrieving embedding models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve embedding models: {str(e)}"
        )


@router.get("/models/embeddings/active", response_model=Optional[EmbeddingModelInfo])
async def get_active_embedding_model(
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> Optional[EmbeddingModelInfo]:
    """
    Get currently active embedding model.
    
    Returns information about the currently active embedding model,
    or null if no model is active.
    """
    try:
        active_model = await embedding_service.get_active_model()
        if active_model:
            logger.info(f"Active embedding model: {active_model.key}")
        else:
            logger.info("No active embedding model")
        return active_model
    
    except Exception as e:
        logger.error(f"Error retrieving active embedding model: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active embedding model: {str(e)}"
        )


@router.get("/models/ollama", response_model=List[Dict[str, Any]])
async def get_ollama_models(
    force_refresh: bool = False,
    ollama_client: OllamaClient = Depends(get_ollama_client)
) -> List[Dict[str, Any]]:
    """
    Get list of available Ollama models.
    
    Args:
        force_refresh: Whether to force refresh the model list from Ollama
    
    Returns information about all available Ollama models including:
    - Model names and sizes
    - Availability status
    - Download information
    """
    try:
        models = await ollama_client.list_models(force_refresh=force_refresh)
        
        # Convert to response format
        model_list = []
        for model in models:
            model_dict = model.to_dict()
            
            # Add additional fields for API response
            model_dict.update({
                "display_name": model.name.replace(":", " "),
                "family": model.name.split(":")[0] if ":" in model.name else model.name,
                "parameter_count": model.details.get("parameter_size", "Unknown"),
                "quantization": model.details.get("quantization_level"),
                "status": ModelStatus.AVAILABLE if model.is_available else ModelStatus.UNAVAILABLE,
                "is_active": False  # Will be updated based on system config
            })
            
            model_list.append(model_dict)
        
        # Mark active model
        config = await config_service.get_system_config()
        for model_dict in model_list:
            if model_dict["name"] == config.ollama_model:
                model_dict["is_active"] = True
        
        logger.info(f"Retrieved {len(model_list)} Ollama models")
        return model_list
    
    except Exception as e:
        logger.error(f"Error retrieving Ollama models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Ollama models: {str(e)}"
        )


@router.get("/models/ollama/active")
async def get_active_ollama_model(
    ollama_client: OllamaClient = Depends(get_ollama_client)
) -> Dict[str, Any]:
    """
    Get currently active Ollama model.
    
    Returns information about the currently active Ollama model.
    """
    try:
        config = await config_service.get_system_config()
        active_model_name = config.ollama_model
        
        # Get model info from Ollama
        model_info = await ollama_client.get_model_info(active_model_name)
        
        if model_info:
            result = model_info.to_dict()
            result["is_active"] = True
            result["status"] = ModelStatus.AVAILABLE if model_info.is_available else ModelStatus.UNAVAILABLE
        else:
            result = {
                "name": active_model_name,
                "is_active": True,
                "status": ModelStatus.UNAVAILABLE,
                "error": "Model not found in Ollama"
            }
        
        logger.info(f"Active Ollama model: {active_model_name}")
        return result
    
    except Exception as e:
        logger.error(f"Error retrieving active Ollama model: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active Ollama model: {str(e)}"
        )


@router.post("/models/switch", response_model=ModelSwitchResponse)
async def switch_model(
    request: ModelSwitchRequest,
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    ollama_client: OllamaClient = Depends(get_ollama_client)
) -> ModelSwitchResponse:
    """
    Switch to a different model (embedding or Ollama).
    
    Args:
        request: Model switch request with type and model key
    
    Returns:
        Switch response with success status and timing information
    """
    start_time = time.time()
    
    try:
        config = await config_service.get_system_config()
        
        if request.model_type == ModelType.EMBEDDING:
            # Switch embedding model
            previous_model = config.embedding_model
            
            try:
                model_info = await embedding_service.switch_model(request.model_key)
                
                # Update system configuration
                config.embedding_model = request.model_key
                config.updated_at = datetime.now()
                
                switch_time = time.time() - start_time
                
                logger.info(f"Switched embedding model from {previous_model} to {request.model_key}")
                
                return ModelSwitchResponse(
                    success=True,
                    model_type=request.model_type,
                    previous_model=previous_model,
                    new_model=request.model_key,
                    switch_time=switch_time,
                    message=f"Successfully switched to embedding model '{request.model_key}'"
                )
                
            except ModelNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except ModelLoadError as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        elif request.model_type == ModelType.LLM:
            # Switch Ollama model
            previous_model = config.ollama_model
            
            # Validate model exists
            model_validation = await ollama_client.validate_model(request.model_key)
            
            if not model_validation["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ollama model '{request.model_key}' is not valid: {model_validation.get('error', 'Unknown error')}"
                )
            
            # Update system configuration
            config.ollama_model = request.model_key
            config.updated_at = datetime.now()
            
            switch_time = time.time() - start_time
            
            logger.info(f"Switched Ollama model from {previous_model} to {request.model_key}")
            
            return ModelSwitchResponse(
                success=True,
                model_type=request.model_type,
                previous_model=previous_model,
                new_model=request.model_key,
                switch_time=switch_time,
                message=f"Successfully switched to Ollama model '{request.model_key}'"
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model type: {request.model_type}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching model: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to switch model: {str(e)}"
        )


@router.post("/benchmark", response_model=Dict[str, Any])
async def start_benchmark(
    request: BenchmarkRequest,
    background_tasks: BackgroundTasks,
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    ollama_client: OllamaClient = Depends(get_ollama_client)
) -> Dict[str, Any]:
    """
    Start model performance benchmarking.
    
    Args:
        request: Benchmark request with model type and parameters
        background_tasks: FastAPI background tasks
    
    Returns:
        Benchmark task information with ID for status tracking
    """
    try:
        # Generate unique benchmark ID
        benchmark_id = f"benchmark_{int(time.time())}_{request.model_type}"
        
        # Initialize benchmark task
        config_service._benchmark_tasks[benchmark_id] = {
            "id": benchmark_id,
            "status": "started",
            "model_type": request.model_type,
            "started_at": datetime.now(),
            "progress": 0.0,
            "results": None,
            "error": None
        }
        
        # Start benchmark in background
        if request.model_type == ModelType.EMBEDDING:
            background_tasks.add_task(
                _run_embedding_benchmark,
                benchmark_id,
                request,
                embedding_service
            )
        elif request.model_type == ModelType.LLM:
            background_tasks.add_task(
                _run_ollama_benchmark,
                benchmark_id,
                request,
                ollama_client
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model type for benchmarking: {request.model_type}"
            )
        
        logger.info(f"Started benchmark {benchmark_id} for {request.model_type}")
        
        return {
            "benchmark_id": benchmark_id,
            "status": "started",
            "model_type": request.model_type,
            "message": f"Benchmark started for {request.model_type} models"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting benchmark: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start benchmark: {str(e)}"
        )


@router.get("/benchmark/{benchmark_id}")
async def get_benchmark_status(benchmark_id: str) -> Dict[str, Any]:
    """
    Get benchmark status and results.
    
    Args:
        benchmark_id: ID of the benchmark to check
    
    Returns:
        Benchmark status and results if completed
    """
    try:
        if benchmark_id not in config_service._benchmark_tasks:
            raise HTTPException(
                status_code=404,
                detail=f"Benchmark {benchmark_id} not found"
            )
        
        task_info = config_service._benchmark_tasks[benchmark_id]
        
        return {
            "benchmark_id": benchmark_id,
            "status": task_info["status"],
            "model_type": task_info["model_type"],
            "started_at": task_info["started_at"].isoformat(),
            "progress": task_info["progress"],
            "results": task_info["results"],
            "error": task_info["error"],
            "completed_at": task_info.get("completed_at")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving benchmark status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve benchmark status: {str(e)}"
        )


@router.get("/system")
async def get_system_configuration() -> SystemConfiguration:
    """
    Get current system configuration.
    
    Returns:
        Current system configuration including active models and settings
    """
    try:
        config = await config_service.get_system_config()
        logger.info("Retrieved system configuration")
        return config
    
    except Exception as e:
        logger.error(f"Error retrieving system configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve system configuration: {str(e)}"
        )


@router.put("/system")
async def update_system_configuration(
    updates: ConfigurationUpdateRequest
) -> SystemConfiguration:
    """
    Update system configuration.
    
    Args:
        updates: Configuration updates to apply
    
    Returns:
        Updated system configuration
    """
    try:
        config = await config_service.update_system_config(updates)
        logger.info(f"Updated system configuration")
        return config
    
    except Exception as e:
        logger.error(f"Error updating system configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update system configuration: {str(e)}"
        )


# Background task functions

async def _run_embedding_benchmark(
    benchmark_id: str,
    request: BenchmarkRequest,
    embedding_service: EmbeddingService
):
    """Run embedding model benchmark in background."""
    try:
        task_info = config_service._benchmark_tasks[benchmark_id]
        task_info["status"] = "running"
        task_info["progress"] = 0.1
        
        # Use custom test queries or defaults
        test_queries = request.test_queries or [
            "What are the technical specifications of the ESP32 microcontroller?",
            "How to implement machine learning algorithms in Python?",
            "Explain the architecture of neural networks and deep learning.",
            "Database design principles and normalization techniques.",
            "Web development with JavaScript and modern frameworks.",
            "Cloud computing services and deployment strategies.",
            "Cybersecurity best practices for web applications.",
            "Data analysis and visualization with Python libraries."
        ]
        
        # Get models to benchmark
        model_keys = request.model_keys
        if not model_keys:
            available_models = await embedding_service.get_available_models()
            model_keys = [model.key for model in available_models]
        
        task_info["progress"] = 0.2
        
        # Run benchmark
        results = await embedding_service.benchmark_models(
            test_texts=test_queries,
            model_keys=model_keys
        )
        
        task_info["progress"] = 0.9
        
        # Convert results to BenchmarkResult format
        benchmark_results = []
        for model_key, model_results in results.items():
            if "error" not in model_results:
                benchmark_results.append(BenchmarkResult(
                    model_key=model_key,
                    test_name="embedding_generation",
                    avg_time=model_results["avg_time_per_text"],
                    min_time=model_results["avg_time_per_text"] * 0.8,  # Approximation
                    max_time=model_results["avg_time_per_text"] * 1.2,  # Approximation
                    throughput=model_results["throughput"],
                    accuracy_score=model_results.get("model_info", {}).get("performance_score"),
                    memory_usage=None  # Not available in current implementation
                ))
        
        # Create response
        response = BenchmarkResponse(
            benchmark_id=benchmark_id,
            model_type=ModelType.EMBEDDING,
            results=benchmark_results,
            total_time=sum(r.avg_time for r in benchmark_results),
            timestamp=datetime.now()
        )
        
        # Update task
        task_info["status"] = "completed"
        task_info["progress"] = 1.0
        task_info["results"] = response.model_dump()
        task_info["completed_at"] = datetime.now()
        
        logger.info(f"Completed embedding benchmark {benchmark_id}")
        
    except Exception as e:
        logger.error(f"Embedding benchmark {benchmark_id} failed: {e}")
        task_info = config_service._benchmark_tasks[benchmark_id]
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["completed_at"] = datetime.now()


async def _run_ollama_benchmark(
    benchmark_id: str,
    request: BenchmarkRequest,
    ollama_client: OllamaClient
):
    """Run Ollama model benchmark in background."""
    try:
        task_info = config_service._benchmark_tasks[benchmark_id]
        task_info["status"] = "running"
        task_info["progress"] = 0.1
        
        # Use custom test queries or defaults
        test_queries = request.test_queries or [
            "Explain quantum computing in simple terms.",
            "Write a Python function to calculate fibonacci numbers.",
            "What are the benefits of renewable energy?",
            "Describe the process of photosynthesis.",
            "How does machine learning work?"
        ]
        
        # Get models to benchmark
        model_keys = request.model_keys
        if not model_keys:
            available_models = await ollama_client.list_models()
            model_keys = [model.name for model in available_models if model.is_available]
        
        task_info["progress"] = 0.2
        
        benchmark_results = []
        
        for i, model_name in enumerate(model_keys):
            try:
                logger.info(f"Benchmarking Ollama model: {model_name}")
                
                total_time = 0
                times = []
                
                # Run multiple iterations
                for iteration in range(request.iterations):
                    for query in test_queries:
                        start_time = time.time()
                        
                        # Generate response
                        response_text = ""
                        async for chunk in ollama_client.generate(
                            model=model_name,
                            prompt=query,
                            stream=False
                        ):
                            if chunk.get("done"):
                                response_text = chunk.get("response", "")
                                break
                        
                        end_time = time.time()
                        query_time = end_time - start_time
                        times.append(query_time)
                        total_time += query_time
                
                # Calculate metrics
                avg_time = total_time / (len(test_queries) * request.iterations)
                min_time = min(times)
                max_time = max(times)
                throughput = 1.0 / avg_time if avg_time > 0 else 0
                
                benchmark_results.append(BenchmarkResult(
                    model_key=model_name,
                    test_name="text_generation",
                    avg_time=avg_time,
                    min_time=min_time,
                    max_time=max_time,
                    throughput=throughput,
                    accuracy_score=None,  # Would need human evaluation
                    memory_usage=None
                ))
                
                # Update progress
                progress = 0.2 + (0.7 * (i + 1) / len(model_keys))
                task_info["progress"] = progress
                
            except Exception as e:
                logger.error(f"Failed to benchmark Ollama model {model_name}: {e}")
                continue
        
        # Create response
        response = BenchmarkResponse(
            benchmark_id=benchmark_id,
            model_type=ModelType.LLM,
            results=benchmark_results,
            total_time=sum(r.avg_time for r in benchmark_results),
            timestamp=datetime.now()
        )
        
        # Update task
        task_info["status"] = "completed"
        task_info["progress"] = 1.0
        task_info["results"] = response.model_dump()
        task_info["completed_at"] = datetime.now()
        
        logger.info(f"Completed Ollama benchmark {benchmark_id}")
        
    except Exception as e:
        logger.error(f"Ollama benchmark {benchmark_id} failed: {e}")
        task_info = config_service._benchmark_tasks[benchmark_id]
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["completed_at"] = datetime.now()