"""Tests for custom exceptions."""

import pytest
from datetime import datetime

from app.core.exceptions import (
    APIException,
    UnsupportedFileTypeException,
    FileSizeExceededException,
    CorruptedFileException,
    InvalidQueryException,
    NoResultsFoundException,
    OllamaConnectionException,
    EmbeddingModelNotFoundException
)


class TestAPIException:
    """Test base API exception."""
    
    def test_api_exception_creation(self):
        """Test creating an API exception."""
        exc = APIException(
            error_code="TEST_001",
            message="Test error message",
            status_code=400,
            details={"key": "value"}
        )
        
        assert exc.error_code == "TEST_001"
        assert exc.message == "Test error message"
        assert exc.status_code == 400
        assert exc.details == {"key": "value"}
        assert isinstance(exc.timestamp, datetime)
    
    def test_api_exception_defaults(self):
        """Test API exception with default values."""
        exc = APIException(
            error_code="TEST_001",
            message="Test error message"
        )
        
        assert exc.status_code == 500
        assert exc.details == {}


class TestDocumentProcessingExceptions:
    """Test document processing exceptions."""
    
    def test_unsupported_file_type_exception(self):
        """Test UnsupportedFileTypeException."""
        exc = UnsupportedFileTypeException("xyz", ["pdf", "docx"])
        
        assert exc.error_code == "DOC_001"
        assert exc.status_code == 400
        assert "xyz" in exc.message
        assert exc.details["file_type"] == "xyz"
        assert exc.details["supported_types"] == ["pdf", "docx"]
    
    def test_file_size_exceeded_exception(self):
        """Test FileSizeExceededException."""
        exc = FileSizeExceededException(60000000, 50000000)
        
        assert exc.error_code == "DOC_002"
        assert exc.status_code == 413
        assert exc.details["file_size"] == 60000000
        assert exc.details["max_size"] == 50000000
        assert exc.details["max_size_mb"] == pytest.approx(47.68, rel=1e-2)
    
    def test_corrupted_file_exception(self):
        """Test CorruptedFileException."""
        exc = CorruptedFileException("test.pdf", "Invalid PDF header")
        
        assert exc.error_code == "DOC_003"
        assert exc.status_code == 400
        assert exc.details["filename"] == "test.pdf"
        assert exc.details["error_details"] == "Invalid PDF header"


class TestSearchExceptions:
    """Test search exceptions."""
    
    def test_invalid_query_exception(self):
        """Test InvalidQueryException."""
        exc = InvalidQueryException("", "Query is empty")
        
        assert exc.error_code == "SEARCH_001"
        assert exc.status_code == 400
        assert exc.details["query"] == ""
        assert exc.details["reason"] == "Query is empty"
    
    def test_no_results_found_exception(self):
        """Test NoResultsFoundException."""
        exc = NoResultsFoundException("test query", 0.8)
        
        assert exc.error_code == "SEARCH_002"
        assert exc.status_code == 404
        assert exc.details["query"] == "test query"
        assert exc.details["min_similarity"] == 0.8


class TestChatExceptions:
    """Test chat exceptions."""
    
    def test_ollama_connection_exception(self):
        """Test OllamaConnectionException."""
        exc = OllamaConnectionException("http://localhost:11434", "Connection refused")
        
        assert exc.error_code == "CHAT_001"
        assert exc.status_code == 503
        assert exc.details["ollama_url"] == "http://localhost:11434"
        assert exc.details["error_details"] == "Connection refused"


class TestConfigurationExceptions:
    """Test configuration exceptions."""
    
    def test_embedding_model_not_found_exception(self):
        """Test EmbeddingModelNotFoundException."""
        exc = EmbeddingModelNotFoundException("unknown-model", ["model1", "model2"])
        
        assert exc.error_code == "CONFIG_001"
        assert exc.status_code == 404
        assert exc.details["model_name"] == "unknown-model"
        assert exc.details["available_models"] == ["model1", "model2"]