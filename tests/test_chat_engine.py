"""Tests for chat engine."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.chat_engine import ChatEngine, ChatContextError
from app.services.ollama_client import OllamaClient
from app.services.conversation_manager import ConversationManager
from app.services.prompt_templates import PromptBuilder
from app.services.search_engine import SearchEngine
from app.models.chat import (
    ChatRequest, ChatResponse, MessageRole, ConversationCreateRequest,
    StreamingChatResponse
)
from app.models.search import SearchResult, SearchResponse
from app.core.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.OLLAMA_MODEL = "llama2"
    settings.MAX_CONTEXT_TOKENS = 4000
    return settings


@pytest.fixture
def mock_search_engine():
    """Mock search engine."""
    search_engine = AsyncMock(spec=SearchEngine)
    return search_engine


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client."""
    ollama_client = AsyncMock(spec=OllamaClient)
    return ollama_client


@pytest.fixture
def mock_conversation_manager():
    """Mock conversation manager."""
    conv_manager = AsyncMock(spec=ConversationManager)
    return conv_manager


@pytest.fixture
def mock_prompt_builder():
    """Mock prompt builder."""
    prompt_builder = MagicMock(spec=PromptBuilder)
    prompt_builder.build_rag_prompt.return_value = "Test prompt"
    prompt_builder.get_system_prompt.return_value = "System prompt"
    prompt_builder.build_context_from_sources.return_value = "Test context"
    return prompt_builder


@pytest.fixture
def chat_engine(mock_settings, mock_search_engine, mock_ollama_client, 
                mock_conversation_manager, mock_prompt_builder):
    """Create chat engine for testing."""
    return ChatEngine(
        search_engine=mock_search_engine,
        ollama_client=mock_ollama_client,
        conversation_manager=mock_conversation_manager,
        prompt_builder=mock_prompt_builder,
        settings=mock_settings
    )


@pytest.fixture
def sample_chat_request():
    """Create sample chat request."""
    return ChatRequest(
        message="What is machine learning?",
        conversation_id=None,
        model_name="llama2",
        include_sources=True
    )


@pytest.fixture
def sample_search_results():
    """Create sample search results."""
    from app.models.chunk import Chunk
    from app.models.document import Document
    
    # Mock objects
    chunk = MagicMock(spec=Chunk)
    chunk.content = "Machine learning is a subset of AI."
    chunk.id = "chunk1"
    
    document = MagicMock(spec=Document)
    document.filename = "ml_guide.pdf"
    document.id = "doc1"
    
    result = MagicMock(spec=SearchResult)
    result.chunk = chunk
    result.document = document
    result.similarity_score = 0.85
    
    search_response = MagicMock(spec=SearchResponse)
    search_response.results = [result]
    search_response.total_results = 1
    
    return [result]


