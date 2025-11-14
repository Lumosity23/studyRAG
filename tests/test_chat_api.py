"""Tests for chat API endpoints."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from typing import Dict, Any

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.models.chat import (
    ChatRequest, ChatResponse, ChatMessage, Conversation, MessageRole,
    ConversationStatus, ConversationCreateRequest, StreamingChatResponse
)
from app.models.search import SearchResult, SearchResponse
from app.services.chat_engine import ChatEngine
from app.services.conversation_manager import ConversationManager, ConversationNotFoundError
from app.api.endpoints.chat import router
from app.core.dependencies import get_chat_engine, get_conversation_manager


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
def mock_chat_engine():
    """Mock chat engine."""
    return AsyncMock(spec=ChatEngine)


@pytest.fixture
def mock_conversation_manager():
    """Mock conversation manager."""
    return AsyncMock(spec=ConversationManager)


@pytest.fixture
def sample_conversation():
    """Sample conversation for testing."""
    return Conversation(
        id="conv-123",
        title="Test Conversation",
        status=ConversationStatus.ACTIVE,
        message_count=2,
        last_message_at=datetime.now(),
        model_name="llama2"
    )


@pytest.fixture
def sample_message():
    """Sample chat message for testing."""
    return ChatMessage(
        id="msg-123",
        conversation_id="conv-123",
        content="Hello, how can I help you?",
        role=MessageRole.ASSISTANT,
        model_name="llama2",
        generation_time=1.5
    )


@pytest.fixture
def sample_chat_response(sample_message, sample_conversation):
    """Sample chat response for testing."""
    return ChatResponse(
        message=sample_message,
        conversation=sample_conversation,
        sources_used=[],
        generation_stats={"total_time": 1.5, "model_used": "llama2"}
    )


class TestChatMessageEndpoint:
    """Test chat message endpoint."""
    
    async def test_send_chat_message_success(self, client, mock_chat_engine, sample_chat_response):
        """Test successful chat message sending."""
        mock_chat_engine.process_message.return_value = sample_chat_response
        
        # Override the dependency
        def override_get_chat_engine():
            return mock_chat_engine
        
        client.app.dependency_overrides[get_chat_engine] = override_get_chat_engine
        
        try:
            request_data = {
                "message": "Hello, world!",
                "conversation_id": "conv-123",
                "include_sources": True
            }
            
            response = client.post("/chat/message", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"]["content"] == "Hello, how can I help you?"
            assert data["conversation"]["id"] == "conv-123"
            assert "generation_stats" in data
            
            # Verify chat engine was called correctly
            mock_chat_engine.process_message.assert_called_once()
            call_args = mock_chat_engine.process_message.call_args[0][0]
            assert isinstance(call_args, ChatRequest)
            assert call_args.message == "Hello, world!"
            assert call_args.conversation_id == "conv-123"
        finally:
            # Clean up dependency override
            client.app.dependency_overrides.clear()
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_send_chat_message_new_conversation(self, mock_get_engine, client, mock_chat_engine, sample_chat_response):
        """Test sending message without conversation ID (new conversation)."""
        mock_get_engine.return_value = mock_chat_engine
        mock_chat_engine.process_message.return_value = sample_chat_response
        
        request_data = {
            "message": "Start new conversation",
            "model_name": "llama2"
        }
        
        response = client.post("/chat/message", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"]["content"] == "Hello, how can I help you?"
        
        # Verify request was processed correctly
        call_args = mock_chat_engine.process_message.call_args[0][0]
        assert call_args.conversation_id is None
        assert call_args.model_name == "llama2"
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_send_chat_message_validation_error(self, mock_get_engine, client):
        """Test chat message validation errors."""
        mock_get_engine.return_value = AsyncMock()
        
        # Empty message
        response = client.post("/chat/message", json={"message": ""})
        assert response.status_code == 422
        
        # Message too long
        long_message = "x" * 5001
        response = client.post("/chat/message", json={"message": long_message})
        assert response.status_code == 422
        
        # Invalid max_context_tokens
        response = client.post("/chat/message", json={
            "message": "test",
            "max_context_tokens": 50  # Too low
        })
        assert response.status_code == 422
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_send_chat_message_engine_error(self, mock_get_engine, client, mock_chat_engine):
        """Test chat engine error handling."""
        mock_get_engine.return_value = mock_chat_engine
        mock_chat_engine.process_message.side_effect = Exception("Engine error")
        
        request_data = {"message": "Hello"}
        
        response = client.post("/chat/message", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Failed to process chat message" in data["message"]


class TestStreamingEndpoint:
    """Test streaming chat endpoint."""
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_stream_chat_message(self, mock_get_engine, client, mock_chat_engine):
        """Test streaming chat response."""
        mock_get_engine.return_value = mock_chat_engine
        
        # Mock streaming response
        async def mock_stream():
            yield StreamingChatResponse(
                conversation_id="conv-123",
                message_id="msg-123",
                content_delta="Hello",
                is_complete=False
            )
            yield StreamingChatResponse(
                conversation_id="conv-123",
                message_id="msg-123",
                content_delta=" world!",
                is_complete=True
            )
        
        mock_chat_engine.stream_message.return_value = mock_stream()
        
        response = client.get("/chat/stream/conv-123?message=Hello")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Check that streaming was called
        mock_chat_engine.stream_message.assert_called_once()


class TestConversationEndpoints:
    """Test conversation management endpoints."""
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_list_conversations(self, mock_get_manager, client, mock_conversation_manager, sample_conversation):
        """Test listing conversations."""
        from app.models.chat import ConversationListResponse
        
        mock_get_manager.return_value = mock_conversation_manager
        mock_conversation_manager.list_conversations.return_value = ConversationListResponse(
            conversations=[sample_conversation],
            total=1
        )
        
        response = client.get("/chat/conversations")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["id"] == "conv-123"
        
        # Test with filters
        response = client.get("/chat/conversations?status=active&limit=10&offset=0")
        assert response.status_code == 200
        
        mock_conversation_manager.list_conversations.assert_called_with(
            status=ConversationStatus.ACTIVE,
            limit=10,
            offset=0
        )
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_create_conversation(self, mock_get_manager, client, mock_conversation_manager, sample_conversation):
        """Test creating a new conversation."""
        mock_get_manager.return_value = mock_conversation_manager
        mock_conversation_manager.create_conversation.return_value = sample_conversation
        
        request_data = {
            "title": "New Conversation",
            "model_name": "llama2",
            "system_prompt": "You are a helpful assistant"
        }
        
        response = client.post("/chat/conversations", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "conv-123"
        assert data["title"] == "Test Conversation"
        
        # Verify manager was called correctly
        mock_conversation_manager.create_conversation.assert_called_once()
        call_args = mock_conversation_manager.create_conversation.call_args[0][0]
        assert isinstance(call_args, ConversationCreateRequest)
        assert call_args.title == "New Conversation"
        assert call_args.model_name == "llama2"
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_get_conversation(self, mock_get_manager, client, mock_conversation_manager, sample_conversation):
        """Test getting a specific conversation."""
        mock_get_manager.return_value = mock_conversation_manager
        mock_conversation_manager.get_conversation.return_value = sample_conversation
        
        response = client.get("/chat/conversations/conv-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "conv-123"
        assert data["title"] == "Test Conversation"
        
        mock_conversation_manager.get_conversation.assert_called_once_with("conv-123")
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_get_conversation_not_found(self, mock_get_manager, client, mock_conversation_manager):
        """Test getting non-existent conversation."""
        mock_get_manager.return_value = mock_conversation_manager
        mock_conversation_manager.get_conversation.side_effect = ConversationNotFoundError("conv-999")
        
        response = client.get("/chat/conversations/conv-999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_get_conversation_messages(self, mock_get_manager, client, mock_conversation_manager, sample_conversation, sample_message):
        """Test getting conversation messages."""
        from app.models.chat import ConversationMessagesResponse
        
        mock_get_manager.return_value = mock_conversation_manager
        mock_conversation_manager.get_messages.return_value = ConversationMessagesResponse(
            conversation=sample_conversation,
            messages=[sample_message],
            total_messages=1
        )
        
        response = client.get("/chat/conversations/conv-123/messages")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 1
        assert len(data["messages"]) == 1
        assert data["messages"][0]["id"] == "msg-123"
        
        # Test with pagination
        response = client.get("/chat/conversations/conv-123/messages?limit=50&offset=10")
        assert response.status_code == 200
        
        mock_conversation_manager.get_messages.assert_called_with(
            conversation_id="conv-123",
            limit=50,
            offset=10
        )
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_update_conversation(self, mock_get_manager, client, mock_conversation_manager, sample_conversation):
        """Test updating conversation details."""
        mock_get_manager.return_value = mock_conversation_manager
        
        updated_conversation = sample_conversation.model_copy()
        updated_conversation.title = "Updated Title"
        mock_conversation_manager.update_conversation.return_value = updated_conversation
        
        response = client.put("/chat/conversations/conv-123?title=Updated Title&status=active")
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        
        mock_conversation_manager.update_conversation.assert_called_once_with(
            conversation_id="conv-123",
            title="Updated Title",
            status=ConversationStatus.ACTIVE,
            model_name=None,
            system_prompt=None
        )
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_delete_conversation(self, mock_get_manager, client, mock_conversation_manager):
        """Test deleting a conversation."""
        mock_get_manager.return_value = mock_conversation_manager
        mock_conversation_manager.delete_conversation.return_value = True
        
        response = client.delete("/chat/conversations/conv-123")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        assert data["conversation_id"] == "conv-123"
        
        mock_conversation_manager.delete_conversation.assert_called_once_with("conv-123")
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_delete_conversation_not_found(self, mock_get_manager, client, mock_conversation_manager):
        """Test deleting non-existent conversation."""
        mock_get_manager.return_value = mock_conversation_manager
        mock_conversation_manager.delete_conversation.return_value = False
        
        response = client.delete("/chat/conversations/conv-999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestChatStats:
    """Test chat statistics endpoint."""
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_get_chat_stats(self, mock_get_manager, client, mock_conversation_manager):
        """Test getting chat statistics."""
        mock_get_manager.return_value = mock_conversation_manager
        mock_conversation_manager.get_conversation_stats.return_value = {
            "total_conversations": 10,
            "active_conversations": 8,
            "total_messages": 150,
            "avg_messages_per_conversation": 15.0,
            "model_usage": {"llama2": 5, "mistral": 3}
        }
        
        response = client.get("/chat/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_conversations"] == 10
        assert data["active_conversations"] == 8
        assert "websocket_connections" in data
        assert "model_usage" in data


class TestWebSocketManager:
    """Test WebSocket manager functionality."""
    
    def test_websocket_manager_initialization(self):
        """Test WebSocket manager initialization."""
        from app.api.endpoints.chat import WebSocketManager
        
        manager = WebSocketManager()
        assert manager.active_connections == {}
        assert manager.connection_metadata == {}
    
    async def test_websocket_connect_disconnect(self):
        """Test WebSocket connection and disconnection."""
        from app.api.endpoints.chat import WebSocketManager
        
        manager = WebSocketManager()
        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        
        # Test connection
        await manager.connect(mock_websocket, "conv-123", "client-1")
        
        assert "conv-123" in manager.active_connections
        assert mock_websocket in manager.active_connections["conv-123"]
        assert mock_websocket in manager.connection_metadata
        
        # Test disconnection
        manager.disconnect(mock_websocket)
        
        assert "conv-123" not in manager.active_connections
        assert mock_websocket not in manager.connection_metadata
    
    async def test_websocket_send_to_conversation(self):
        """Test sending messages to conversation."""
        from app.api.endpoints.chat import WebSocketManager
        
        manager = WebSocketManager()
        mock_websocket1 = MagicMock()
        mock_websocket2 = MagicMock()
        
        mock_websocket1.accept = AsyncMock()
        mock_websocket2.accept = AsyncMock()
        mock_websocket1.send_text = AsyncMock()
        mock_websocket2.send_text = AsyncMock()
        
        # Connect two clients to same conversation
        await manager.connect(mock_websocket1, "conv-123", "client-1")
        await manager.connect(mock_websocket2, "conv-123", "client-2")
        
        # Send message to conversation
        message = {"type": "test", "data": "hello"}
        await manager.send_to_conversation("conv-123", message)
        
        # Both clients should receive the message
        mock_websocket1.send_text.assert_called_once_with(json.dumps(message))
        mock_websocket2.send_text.assert_called_once_with(json.dumps(message))


class TestErrorHandling:
    """Test error handling in chat endpoints."""
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_chat_engine_unavailable(self, mock_get_engine, client):
        """Test handling when chat engine is unavailable."""
        mock_get_engine.side_effect = Exception("Service unavailable")
        
        response = client.post("/chat/message", json={"message": "test"})
        
        # Should handle the dependency injection error gracefully
        assert response.status_code in [500, 503]
    
    @patch('app.api.endpoints.chat.get_conversation_manager')
    async def test_conversation_manager_error(self, mock_get_manager, client):
        """Test handling conversation manager errors."""
        mock_get_manager.side_effect = Exception("Database error")
        
        response = client.get("/chat/conversations")
        
        # Should handle the dependency injection error gracefully
        assert response.status_code in [500, 503]
    
    async def test_invalid_conversation_id_format(self, client):
        """Test handling invalid conversation ID formats."""
        # This would be handled by FastAPI's path validation
        # Testing with a very long ID that might cause issues
        long_id = "x" * 1000
        
        with patch('app.api.endpoints.chat.get_conversation_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.get_conversation.side_effect = ConversationNotFoundError(long_id)
            
            response = client.get(f"/chat/conversations/{long_id}")
            assert response.status_code == 404


@pytest.mark.asyncio
class TestAsyncEndpoints:
    """Test async functionality of endpoints."""
    
    async def test_concurrent_message_processing(self):
        """Test handling concurrent message processing."""
        # This would test the actual async behavior
        # For now, we'll test that the endpoints are properly async
        from app.api.endpoints.chat import send_chat_message
        
        # Verify the function is async
        import inspect
        assert inspect.iscoroutinefunction(send_chat_message)
    
    async def test_websocket_concurrent_connections(self):
        """Test handling multiple concurrent WebSocket connections."""
        from app.api.endpoints.chat import WebSocketManager
        
        manager = WebSocketManager()
        
        # Simulate multiple concurrent connections
        mock_websockets = []
        for i in range(5):
            mock_ws = MagicMock()
            mock_ws.accept = AsyncMock()
            mock_websockets.append(mock_ws)
            await manager.connect(mock_ws, "conv-123", f"client-{i}")
        
        assert len(manager.active_connections["conv-123"]) == 5
        
        # Disconnect all
        for ws in mock_websockets:
            manager.disconnect(ws)
        
        assert "conv-123" not in manager.active_connections