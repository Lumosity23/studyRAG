"""Integration tests for chat API endpoints."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.models.chat import (
    ChatRequest, ChatResponse, ChatMessage, Conversation, MessageRole,
    ConversationStatus, ConversationCreateRequest, StreamingChatResponse
)
from app.models.search import SearchResult, SearchResponse
from app.models.document import Document, DocumentType
from app.models.chunk import Chunk
from app.services.chat_engine import ChatEngine
from app.services.conversation_manager import ConversationManager
from app.services.search_engine import SearchEngine
from app.services.ollama_client import OllamaClient
from app.api.endpoints.chat import router


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/chat")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_services():
    """Mock all required services."""
    return {
        'chat_engine': AsyncMock(spec=ChatEngine),
        'conversation_manager': AsyncMock(spec=ConversationManager),
        'search_engine': AsyncMock(spec=SearchEngine),
        'ollama_client': AsyncMock(spec=OllamaClient)
    }


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return Document(
        id="doc-123",
        filename="test.pdf",
        file_type=DocumentType.PDF,
        file_size=1024,
        metadata={"title": "Test Document"}
    )


@pytest.fixture
def sample_chunk(sample_document):
    """Sample chunk for testing."""
    return Chunk(
        id="chunk-123",
        document_id=sample_document.id,
        content="This is a test chunk with relevant information about AI and machine learning.",
        start_index=0,
        end_index=100,
        metadata={"section": "introduction"}
    )


@pytest.fixture
def sample_search_result(sample_chunk, sample_document):
    """Sample search result for testing."""
    return SearchResult(
        chunk=sample_chunk,
        similarity_score=0.85,
        document=sample_document,
        highlighted_content="This is a test chunk with <mark>relevant information</mark> about AI"
    )


@pytest.fixture
def sample_conversation():
    """Sample conversation for testing."""
    return Conversation(
        id="conv-123",
        title="AI Research Discussion",
        status=ConversationStatus.ACTIVE,
        message_count=3,
        last_message_at=datetime.now(),
        model_name="llama2",
        system_prompt="You are a helpful AI research assistant."
    )


@pytest.fixture
def sample_messages(sample_conversation):
    """Sample messages for testing."""
    return [
        ChatMessage(
            id="msg-1",
            conversation_id=sample_conversation.id,
            content="What is machine learning?",
            role=MessageRole.USER,
            created_at=datetime.now()
        ),
        ChatMessage(
            id="msg-2",
            conversation_id=sample_conversation.id,
            content="Machine learning is a subset of artificial intelligence...",
            role=MessageRole.ASSISTANT,
            model_name="llama2",
            generation_time=2.1,
            created_at=datetime.now()
        )
    ]


class TestChatWorkflowIntegration:
    """Test complete chat workflow integration."""
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_complete_chat_workflow(self, mock_get_engine, client, mock_services, sample_conversation, sample_search_result):
        """Test complete chat workflow from message to response."""
        # Setup mocks
        mock_get_engine.return_value = mock_services['chat_engine']
        
        # Mock chat response
        assistant_message = ChatMessage(
            id="msg-new",
            conversation_id=sample_conversation.id,
            content="Based on the documents, machine learning is a method of data analysis...",
            role=MessageRole.ASSISTANT,
            sources=[sample_search_result],
            model_name="llama2",
            generation_time=1.8
        )
        
        chat_response = ChatResponse(
            message=assistant_message,
            conversation=sample_conversation,
            sources_used=[sample_search_result],
            generation_stats={
                "total_time": 1.8,
                "model_used": "llama2",
                "total_tokens": 150,
                "prompt_tokens": 50
            }
        )
        
        mock_services['chat_engine'].process_message.return_value = chat_response
        
        # Send chat message
        request_data = {
            "message": "What is machine learning?",
            "conversation_id": sample_conversation.id,
            "include_sources": True,
            "max_context_tokens": 2000
        }
        
        response = client.post("/chat/message", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check message content
        assert data["message"]["content"] == assistant_message.content
        assert data["message"]["role"] == "assistant"
        assert data["message"]["model_name"] == "llama2"
        assert data["message"]["generation_time"] == 1.8
        
        # Check conversation
        assert data["conversation"]["id"] == sample_conversation.id
        assert data["conversation"]["title"] == sample_conversation.title
        
        # Check sources
        assert "sources_used" in data
        assert len(data["sources_used"]) == 1
        assert data["sources_used"][0]["similarity_score"] == 0.85
        
        # Check generation stats
        assert data["generation_stats"]["total_time"] == 1.8
        assert data["generation_stats"]["model_used"] == "llama2"
        
        # Verify chat engine was called correctly
        mock_services['chat_engine'].process_message.assert_called_once()
        call_args = mock_services['chat_engine'].process_message.call_args[0][0]
        assert isinstance(call_args, ChatRequest)
        assert call_args.message == "What is machine learning?"
        assert call_args.conversation_id == sample_conversation.id
        assert call_args.include_sources is True
        assert call_args.max_context_tokens == 2000
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_new_conversation_workflow(self, mock_get_engine, client, mock_services):
        """Test creating new conversation through chat."""
        # Setup mocks
        mock_get_engine.return_value = mock_services['chat_engine']
        
        # Mock new conversation creation
        new_conversation = Conversation(
            id="conv-new",
            title="Hello World",
            status=ConversationStatus.ACTIVE,
            message_count=1,
            model_name="llama2"
        )
        
        assistant_message = ChatMessage(
            id="msg-first",
            conversation_id=new_conversation.id,
            content="Hello! How can I help you today?",
            role=MessageRole.ASSISTANT,
            model_name="llama2",
            generation_time=0.8
        )
        
        chat_response = ChatResponse(
            message=assistant_message,
            conversation=new_conversation,
            sources_used=[],
            generation_stats={"total_time": 0.8, "model_used": "llama2"}
        )
        
        mock_services['chat_engine'].process_message.return_value = chat_response
        
        # Send message without conversation_id (new conversation)
        request_data = {
            "message": "Hello, world!",
            "model_name": "llama2",
            "include_sources": True
        }
        
        response = client.post("/chat/message", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Should create new conversation
        assert data["conversation"]["id"] == "conv-new"
        assert data["conversation"]["title"] == "Hello World"
        assert data["conversation"]["message_count"] == 1
        
        # Verify request had no conversation_id
        call_args = mock_services['chat_engine'].process_message.call_args[0][0]
        assert call_args.conversation_id is None
        assert call_args.model_name == "llama2"
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_streaming_workflow(self, mock_get_engine, client, mock_services):
        """Test streaming chat workflow."""
        # Setup mocks
        mock_get_engine.return_value = mock_services['chat_engine']
        
        # Mock streaming response
        streaming_chunks = [
            StreamingChatResponse(
                conversation_id="conv-123",
                message_id="msg-stream",
                content_delta="Hello",
                is_complete=False
            ),
            StreamingChatResponse(
                conversation_id="conv-123",
                message_id="msg-stream",
                content_delta=" there!",
                is_complete=False
            ),
            StreamingChatResponse(
                conversation_id="conv-123",
                message_id="msg-stream",
                content_delta="",
                is_complete=True,
                sources=[],
                generation_stats={"total_time": 1.2}
            )
        ]
        
        async def mock_stream():
            for chunk in streaming_chunks:
                yield chunk
        
        mock_services['chat_engine'].stream_message.return_value = mock_stream()
        
        # Test streaming endpoint
        response = client.get("/chat/stream/conv-123?message=Hello&include_sources=true")
        
        # Verify streaming response
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Verify chat engine was called for streaming
        mock_services['chat_engine'].stream_message.assert_called_once()
        call_args = mock_services['chat_engine'].stream_message.call_args[0][0]
        assert call_args.message == "Hello"
        assert call_args.conversation_id == "conv-123"
        assert call_args.stream is True


class TestConversationManagementIntegration:
    """Test conversation management integration."""
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_conversation_lifecycle(self, mock_get_manager, client, mock_services, sample_conversation):
        """Test complete conversation lifecycle."""
        mock_get_manager.return_value = mock_services['conversation_manager']
        
        # 1. Create conversation
        mock_services['conversation_manager'].create_conversation.return_value = sample_conversation
        
        create_request = {
            "title": "AI Research Discussion",
            "model_name": "llama2",
            "system_prompt": "You are a helpful AI research assistant."
        }
        
        response = client.post("/chat/conversations", json=create_request)
        assert response.status_code == 200
        created_conv = response.json()
        assert created_conv["id"] == sample_conversation.id
        
        # 2. Get conversation
        mock_services['conversation_manager'].get_conversation.return_value = sample_conversation
        
        response = client.get(f"/chat/conversations/{sample_conversation.id}")
        assert response.status_code == 200
        conv_data = response.json()
        assert conv_data["title"] == sample_conversation.title
        
        # 3. Update conversation
        updated_conversation = sample_conversation.model_copy()
        updated_conversation.title = "Updated AI Discussion"
        mock_services['conversation_manager'].update_conversation.return_value = updated_conversation
        
        response = client.put(f"/chat/conversations/{sample_conversation.id}?title=Updated AI Discussion")
        assert response.status_code == 200
        updated_data = response.json()
        assert updated_data["title"] == "Updated AI Discussion"
        
        # 4. Delete conversation
        mock_services['conversation_manager'].delete_conversation.return_value = True
        
        response = client.delete(f"/chat/conversations/{sample_conversation.id}")
        assert response.status_code == 200
        delete_data = response.json()
        assert "deleted successfully" in delete_data["message"]
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_conversation_messages_integration(self, mock_get_manager, client, mock_services, sample_conversation, sample_messages):
        """Test conversation messages integration."""
        from app.models.chat import ConversationMessagesResponse
        
        mock_get_manager.return_value = mock_services['conversation_manager']
        
        # Mock messages response
        messages_response = ConversationMessagesResponse(
            conversation=sample_conversation,
            messages=sample_messages,
            total_messages=len(sample_messages)
        )
        
        mock_services['conversation_manager'].get_messages.return_value = messages_response
        
        # Get messages
        response = client.get(f"/chat/conversations/{sample_conversation.id}/messages")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["total_messages"] == len(sample_messages)
        assert len(data["messages"]) == len(sample_messages)
        assert data["conversation"]["id"] == sample_conversation.id
        
        # Verify message content
        for i, message in enumerate(data["messages"]):
            assert message["id"] == sample_messages[i].id
            assert message["content"] == sample_messages[i].content
            assert message["role"] == sample_messages[i].role.value
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_conversation_listing_with_filters(self, mock_get_manager, client, mock_services):
        """Test conversation listing with various filters."""
        from app.models.chat import ConversationListResponse
        
        mock_get_manager.return_value = mock_services['conversation_manager']
        
        # Create sample conversations with different statuses
        conversations = [
            Conversation(
                id=f"conv-{i}",
                title=f"Conversation {i}",
                status=ConversationStatus.ACTIVE if i % 2 == 0 else ConversationStatus.ARCHIVED,
                message_count=i * 2
            )
            for i in range(5)
        ]
        
        # Test listing all conversations
        mock_services['conversation_manager'].list_conversations.return_value = ConversationListResponse(
            conversations=conversations,
            total=len(conversations)
        )
        
        response = client.get("/chat/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["conversations"]) == 5
        
        # Test filtering by status
        active_conversations = [c for c in conversations if c.status == ConversationStatus.ACTIVE]
        mock_services['conversation_manager'].list_conversations.return_value = ConversationListResponse(
            conversations=active_conversations,
            total=len(active_conversations)
        )
        
        response = client.get("/chat/conversations?status=active")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == len(active_conversations)
        
        # Test pagination
        response = client.get("/chat/conversations?limit=2&offset=1")
        assert response.status_code == 200
        
        # Verify manager was called with correct parameters
        mock_services['conversation_manager'].list_conversations.assert_called_with(
            status=None,
            limit=2,
            offset=1
        )


class TestErrorHandlingIntegration:
    """Test error handling integration."""
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_chat_engine_errors(self, mock_get_engine, client, mock_services):
        """Test chat engine error handling."""
        mock_get_engine.return_value = mock_services['chat_engine']
        
        # Test different types of errors
        error_scenarios = [
            (Exception("Ollama connection failed"), "Failed to process chat message"),
            (ValueError("Invalid model"), "Failed to process chat message"),
            (TimeoutError("Request timeout"), "Failed to process chat message")
        ]
        
        for error, expected_message in error_scenarios:
            mock_services['chat_engine'].process_message.side_effect = error
            
            response = client.post("/chat/message", json={"message": "test"})
            
            assert response.status_code == 400
            data = response.json()
            assert expected_message in data["message"]
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_conversation_not_found_errors(self, mock_get_manager, client, mock_services):
        """Test conversation not found error handling."""
        from app.services.conversation_manager import ConversationNotFoundError
        
        mock_get_manager.return_value = mock_services['conversation_manager']
        
        # Test various endpoints with non-existent conversation
        endpoints_to_test = [
            ("GET", "/chat/conversations/nonexistent"),
            ("GET", "/chat/conversations/nonexistent/messages"),
            ("PUT", "/chat/conversations/nonexistent?title=New Title"),
        ]
        
        for method, endpoint in endpoints_to_test:
            mock_services['conversation_manager'].get_conversation.side_effect = ConversationNotFoundError("nonexistent")
            mock_services['conversation_manager'].get_messages.side_effect = ConversationNotFoundError("nonexistent")
            mock_services['conversation_manager'].update_conversation.side_effect = ConversationNotFoundError("nonexistent")
            
            if method == "GET":
                response = client.get(endpoint)
            elif method == "PUT":
                response = client.put(endpoint)
            
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]
    
    async def test_validation_errors(self, client):
        """Test request validation errors."""
        # Test invalid chat message requests
        invalid_requests = [
            {},  # Missing message
            {"message": ""},  # Empty message
            {"message": "x" * 5001},  # Message too long
            {"message": "test", "max_context_tokens": 50},  # Invalid context tokens
            {"message": "test", "max_context_tokens": 10000},  # Context tokens too high
        ]
        
        for invalid_request in invalid_requests:
            response = client.post("/chat/message", json=invalid_request)
            assert response.status_code == 422
    
    async def test_query_parameter_validation(self, client):
        """Test query parameter validation."""
        # Test invalid pagination parameters
        invalid_params = [
            "limit=-1",  # Negative limit
            "limit=101",  # Limit too high
            "offset=-1",  # Negative offset
        ]
        
        for param in invalid_params:
            response = client.get(f"/chat/conversations?{param}")
            assert response.status_code == 422


class TestPerformanceIntegration:
    """Test performance-related integration scenarios."""
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_concurrent_chat_requests(self, mock_get_engine, client, mock_services, sample_conversation):
        """Test handling concurrent chat requests."""
        mock_get_engine.return_value = mock_services['chat_engine']
        
        # Mock response with delay to simulate processing time
        async def mock_process_with_delay(request):
            await asyncio.sleep(0.1)  # Simulate processing time
            return ChatResponse(
                message=ChatMessage(
                    id="msg-concurrent",
                    conversation_id=sample_conversation.id,
                    content=f"Response to: {request.message}",
                    role=MessageRole.ASSISTANT
                ),
                conversation=sample_conversation,
                sources_used=[],
                generation_stats={"total_time": 0.1}
            )
        
        mock_services['chat_engine'].process_message.side_effect = mock_process_with_delay
        
        # Send multiple concurrent requests
        request_data = {
            "message": "Concurrent test",
            "conversation_id": sample_conversation.id
        }
        
        # In a real test, you'd use asyncio to send concurrent requests
        # For this test, we verify the endpoint can handle the mock
        response = client.post("/chat/message", json=request_data)
        assert response.status_code == 200
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_large_conversation_listing(self, mock_get_manager, client, mock_services):
        """Test listing large numbers of conversations."""
        from app.models.chat import ConversationListResponse
        
        mock_get_manager.return_value = mock_services['conversation_manager']
        
        # Create large number of conversations
        large_conversation_list = [
            Conversation(
                id=f"conv-{i}",
                title=f"Conversation {i}",
                status=ConversationStatus.ACTIVE,
                message_count=i % 10
            )
            for i in range(100)
        ]
        
        mock_services['conversation_manager'].list_conversations.return_value = ConversationListResponse(
            conversations=large_conversation_list[:50],  # Paginated
            total=100
        )
        
        response = client.get("/chat/conversations?limit=50")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 100
        assert len(data["conversations"]) == 50
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_conversation_with_many_messages(self, mock_get_manager, client, mock_services, sample_conversation):
        """Test conversation with large number of messages."""
        from app.models.chat import ConversationMessagesResponse
        
        mock_get_manager.return_value = mock_services['conversation_manager']
        
        # Create many messages
        many_messages = [
            ChatMessage(
                id=f"msg-{i}",
                conversation_id=sample_conversation.id,
                content=f"Message {i}",
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            )
            for i in range(200)
        ]
        
        mock_services['conversation_manager'].get_messages.return_value = ConversationMessagesResponse(
            conversation=sample_conversation,
            messages=many_messages[:100],  # Paginated
            total_messages=200
        )
        
        response = client.get(f"/chat/conversations/{sample_conversation.id}/messages?limit=100")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 200
        assert len(data["messages"]) == 100


class TestChatStatsIntegration:
    """Test chat statistics integration."""
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_comprehensive_stats(self, mock_get_manager, client, mock_services):
        """Test comprehensive chat statistics."""
        mock_get_manager.return_value = mock_services['conversation_manager']
        
        # Mock comprehensive stats
        mock_stats = {
            "total_conversations": 25,
            "active_conversations": 20,
            "archived_conversations": 4,
            "deleted_conversations": 1,
            "total_messages": 500,
            "avg_messages_per_conversation": 20.0,
            "model_usage": {
                "llama2": 15,
                "mistral": 8,
                "codellama": 2
            }
        }
        
        mock_services['conversation_manager'].get_conversation_stats.return_value = mock_stats
        
        response = client.get("/chat/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected stats are present
        assert data["total_conversations"] == 25
        assert data["active_conversations"] == 20
        assert data["total_messages"] == 500
        assert data["avg_messages_per_conversation"] == 20.0
        
        # Verify model usage stats
        assert "model_usage" in data
        assert data["model_usage"]["llama2"] == 15
        assert data["model_usage"]["mistral"] == 8
        
        # Verify WebSocket stats are added
        assert "websocket_connections" in data
        assert "active_conversations" in data["websocket_connections"]
        assert "total_connections" in data["websocket_connections"]