class TestChatEngine:
    """Test ChatEngine class."""
    
    def test_initialization(self, chat_engine, mock_settings):
        """Test chat engine initialization."""
        assert chat_engine is not None
        assert chat_engine.default_model == "llama2"
        assert chat_engine.max_context_tokens == 4000
    
    @pytest.mark.asyncio
    async def test_process_message_new_conversation(
        self, chat_engine, sample_chat_request, sample_search_results,
        mock_conversation_manager, mock_search_engine, mock_ollama_client
    ):
        """Test processing message with new conversation."""
        # Mock conversation creation
        from app.models.chat import Conversation, ChatMessage
        
        mock_conversation = MagicMock(spec=Conversation)
        mock_conversation.id = "conv1"
        mock_conversation.title = "Test Conversation"
        mock_conversation.model_name = "llama2"
        mock_conversation.system_prompt = None
        
        mock_user_message = MagicMock(spec=ChatMessage)
        mock_user_message.id = "msg1"
        mock_user_message.content = "What is machine learning?"
        mock_user_message.role = MessageRole.USER
        
        mock_assistant_message = MagicMock(spec=ChatMessage)
        mock_assistant_message.id = "msg2"
        mock_assistant_message.content = "Machine learning is..."
        mock_assistant_message.role = MessageRole.ASSISTANT
        
        # Setup mocks
        mock_conversation_manager.create_conversation.return_value = mock_conversation
        mock_conversation_manager.add_message.side_effect = [
            mock_user_message, mock_assistant_message
        ]
        mock_conversation_manager.get_conversation_history.return_value = [mock_user_message]
        mock_conversation_manager.get_conversation.return_value = mock_conversation
        
        # Mock search
        chat_engine._retrieve_context = AsyncMock(return_value=sample_search_results)
        
        # Mock generation
        chat_engine._generate_response = AsyncMock(return_value=(
            "Machine learning is a subset of AI that enables computers to learn.",
            {"total_tokens": 50, "prompt_tokens": 30}
        ))
        
        # Process message
        response = await chat_engine.process_message(sample_chat_request)
        
        # Verify response
        assert isinstance(response, ChatResponse)
        assert response.message == mock_assistant_message
        assert response.conversation == mock_conversation
        assert response.sources_used == sample_search_results
        
        # Verify calls
        mock_conversation_manager.create_conversation.assert_called_once()
        mock_conversation_manager.add_message.assert_called()
        chat_engine._retrieve_context.assert_called_once()
        chat_engine._generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_existing_conversation(
        self, chat_engine, sample_chat_request, sample_search_results,
        mock_conversation_manager
    ):
        """Test processing message with existing conversation."""
        # Set existing conversation ID
        sample_chat_request.conversation_id = "existing_conv"
        
        from app.models.chat import Conversation, ChatMessage
        
        mock_conversation = MagicMock(spec=Conversation)
        mock_conversation.id = "existing_conv"
        mock_conversation.title = "Existing Conversation"
        
        mock_message = MagicMock(spec=ChatMessage)
        
        # Setup mocks
        mock_conversation_manager.get_conversation.return_value = mock_conversation
        mock_conversation_manager.add_message.return_value = mock_message
        mock_conversation_manager.get_conversation_history.return_value = []
        
        chat_engine._retrieve_context = AsyncMock(return_value=sample_search_results)
        chat_engine._generate_response = AsyncMock(return_value=(
            "Response text", {"total_tokens": 50}
        ))
        
        # Process message
        response = await chat_engine.process_message(sample_chat_request)
        
        # Verify that existing conversation was used
        mock_conversation_manager.get_conversation.assert_called_with("existing_conv")
        mock_conversation_manager.create_conversation.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_stream_message(
        self, chat_engine, sample_chat_request, sample_search_results,
        mock_conversation_manager
    ):
        """Test streaming message response."""
        from app.models.chat import Conversation, ChatMessage
        
        mock_conversation = MagicMock(spec=Conversation)
        mock_conversation.id = "conv1"
        
        mock_user_message = MagicMock(spec=ChatMessage)
        mock_assistant_message = MagicMock(spec=ChatMessage)
        
        # Setup mocks
        mock_conversation_manager.create_conversation.return_value = mock_conversation
        mock_conversation_manager.add_message.side_effect = [
            mock_user_message, mock_assistant_message
        ]
        mock_conversation_manager.get_conversation_history.return_value = []
        
        chat_engine._retrieve_context = AsyncMock(return_value=sample_search_results)
        
        # Mock streaming response
        async def mock_stream_response(*args, **kwargs):
            yield {"message": {"content": "Hello"}, "done": False}
            yield {"message": {"content": " there"}, "done": False}
            yield {"message": {"content": "!"}, "done": True, "eval_count": 10}
        
        chat_engine._stream_response = mock_stream_response
        
        # Collect streaming responses
        responses = []
        async for chunk in chat_engine.stream_message(sample_chat_request):
            responses.append(chunk)
        
        # Verify streaming responses
        assert len(responses) >= 3  # At least 3 chunks
        
        # Check that we got content deltas
        content_chunks = [r for r in responses if not r.is_complete]
        assert len(content_chunks) >= 2
        
        # Check final chunk
        final_chunks = [r for r in responses if r.is_complete]
        assert len(final_chunks) == 1
        assert final_chunks[0].sources is not None
    
    @pytest.mark.asyncio
    async def test_retrieve_context(self, chat_engine, mock_search_engine, sample_search_results):
        """Test context retrieval."""
        # Mock search engine response
        mock_search_response = MagicMock()
        mock_search_response.results = sample_search_results
        mock_search_engine.semantic_search.return_value = mock_search_response
        
        # Retrieve context
        results = await chat_engine._retrieve_context("test query", max_tokens=1000)
        
        # Verify search was called
        mock_search_engine.semantic_search.assert_called_once_with(
            query="test query",
            top_k=10,
            min_similarity=0.3
        )
        
        # Verify results
        assert results == sample_search_results
    
    @pytest.mark.asyncio
    async def test_retrieve_context_error_handling(self, chat_engine, mock_search_engine):
        """Test context retrieval error handling."""
        # Mock search engine to raise exception
        mock_search_engine.semantic_search.side_effect = Exception("Search failed")
        
        # Should return empty list on error
        results = await chat_engine._retrieve_context("test query")
        assert results == []
    
    @pytest.mark.asyncio
    async def test_generate_response(self, chat_engine, mock_ollama_client, mock_prompt_builder):
        """Test response generation."""
        # Mock Ollama response
        async def mock_chat(*args, **kwargs):
            yield {
                "message": {"content": "This is a test response."},
                "done": True,
                "eval_count": 20,
                "prompt_eval_count": 15
            }
        
        mock_ollama_client.chat = mock_chat
        mock_ollama_client.__aenter__ = AsyncMock(return_value=mock_ollama_client)
        mock_ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        # Generate response
        response_text, stats = await chat_engine._generate_response(
            question="What is AI?",
            context="AI is artificial intelligence.",
            conversation_history=[],
            model_name="llama2"
        )
        
        # Verify response
        assert response_text == "This is a test response."
        assert stats["total_tokens"] == 20
        assert stats["prompt_tokens"] == 15
        
        # Verify prompt building was called
        mock_prompt_builder.build_rag_prompt.assert_called_once()
        mock_prompt_builder.get_system_prompt.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_with_history(self, chat_engine, mock_ollama_client):
        """Test response generation with conversation history."""
        from app.models.chat import ChatMessage
        
        # Create mock history
        history = [
            MagicMock(spec=ChatMessage, role=MessageRole.USER, content="Hello"),
            MagicMock(spec=ChatMessage, role=MessageRole.ASSISTANT, content="Hi there!")
        ]
        
        # Mock Ollama response
        async def mock_chat(*args, **kwargs):
            # Verify that history was included in messages
            messages = kwargs.get("messages", [])
            assert len(messages) >= 3  # System + history + current
            yield {"message": {"content": "Response with history."}, "done": True}
        
        mock_ollama_client.chat = mock_chat
        mock_ollama_client.__aenter__ = AsyncMock(return_value=mock_ollama_client)
        mock_ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        # Generate response
        response_text, _ = await chat_engine._generate_response(
            question="Continue our conversation",
            context="Some context",
            conversation_history=history,
            model_name="llama2"
        )
        
        assert response_text == "Response with history."
    
    @pytest.mark.asyncio
    async def test_generate_response_error_handling(self, chat_engine, mock_ollama_client):
        """Test response generation error handling."""
        from app.services.ollama_client import OllamaModelError
        
        # Mock Ollama to raise error
        async def mock_chat(*args, **kwargs):
            raise OllamaModelError("Model not found")
        
        mock_ollama_client.chat = mock_chat
        mock_ollama_client.__aenter__ = AsyncMock(return_value=mock_ollama_client)
        mock_ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        # Should raise ChatContextError
        with pytest.raises(ChatContextError) as exc_info:
            await chat_engine._generate_response(
                question="Test",
                context="Test",
                conversation_history=[],
                model_name="llama2"
            )
        
        assert "Model error" in str(exc_info.value)
    
    def test_generate_conversation_title(self, chat_engine):
        """Test conversation title generation."""
        # Test normal message
        title = chat_engine._generate_conversation_title(
            "What is machine learning and how does it work?"
        )
        assert "What is machine learning and" in title
        assert len(title) <= 50
        
        # Test very long message
        long_message = "This is a very long message " * 10
        title = chat_engine._generate_conversation_title(long_message)
        assert len(title) <= 50
        assert title.endswith("...")
        
        # Test empty message
        title = chat_engine._generate_conversation_title("")
        assert "Chat" in title
    
    @pytest.mark.asyncio
    async def test_get_available_models(self, chat_engine, mock_ollama_client):
        """Test getting available models."""
        from app.services.ollama_client import OllamaModelInfo
        
        # Mock model list
        mock_models = [
            OllamaModelInfo("llama2", size="3.8GB", digest="abc123"),
            OllamaModelInfo("codellama", size="7.3GB", digest="def456")
        ]
        
        mock_ollama_client.list_models.return_value = mock_models
        mock_ollama_client.__aenter__ = AsyncMock(return_value=mock_ollama_client)
        mock_ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        # Get models
        models = await chat_engine.get_available_models()
        
        assert len(models) == 2
        assert models[0]["name"] == "llama2"
        assert models[1]["name"] == "codellama"
    
    @pytest.mark.asyncio
    async def test_get_available_models_error(self, chat_engine, mock_ollama_client):
        """Test getting available models with error."""
        # Mock error
        mock_ollama_client.list_models.side_effect = Exception("Connection failed")
        mock_ollama_client.__aenter__ = AsyncMock(return_value=mock_ollama_client)
        mock_ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        # Should return empty list on error
        models = await chat_engine.get_available_models()
        assert models == []
    
    @pytest.mark.asyncio
    async def test_validate_model(self, chat_engine, mock_ollama_client):
        """Test model validation."""
        # Mock validation result
        mock_result = {
            "valid": True,
            "available": True,
            "model_info": {"name": "llama2"}
        }
        
        mock_ollama_client.validate_model.return_value = mock_result
        mock_ollama_client.__aenter__ = AsyncMock(return_value=mock_ollama_client)
        mock_ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        # Validate model
        result = await chat_engine.validate_model("llama2")
        
        assert result["valid"] is True
        assert result["available"] is True
        mock_ollama_client.validate_model.assert_called_once_with("llama2")
    
    @pytest.mark.asyncio
    async def test_validate_model_error(self, chat_engine, mock_ollama_client):
        """Test model validation with error."""
        # Mock error
        mock_ollama_client.validate_model.side_effect = Exception("Validation failed")
        mock_ollama_client.__aenter__ = AsyncMock(return_value=mock_ollama_client)
        mock_ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        # Should return error result
        result = await chat_engine.validate_model("llama2")
        
        assert result["valid"] is False
        assert result["available"] is False
        assert "Validation failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_health_check(self, chat_engine, mock_ollama_client, mock_search_engine):
        """Test health check."""
        # Mock healthy services
        mock_ollama_client.health_check.return_value = True
        mock_ollama_client.__aenter__ = AsyncMock(return_value=mock_ollama_client)
        mock_ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_search_engine.semantic_search.return_value = MagicMock()
        
        # Perform health check
        health = await chat_engine.health_check()
        
        assert health["ollama"] is True
        assert health["search_engine"] is True
        assert health["conversation_manager"] is True
        assert health["overall"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, chat_engine, mock_ollama_client, mock_search_engine):
        """Test health check with unhealthy services."""
        # Mock unhealthy services
        mock_ollama_client.health_check.return_value = False
        mock_ollama_client.__aenter__ = AsyncMock(return_value=mock_ollama_client)
        mock_ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_search_engine.semantic_search.side_effect = Exception("Search failed")
        
        # Perform health check
        health = await chat_engine.health_check()
        
        assert health["ollama"] is False
        assert health["search_engine"] is False
        assert health["conversation_manager"] is True  # Always true (file-based)
        assert health["overall"] is False
    
    @pytest.mark.asyncio
    async def test_process_message_error_handling(
        self, chat_engine, sample_chat_request, mock_conversation_manager
    ):
        """Test error handling in process_message."""
        from app.models.chat import Conversation, ChatMessage
        
        mock_conversation = MagicMock(spec=Conversation)
        mock_conversation.id = "conv1"
        
        mock_user_message = MagicMock(spec=ChatMessage)
        
        # Setup mocks to succeed initially
        mock_conversation_manager.create_conversation.return_value = mock_conversation
        mock_conversation_manager.add_message.side_effect = [
            mock_user_message,  # First call succeeds (user message)
            Exception("Database error")  # Second call fails (assistant message)
        ]
        mock_conversation_manager.get_conversation_history.return_value = []
        
        chat_engine._retrieve_context = AsyncMock(return_value=[])
        chat_engine._generate_response = AsyncMock(return_value=("Response", {}))
        
        # Should raise the exception
        with pytest.raises(Exception) as exc_info:
            await chat_engine.process_message(sample_chat_request)
        
        assert "Database error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_chat_request_validation(self, chat_engine):
        """Test chat request validation."""
        # Test with invalid request (empty message)
        with pytest.raises(Exception):  # Pydantic validation error
            ChatRequest(message="", conversation_id=None)
        
        # Test with valid request
        request = ChatRequest(
            message="Valid message",
            conversation_id=None,
            max_context_tokens=2000,
            include_sources=False,
            stream=True
        )
        
        assert request.message == "Valid message"
        assert request.max_context_tokens == 2000
        assert request.include_sources is False
        assert request.stream is True