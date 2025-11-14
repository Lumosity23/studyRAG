"""Custom exception classes for StudyRAG application."""

from typing import Dict, Any, Optional
from datetime import datetime


class APIException(Exception):
    """Base API exception class."""
    
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(self.message)


# Document Processing Exceptions
class DocumentProcessingException(APIException):
    """Base exception for document processing errors."""
    pass


class DocumentProcessingError(DocumentProcessingException):
    """Raised when document processing fails."""
    
    def __init__(self, message: str, error_details: str = None):
        super().__init__(
            error_code="DOC_PROCESSING_001",
            message=message,
            status_code=500,
            details={
                "error_details": error_details
            }
        )


class UnsupportedFileTypeException(DocumentProcessingException):
    """Raised when file type is not supported."""
    
    def __init__(self, file_type: str, supported_types: list):
        super().__init__(
            error_code="DOC_001",
            message=f"File type '{file_type}' is not supported",
            status_code=400,
            details={
                "file_type": file_type,
                "supported_types": supported_types
            }
        )


class FileSizeExceededException(DocumentProcessingException):
    """Raised when file size exceeds maximum allowed size."""
    
    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            error_code="DOC_002",
            message=f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)",
            status_code=413,
            details={
                "file_size": file_size,
                "max_size": max_size,
                "max_size_mb": max_size / (1024 * 1024)
            }
        )


class CorruptedFileException(DocumentProcessingException):
    """Raised when file is corrupted or cannot be read."""
    
    def __init__(self, filename: str, error_details: str = None):
        super().__init__(
            error_code="DOC_003",
            message=f"File '{filename}' is corrupted or cannot be read",
            status_code=400,
            details={
                "filename": filename,
                "error_details": error_details
            }
        )


class DoclingExtractionException(DocumentProcessingException):
    """Raised when Docling extraction fails."""
    
    def __init__(self, filename: str, error_details: str = None):
        super().__init__(
            error_code="DOC_004",
            message=f"Failed to extract content from '{filename}' using Docling",
            status_code=500,
            details={
                "filename": filename,
                "error_details": error_details
            }
        )


class EmbeddingGenerationException(DocumentProcessingException):
    """Raised when embedding generation fails."""
    
    def __init__(self, model_name: str, error_details: str = None):
        super().__init__(
            error_code="DOC_005",
            message=f"Failed to generate embeddings using model '{model_name}'",
            status_code=500,
            details={
                "model_name": model_name,
                "error_details": error_details
            }
        )


# Search Exceptions
class SearchException(APIException):
    """Base exception for search errors."""
    pass


class SearchEngineError(SearchException):
    """Raised when search engine operation fails."""
    
    def __init__(self, message: str, error_details: str = None):
        super().__init__(
            error_code="SEARCH_ENGINE_001",
            message=message,
            status_code=500,
            details={
                "error_details": error_details
            }
        )


class InvalidQueryException(SearchException):
    """Raised when search query is invalid."""
    
    def __init__(self, query: str, reason: str = None):
        super().__init__(
            error_code="SEARCH_001",
            message=f"Invalid search query: {reason or 'Query is empty or malformed'}",
            status_code=400,
            details={
                "query": query,
                "reason": reason
            }
        )


class NoResultsFoundException(SearchException):
    """Raised when no search results are found."""
    
    def __init__(self, query: str, min_similarity: float):
        super().__init__(
            error_code="SEARCH_002",
            message=f"No results found for query with minimum similarity {min_similarity}",
            status_code=404,
            details={
                "query": query,
                "min_similarity": min_similarity
            }
        )


class VectorDatabaseException(SearchException):
    """Raised when vector database operation fails."""
    
    def __init__(self, operation: str, error_details: str = None):
        super().__init__(
            error_code="SEARCH_003",
            message=f"Vector database operation '{operation}' failed",
            status_code=500,
            details={
                "operation": operation,
                "error_details": error_details
            }
        )


class SearchTimeoutException(SearchException):
    """Raised when search operation times out."""
    
    def __init__(self, timeout_seconds: int):
        super().__init__(
            error_code="SEARCH_004",
            message=f"Search operation timed out after {timeout_seconds} seconds",
            status_code=408,
            details={
                "timeout_seconds": timeout_seconds
            }
        )


# Chat Exceptions
class ChatException(APIException):
    """Base exception for chat errors."""
    pass


class OllamaConnectionException(ChatException):
    """Raised when connection to Ollama fails."""
    
    def __init__(self, ollama_url: str, error_details: str = None):
        super().__init__(
            error_code="CHAT_001",
            message=f"Failed to connect to Ollama at {ollama_url}",
            status_code=503,
            details={
                "ollama_url": ollama_url,
                "error_details": error_details
            }
        )


class OllamaModelUnavailableException(ChatException):
    """Raised when Ollama model is not available."""
    
    def __init__(self, model_name: str, available_models: list = None):
        super().__init__(
            error_code="CHAT_002",
            message=f"Ollama model '{model_name}' is not available",
            status_code=404,
            details={
                "model_name": model_name,
                "available_models": available_models or []
            }
        )


