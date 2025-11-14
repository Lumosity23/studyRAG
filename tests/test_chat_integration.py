"""Integration tests for chat functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import shutil
from pathlib import Path

from app.services.chat_engine import ChatEngine
from app.services.ollama_client import OllamaClient
from app.services.conversation_manager import ConversationManager
from app.services.prompt_templates import PromptBuilder
from app.services.search_engine import SearchEngine
from app.models.chat import ChatRequest, MessageRole
from app.core.config import Settings


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_settings(temp_dir):
    """Mock settings for integration testing."""
    settings = MagicMock(spec=Settings)
    settings.OLLAMA_MODEL = "llama2"
    settings.MAX_CONTEXT_TOKENS = 4000
    settings.PROCESSED_DIR = str(temp_dir)
    settings.ollama_url = "http://localhost:11434"
    settings.OLLAMA_TIMEOUT = 30
    return settings


@pytest.fixture
def integrated_chat_engine(mock_settings):
    """Create integrated chat engine with real components."""
    # Create real components (but with mocked external dependencies)
    search_engine = MagicMock(spec=SearchEngine)
    ollama_client = MagicMock(spec=OllamaClient)
    conversation_manager = ConversationManager(mock_settings)
    prompt_builder = PromptBuilder()
    
    return ChatEngine(
        search_engine=search_engine,
        ollama_client=ollama_client,
        conversation_manager=conversation_manager,
        prompt_builder=prompt_builder,
        settings=mock_settings
    )


class TestChatIntegration:
    """Integration tests for chat functionality."""
    
    @pytest.mark.asyncio
    async def test_full_chat_workflow(self, integrated_chat_engine):
        """Test complete chat workflow from request to response."""
        # Mock search results
        from app.models.search import SearchResult
        from app.models.chunk import Chunk
        from app.models.document import Document
        
        mock_chunk = MagicMock(spec=Chunk)
        mock_chunk.content = "Machine learning is a subset of artificial intelligence."
        mock_chunk.id = "chunk1"
        
        mock_document = MagicMock(spec=Document)
        mock_document.filename = "ml_guide.pdf"
        mock_document.id = "doc1"
        
        mock_result = MagicMock(spec=SearchResult)
        mock_result.chunk = mock_chunk
        mock_result.document = mock_document
        mock_result.similarity_score = 0.85
        
        # Mock search engine
        integrated_chat_engine.search_engine.semantic_search = AsyncMock()
        mock_search_response = MagicMock()
        mock_search_response.results = [mock_result]
        integrated_chat_engine.search_engine.semantic_search.return_value = mock_search_response
        
        # Mock Ollama client
        async def mock_chat(*args, **kwargs):
            yield {
                "message": {"content": "Machine learning is indeed a subset of AI that enables computers to learn from data."},
                "done": True,
                "eval_count": 25,
                "prompt_eval_count": 15
            }
        
        integrated_chat_engine.ollama_client.chat = mock_chat
        integrated_chat_engine.ollama_client.__aenter__ = AsyncMock(return_value=integrated_chat_engine.ollama_client)
        integrated_chat_engine.ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        # Create chat request
        request = ChatRequest(
            message="What is machine learning?",
            conversation_id=None,
            include_sources=True
        )
        
        # Process the message
        response = await integrated_chat_engine.process_message(request)
        
        # Verify response structure
        assert response is not None
        assert response.message is not None
        assert response.conversation is not None
        assert response.sources_used is not None
        assert len(response.sources_used) == 1
        
        # Verify conversation was created
        assert response.conversation.title is not None
        assert response.conversation.message_count == 2  # User + Assistant
        
        # Verify message content
        assert response.message.role == MessageRole.ASSISTANT
        assert "machine learning" in response.message.content.lower()
        
        # Verify sources
        assert response.sources_used[0].chunk.content == mock_chunk.content
    
    @pytest.mark.asyncio
    async def test_conversation_persistence(self, integrated_chat_engine):
        """Test that conversations persist correctly."""
        # Mock external dependencies
        integrated_chat_engine.search_engine.semantic_search = AsyncMock()
        mock_search_response = MagicMock()
        mock_search_response.results = []
        integrated_chat_engine.search_engine.semantic_search.return_value = mock_search_response
        
        async def mock_chat(*args, **kwargs):
            yield {"message": {"content": "Hello there!"}, "done": True}
        
        integrated_chat_engine.ollama_client.chat = mock_chat
        integrated_chat_engine.ollama_client.__aenter__ = AsyncMock(return_value=integrated_chat_engine.ollama_client)
        integrated_chat_engine.ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        # First message - creates new conversation
        request1 = ChatRequest(message="Hello", conversation_id=None)
        response1 = await integrated_chat_engine.process_message(request1)
        
        conversation_id = response1.conversation.id
        
        # Second message - continues existing conversation
        request2 = ChatRequest(message="How are you?", conversation_id=conversation_id)
        response2 = await integrated_chat_engine.process_message(request2)
        
        # Verify same conversation
        assert response2.conversation.id == conversation_id
        assert response2.conversation.message_count == 4  # 2 user + 2 assistant
        
        # Verify conversation history is maintained
        history = await integrated_chat_engine.conversation_manager.get_conversation_history(conversation_id)
        assert len(history) == 4
        assert history[0].content == "Hello"
        assert history[2].content == "How are you?"
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, integrated_chat_engine):
        """Test streaming chat response."""
        # Mock dependencies
        integrated_chat_engine.search_engine.semantic_search = AsyncMock()
        mock_search_response = MagicMock()
        mock_search_response.results = []
        integrated_chat_engine.search_engine.semantic_search.return_value = mock_search_response
        
        # Mock streaming response
        async def mock_stream_response(*args, **kwargs):
            yield {"message": {"content": "Hello"}, "done": False}
            yield {"message": {"content": " there"}, "done": False}
            yield {"message": {"content": "!"}, "done": True, "eval_count": 5}
        
        integrated_chat_engine._stream_response = mock_stream_response
        
        # Stream message
        request = ChatRequest(message="Hello", stream=True)
        
        chunks = []
        async for chunk in integrated_chat_engine.stream_message(request):
            chunks.append(chunk)
        
        # Verify streaming chunks
        assert len(chunks) >= 3
        
        # Check content deltas
        content_chunks = [c for c in chunks if not c.is_complete]
        assert len(content_chunks) >= 2
        
        # Check final chunk
        final_chunks = [c for c in chunks if c.is_complete]
        assert len(final_chunks) == 1
    
    @pytest.mark.asyncio
    async def test_prompt_building_integration(self, integrated_chat_engine):
        """Test that prompt building works correctly with real components."""
        # Create a conversation with history
        from app.models.chat import ConversationCreateRequest
        
        conv_request = ConversationCreateRequest(
            title="Test Conversation",
            system_prompt="You are a helpful AI assistant."
        )
        
        conversation = await integrated_chat_engine.conversation_manager.create_conversation(conv_request)
        
        # Add some history
        await integrated_chat_engine.conversation_manager.add_message(
            conversation.id, "What is AI?", MessageRole.USER
        )
        await integrated_chat_engine.conversation_manager.add_message(
            conversation.id, "AI is artificial intelligence.", MessageRole.ASSISTANT
        )
        
        # Test prompt building with history
        history = await integrated_chat_engine.conversation_manager.get_conversation_history(conversation.id)
        
        prompt = integrated_chat_engine.prompt_builder.build_rag_prompt(
            question="Can you elaborate on that?",
            context="AI involves machine learning and neural networks.",
            conversation_history=history
        )
        
        # Verify prompt contains history and context
        assert "What is AI?" in prompt
        assert "AI is artificial intelligence" in prompt
        assert "Can you elaborate on that?" in prompt
        assert "machine learning" in prompt
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, integrated_chat_engine):
        """Test error handling in integrated system."""
        # Mock search to fail
        integrated_chat_engine.search_engine.semantic_search = AsyncMock(side_effect=Exception("Search failed"))
        
        # Mock Ollama to work
        async def mock_chat(*args, **kwargs):
            yield {"message": {"content": "I can still respond without search."}, "done": True}
        
        integrated_chat_engine.ollama_client.chat = mock_chat
        integrated_chat_engine.ollama_client.__aenter__ = AsyncMock(return_value=integrated_chat_engine.ollama_client)
        integrated_chat_engine.ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        # Should still work even if search fails
        request = ChatRequest(message="Hello")
        response = await integrated_chat_engine.process_message(request)
        
        # Verify response was generated despite search failure
        assert response is not None
        assert response.message.content == "I can still respond without search."
        assert response.sources_used == []  # No sources due to search failure
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, integrated_chat_engine):
        """Test health check with real components."""
        # Mock healthy services
        integrated_chat_engine.ollama_client.health_check = AsyncMock(return_value=True)
        integrated_chat_engine.ollama_client.__aenter__ = AsyncMock(return_value=integrated_chat_engine.ollama_client)
        integrated_chat_engine.ollama_client.__aexit__ = AsyncMock(return_value=None)
        
        integrated_chat_engine.search_engine.semantic_search = AsyncMock()
        mock_search_response = MagicMock()
        mock_search_response.results = []
        integrated_chat_engine.search_engine.semantic_search.return_value = mock_search_response
        
        # Perform health check
        health = await integrated_chat_engine.health_check()
        
        # Verify all components are healthy
        assert health["ollama"] is True
        assert health["search_engine"] is True
        assert health["conversation_manager"] is True
        assert health["overall"] is True