"""Tests for data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import (
    Document, DocumentType, ProcessingStatus,
    Chunk, SearchResult, SearchQuery,
    ChatMessage, Conversation, MessageRole,
    EmbeddingModelInfo, OllamaModelInfo
)


class TestDocument:
    """Test Document model."""
    
    def test_document_creation(self):
        """Test creating a valid document."""
        doc = Document(
            filename="test.pdf",
            file_type=DocumentType.PDF,
            file_size=1024000,
            embedding_model="test-model"
        )
        
        assert doc.filename == "test.pdf"
        assert doc.file_type == DocumentType.PDF
        assert doc.file_size == 1024000
        assert doc.processing_status == ProcessingStatus.PENDING
        assert doc.chunk_count == 0
        assert doc.file_size_mb == pytest.approx(0.976, rel=1e-2)
    
    def test_document_validation_errors(self):
        """Test document validation errors."""
        # Empty filename
        with pytest.raises(ValidationError):
            Document(
                filename="",
                file_type=DocumentType.PDF,
                file_size=1024000
            )
        
        # Negative file size
        with pytest.raises(ValidationError):
            Document(
                filename="test.pdf",
                file_type=DocumentType.PDF,
                file_size=-1
            )
    
    def test_document_properties(self):
        """Test document properties."""
        doc = Document(
            filename="test.pdf",
            file_type=DocumentType.PDF,
            file_size=1024000,
            processing_status=ProcessingStatus.COMPLETED,
            chunk_count=5
        )
        
        assert doc.is_processed is True
        assert doc.has_chunks is True


class TestChunk:
    """Test Chunk model."""
    
    def test_chunk_creation(self):
        """Test creating a valid chunk."""
        chunk = Chunk(
            document_id="doc-123",
            content="This is test content",
            start_index=0,
            end_index=20,
            chunk_index=0
        )
        
        assert chunk.document_id == "doc-123"
        assert chunk.content == "This is test content"
        assert chunk.content_length == 20
        assert chunk.character_range == (0, 20)
        assert chunk.has_embedding is False
    
    def test_chunk_validation_errors(self):
        """Test chunk validation errors."""
        # End index before start index
        with pytest.raises(ValidationError):
            Chunk(
                document_id="doc-123",
                content="Test content",
                start_index=10,
                end_index=5,
                chunk_index=0
            )
        
        # Empty content
        with pytest.raises(ValidationError):
            Chunk(
                document_id="doc-123",
                content="",
                start_index=0,
                end_index=10,
                chunk_index=0
            )


class TestSearchQuery:
    """Test SearchQuery model."""
    
    def test_search_query_creation(self):
        """Test creating a valid search query."""
        query = SearchQuery(
            query="test search",
            top_k=5,
            min_similarity=0.7
        )
        
        assert query.query == "test search"
        assert query.top_k == 5
        assert query.min_similarity == 0.7
    
    def test_search_query_validation(self):
        """Test search query validation."""
        # Empty query
        with pytest.raises(ValidationError):
            SearchQuery(query="")
        
        # Invalid top_k
        with pytest.raises(ValidationError):
            SearchQuery(query="test", top_k=0)
        
        # Invalid similarity score
        with pytest.raises(ValidationError):
            SearchQuery(query="test", min_similarity=1.5)


class TestChatMessage:
    """Test ChatMessage model."""
    
    def test_chat_message_creation(self):
        """Test creating a valid chat message."""
        message = ChatMessage(
            conversation_id="conv-123",
            content="Hello, how are you?",
            role=MessageRole.USER
        )
        
        assert message.conversation_id == "conv-123"
        assert message.content == "Hello, how are you?"
        assert message.role == MessageRole.USER
        assert message.is_user_message is True
        assert message.is_assistant_message is False
        assert message.has_sources is False
    
    def test_chat_message_validation(self):
        """Test chat message validation."""
        # Empty content
        with pytest.raises(ValidationError):
            ChatMessage(
                conversation_id="conv-123",
                content="",
                role=MessageRole.USER
            )


class TestConversation:
    """Test Conversation model."""
    
    def test_conversation_creation(self):
        """Test creating a valid conversation."""
        conv = Conversation(title="Test Conversation")
        
        assert conv.title == "Test Conversation"
        assert conv.message_count == 0
        assert conv.is_active is True
        assert conv.has_messages is False
    
    def test_conversation_update_last_message(self):
        """Test updating last message timestamp."""
        conv = Conversation(title="Test Conversation")
        timestamp = datetime.now()
        
        conv.update_last_message(timestamp)
        
        assert conv.last_message_at == timestamp
        assert conv.message_count == 1


class TestEmbeddingModelInfo:
    """Test EmbeddingModelInfo model."""
    
    def test_embedding_model_creation(self):
        """Test creating a valid embedding model info."""
        model = EmbeddingModelInfo(
            key="test-model",
            name="Test Model",
            dimensions=384,
            model_size="22MB",
            max_sequence_length=512
        )
        
        assert model.key == "test-model"
        assert model.name == "Test Model"
        assert model.dimensions == 384
        assert model.is_active is False
    
    def test_embedding_model_key_validation(self):
        """Test embedding model key validation."""
        # Invalid characters in key
        with pytest.raises(ValidationError):
            EmbeddingModelInfo(
                key="test model!",
                name="Test Model",
                dimensions=384,
                model_size="22MB",
                max_sequence_length=512
            )


class TestOllamaModelInfo:
    """Test OllamaModelInfo model."""
    
    def test_ollama_model_creation(self):
        """Test creating a valid Ollama model info."""
        model = OllamaModelInfo(
            name="llama2:7b",
            size="7B",
            family="llama"
        )
        
        assert model.name == "llama2:7b"
        assert model.size == "7B"
        assert model.family == "llama"
        assert model.is_available is False