class ContextTooLongException(ChatException):
    """Raised when context exceeds maximum token limit."""
    
    def __init__(self, context_length: int, max_tokens: int):
        super().__init__(
            error_code="CHAT_003",
            message=f"Context length ({context_length} tokens) exceeds maximum ({max_tokens} tokens)",
            status_code=400,
            details={
                "context_length": context_length,
                "max_tokens": max_tokens
            }
        )


class ResponseGenerationException(ChatException):
    """Raised when response generation fails."""
    
    def __init__(self, model_name: str, error_details: str = None):
        super().__init__(
            error_code="CHAT_004",
            message=f"Failed to generate response using model '{model_name}'",
            status_code=500,
            details={
                "model_name": model_name,
                "error_details": error_details
            }
        )


# Configuration Exceptions
class ConfigurationException(APIException):
    """Base exception for configuration errors."""
    pass


class EmbeddingModelNotFoundException(ConfigurationException):
    """Raised when embedding model is not found."""
    
    def __init__(self, model_name: str, available_models: list = None):
        super().__init__(
            error_code="CONFIG_001",
            message=f"Embedding model '{model_name}' not found",
            status_code=404,
            details={
                "model_name": model_name,
                "available_models": available_models or []
            }
        )


class InvalidConfigurationException(ConfigurationException):
    """Raised when configuration is invalid."""
    
    def __init__(self, config_key: str, config_value: Any, reason: str = None):
        super().__init__(
            error_code="CONFIG_002",
            message=f"Invalid configuration for '{config_key}': {reason or 'Invalid value'}",
            status_code=400,
            details={
                "config_key": config_key,
                "config_value": str(config_value),
                "reason": reason
            }
        )


class ModelSwitchException(ConfigurationException):
    """Raised when model switching fails."""
    
    def __init__(self, from_model: str, to_model: str, error_details: str = None):
        super().__init__(
            error_code="CONFIG_003",
            message=f"Failed to switch from model '{from_model}' to '{to_model}'",
            status_code=500,
            details={
                "from_model": from_model,
                "to_model": to_model,
                "error_details": error_details
            }
        )


class ConfigurationError(ConfigurationException):
    """Raised when configuration operation fails."""
    
    def __init__(self, message: str, error_details: str = None):
        super().__init__(
            error_code="CONFIG_004",
            message=message,
            status_code=500,
            details={
                "error_details": error_details
            }
        )


# Database Exceptions
class DatabaseException(APIException):
    """Base exception for database errors."""
    pass


class DatabaseError(DatabaseException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str, error_details: str = None):
        super().__init__(
            error_code="DATABASE_001",
            message=message,
            status_code=500,
            details={
                "error_details": error_details
            }
        )


class DocumentNotFoundException(DatabaseException):
    """Raised when document is not found in database."""
    
    def __init__(self, document_id: str):
        super().__init__(
            error_code="DB_001",
            message=f"Document with ID '{document_id}' not found",
            status_code=404,
            details={
                "document_id": document_id
            }
        )


class DatabaseConnectionException(DatabaseException):
    """Raised when database connection fails."""
    
    def __init__(self, database_type: str, error_details: str = None):
        super().__init__(
            error_code="DB_002",
            message=f"Failed to connect to {database_type} database",
            status_code=503,
            details={
                "database_type": database_type,
                "error_details": error_details
            }
        )


class DatabaseOperationException(DatabaseException):
    """Raised when database operation fails."""
    
    def __init__(self, operation: str, error_details: str = None):
        super().__init__(
            error_code="DB_003",
            message=f"Database operation '{operation}' failed",
            status_code=500,
            details={
                "operation": operation,
                "error_details": error_details
            }
        )


# Vector Database Exceptions
class VectorDatabaseError(APIException):
    """Raised when vector database operation fails."""
    
    def __init__(self, message: str, error_details: str = None):
        super().__init__(
            error_code="VECTOR_DB_001",
            message=message,
            status_code=500,
            details={
                "error_details": error_details
            }
        )


# Embedding Service Exceptions
class EmbeddingServiceError(APIException):
    """Base exception for embedding service errors."""
    
    def __init__(self, message: str, error_details: str = None):
        super().__init__(
            error_code="EMBEDDING_001",
            message=message,
            status_code=500,
            details={
                "error_details": error_details
            }
        )


class ModelNotFoundError(EmbeddingServiceError):
    """Raised when embedding model is not found."""
    
    def __init__(self, model_key: str, available_models: list = None):
        super().__init__(
            message=f"Embedding model '{model_key}' not found",
            error_details=f"Available models: {available_models or []}"
        )
        self.error_code = "EMBEDDING_002"
        self.status_code = 404


class ModelLoadError(EmbeddingServiceError):
    """Raised when embedding model fails to load."""
    
    def __init__(self, model_key: str, error_details: str = None):
        super().__init__(
            message=f"Failed to load embedding model '{model_key}'",
            error_details=error_details
        )
        self.error_code = "EMBEDDING_003"
        self.status_code = 500


# Validation Exceptions
class ValidationError(APIException):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(
            error_code="VALIDATION_001",
            message=message,
            status_code=422,
            details={
                "field": field,
                "value": str(value) if value is not None else None
            }
        )


class ValidationException(APIException):
    """Raised when data validation fails."""
    
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            error_code="VALIDATION_002",
            message=f"Validation failed for field '{field}': {reason}",
            status_code=422,
            details={
                "field": field,
                "value": str(value),
                "reason": reason
            }
        )