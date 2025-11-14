"""Configuration management for StudyRAG application."""

from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", alias="ENV")
    DEBUG: bool = Field(default=True)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    # Security settings
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production")
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"]
    )
    
    # ChromaDB settings
    CHROMA_HOST: str = Field(default="localhost")
    CHROMA_PORT: int = Field(default=8001)
    CHROMA_COLLECTION_NAME: str = Field(default="studyrag_documents")
    
    # Ollama settings
    OLLAMA_HOST: str = Field(default="localhost")
    OLLAMA_PORT: int = Field(default=11434)
    OLLAMA_MODEL: str = Field(default="llama3.2")
    OLLAMA_TIMEOUT: int = Field(default=120)
    
    # Embedding settings
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DEVICE: str = Field(default="cpu")
    EMBEDDING_BATCH_SIZE: int = Field(default=32)
    
    # Document processing settings
    MAX_FILE_SIZE: int = Field(default=50 * 1024 * 1024)  # 50MB
    UPLOAD_DIR: str = Field(default="uploads")
    PROCESSED_DIR: str = Field(default="processed_docs")
    CHUNK_SIZE: int = Field(default=1000)
    CHUNK_OVERLAP: int = Field(default=200)
    
    # Search settings
    DEFAULT_TOP_K: int = Field(default=10)
    MIN_SIMILARITY_SCORE: float = Field(default=0.5)
    MAX_CONTEXT_TOKENS: int = Field(default=4000)
    
    # Cache settings (Redis - optional)
    REDIS_URL: Optional[str] = Field(default=None)
    CACHE_TTL: int = Field(default=3600)  # 1 hour
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    LOG_FILE: Optional[str] = Field(default=None)
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse ALLOWED_ORIGINS from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of: {allowed_envs}")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of: {allowed_levels}")
        return v.upper()
    
    @field_validator("EMBEDDING_DEVICE")
    @classmethod
    def validate_embedding_device(cls, v):
        """Validate embedding device."""
        allowed_devices = ["cpu", "cuda", "mps"]
        if v not in allowed_devices:
            raise ValueError(f"Embedding device must be one of: {allowed_devices}")
        return v
    
    @property
    def chroma_url(self) -> str:
        """Get ChromaDB URL."""
        return f"http://{self.CHROMA_HOST}:{self.CHROMA_PORT}"
    
    @property
    def ollama_url(self) -> str:
        """Get Ollama URL."""
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"
    
    def create_directories(self) -> None:
        """Create necessary directories."""
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.PROCESSED_DIR, exist_ok=True)
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra environment variables
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.create_directories()
    return settings