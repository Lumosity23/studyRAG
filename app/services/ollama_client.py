"""Ollama client wrapper with connection management and model validation."""

import asyncio
import logging
from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime
import aiohttp
import json

from app.core.config import get_settings
from app.core.exceptions import APIException


logger = logging.getLogger(__name__)


class OllamaConnectionError(APIException):
    """Ollama connection error."""
    
    def __init__(self, message: str, details: Dict = None):
        super().__init__("CHAT_001", message, 503, details)


class OllamaModelError(APIException):
    """Ollama model error."""
    
    def __init__(self, message: str, details: Dict = None):
        super().__init__("CHAT_002", message, 400, details)


class OllamaGenerationError(APIException):
    """Ollama generation error."""
    
    def __init__(self, message: str, details: Dict = None):
        super().__init__("CHAT_004", message, 500, details)


class OllamaModelInfo:
    """Information about an Ollama model."""
    
    def __init__(self, name: str, size: str = None, digest: str = None, 
                 modified_at: datetime = None, details: Dict = None):
        self.name = name
        self.size = size
        self.digest = digest
        self.modified_at = modified_at
        self.details = details or {}
    
    @property
    def is_available(self) -> bool:
        """Check if model is available locally."""
        return self.digest is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "size": self.size,
            "digest": self.digest,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "is_available": self.is_available,
            "details": self.details
        }


class OllamaClient:
    """Ollama client wrapper with connection management and model validation."""
    
    def __init__(self, settings=None):
        """Initialize Ollama client."""
        self.settings = settings or get_settings()
        self.base_url = self.settings.ollama_url
        self.timeout = self.settings.OLLAMA_TIMEOUT
        self.session: Optional[aiohttp.ClientSession] = None
        self._models_cache: Optional[List[OllamaModelInfo]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 300  # 5 minutes
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is available."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """Check if Ollama service is healthy."""
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self, force_refresh: bool = False) -> List[OllamaModelInfo]:
        """List available Ollama models."""
        # Check cache
        if (not force_refresh and self._models_cache and self._cache_timestamp and 
            (datetime.now() - self._cache_timestamp).seconds < self._cache_ttl):
            return self._models_cache
        
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status != 200:
                    raise OllamaConnectionError(
                        f"Failed to list models: HTTP {response.status}",
                        {"status_code": response.status}
                    )
                
                data = await response.json()
                models = []
                
                for model_data in data.get("models", []):
                    modified_at = None
                    if model_data.get("modified_at"):
                        try:
                            modified_at = datetime.fromisoformat(
                                model_data["modified_at"].replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass
                    
                    model = OllamaModelInfo(
                        name=model_data["name"],
                        size=model_data.get("size"),
                        digest=model_data.get("digest"),
                        modified_at=modified_at,
                        details=model_data.get("details", {})
                    )
                    models.append(model)
                
                # Update cache
                self._models_cache = models
                self._cache_timestamp = datetime.now()
                
                return models
                
        except aiohttp.ClientError as e:
            raise OllamaConnectionError(f"Failed to connect to Ollama: {e}")
        except Exception as e:
            raise OllamaGenerationError(f"Error listing models: {e}")
    
    async def model_exists(self, model_name: str) -> bool:
        """Check if a model exists locally."""
        try:
            models = await self.list_models()
            return any(model.name == model_name for model in models)
        except Exception:
            return False
    
    async def pull_model(self, model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Pull a model from Ollama registry."""
        try:
            await self._ensure_session()
            
            payload = {"name": model_name}
            
            async with self.session.post(
                f"{self.base_url}/api/pull",
                json=payload
            ) as response:
                if response.status != 200:
                    raise OllamaModelError(
                        f"Failed to pull model {model_name}: HTTP {response.status}"
                    )
                
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode())
                            yield data
                        except json.JSONDecodeError:
                            continue
                            
        except aiohttp.ClientError as e:
            raise OllamaConnectionError(f"Failed to connect to Ollama: {e}")
        except Exception as e:
            raise OllamaGenerationError(f"Error pulling model: {e}")
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        context: Optional[List[int]] = None,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate text using Ollama model."""
        try:
            await self._ensure_session()
            
            # Validate model exists
            if not await self.model_exists(model):
                raise OllamaModelError(f"Model '{model}' is not available locally")
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream
            }
            
            if system:
                payload["system"] = system
            if context:
                payload["context"] = context
            if options:
                payload["options"] = options
            
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise OllamaGenerationError(
                        f"Generation failed: HTTP {response.status}",
                        {"status_code": response.status, "error": error_text}
                    )
                
                if stream:
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode())
                                yield data
                            except json.JSONDecodeError:
                                continue
                else:
                    data = await response.json()
                    yield data
                    
        except aiohttp.ClientError as e:
            raise OllamaConnectionError(f"Failed to connect to Ollama: {e}")
        except OllamaModelError:
            raise
        except OllamaGenerationError:
            raise
        except Exception as e:
            raise OllamaGenerationError(f"Unexpected error during generation: {e}")
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Chat with Ollama model using conversation format."""
        try:
            await self._ensure_session()
            
            # Validate model exists
            if not await self.model_exists(model):
                raise OllamaModelError(f"Model '{model}' is not available locally")
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream
            }
            
            if options:
                payload["options"] = options
            
            async with self.session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise OllamaGenerationError(
                        f"Chat failed: HTTP {response.status}",
                        {"status_code": response.status, "error": error_text}
                    )
                
                if stream:
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode())
                                yield data
                            except json.JSONDecodeError:
                                continue
                else:
                    data = await response.json()
                    yield data
                    
        except aiohttp.ClientError as e:
            raise OllamaConnectionError(f"Failed to connect to Ollama: {e}")
        except OllamaModelError:
            raise
        except OllamaGenerationError:
            raise
        except Exception as e:
            raise OllamaGenerationError(f"Unexpected error during chat: {e}")
    
    async def get_model_info(self, model_name: str) -> Optional[OllamaModelInfo]:
        """Get detailed information about a specific model."""
        models = await self.list_models()
        for model in models:
            if model.name == model_name:
                return model
        return None
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Simple approximation: ~4 characters per token for English
        return len(text) // 4
    
    async def validate_model(self, model_name: str) -> Dict[str, Any]:
        """Validate a model and return its capabilities."""
        try:
            model_info = await self.get_model_info(model_name)
            if not model_info:
                return {
                    "valid": False,
                    "error": f"Model '{model_name}' not found",
                    "available": False
                }
            
            # Test generation with a simple prompt
            test_prompt = "Hello"
            try:
                async for response in self.generate(model_name, test_prompt):
                    if response.get("done"):
                        return {
                            "valid": True,
                            "available": True,
                            "model_info": model_info.to_dict(),
                            "test_successful": True
                        }
                
                return {
                    "valid": False,
                    "available": True,
                    "model_info": model_info.to_dict(),
                    "error": "Model test generation failed"
                }
                
            except Exception as e:
                return {
                    "valid": False,
                    "available": True,
                    "model_info": model_info.to_dict(),
                    "error": f"Model test failed: {e}"
                }
                
        except Exception as e:
            return {
                "valid": False,
                "error": f"Model validation failed: {e}",
                "available": False
            }