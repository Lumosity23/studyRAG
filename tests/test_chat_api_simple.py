"""Simple tests for chat API endpoints."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.models.chat import (
    ChatRequest, ChatResponse, ChatMessage, Conversation, MessageRole,
    ConversationStatus, ConversationCreateRequest
)
from app.api.endpoints.chat import router
from app.core.dependencies import get_chat_engine, get_conversation_manager
from app.services.conversation_manager import ConversationNotFoundError


@pytest.fixture
def mock_chat_engine():
    """Mock chat engine."""
    return AsyncMock()


@pytest.fixture
def mock_conversation_manager():
    """Mock conversation manager."""
    return AsyncMock()


@pytest.fixture
def app_with_mocks(mock_chat_engine, mock_conversation_manager):
    """Create test app with mocked dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/chat")
    
    # Override dependencies
    app.dependency_overrides[get_chat_engine] = lambda: mock_chat_engine
    app.dependency_overrides[get_conversation_manager] = lambda: mock_conversation_manager
    
    return app


@pytest.fixture
def client(app_with_mocks):
    """Create test client with mocked dependencies."""
    return TestClient(app_with_mocks)


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
    
    def test_send_chat_message_success(self, client, mock_chat_engine, sample_chat_response):
        """Test successful chat message sending."""
        mock_chat_engine.process_message.return_value = sample_chat_response
        
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
        
        # Verify chat engine was called
        mock_chat_engine.process_message.assert_called_once()
    
    def test_send_chat_message_validation_error(self, client):
        """Test chat message validation errors."""
        # Empty message
        response = client.post("/chat/message", json={"message": ""})
        assert response.status_code == 422
        
        # Message too long
        long_message = "x" * 5001
        response = client.post("/chat/message", json={"message": long_message})
        assert response.status_code == 422
    
    def test_send_chat_message_engine_error(self, client, mock_chat_engine):
        """Test chat engine error handling."""
        mock_chat_engine.process_message.side_effect = Exception("Engine error")
        
        request_data = {"message": "Hello"}
        
        # The test client will raise the exception since we don't have middleware
        # In a real app, this would be handled by the exception middleware
        try:
            response = client.post("/chat/message", json=request_data)
            # If we get here, check it's a server error
            assert response.status_code >= 400
        except Exception as e:
            # Expected - the exception propagates without middleware
            assert "Engine error" in str(e)


class TestConversationEndpoints:
    """Test conversation management endpoints."""
    
    def test_list_conversations(self, client, mock_conversation_manager, sample_conversation):
        """Test listing conversations."""
        from app.models.chat import ConversationListResponse
        
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
    
    def test_create_conversation(self, client, mock_conversation_manager, sample_conversation):
        """Test creating a new conversation."""
        mock_conversation_manager.create_conversation.return_value = sample_conversation
        
        request_data = {
            "title": "New Conversation",
            "model_name": "llama2"
        }
        
        response = client.post("/chat/conversations", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "conv-123"
        assert data["title"] == "Test Conversation"
        
        # Verify manager was called
        mock_conversation_manager.create_conversation.assert_called_once()
    
    def test_get_conversation(self, client, mock_conversation_manager, sample_conversation):
        """Test getting a specific conversation."""
        mock_conversation_manager.get_conversation.return_value = sample_conversation
        
        response = client.get("/chat/conversations/conv-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "conv-123"
        assert data["title"] == "Test Conversation"
    
    def test_get_conversation_not_found(self, client, mock_conversation_manager):
        """Test getting non-existent conversation."""
        mock_conversation_manager.get_conversation.side_effect = ConversationNotFoundError("conv-999")
        
        response = client.get("/chat/conversations/conv-999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_delete_conversation(self, client, mock_conversation_manager):
        """Test deleting a conversation."""
        mock_conversation_manager.delete_conversation.return_value = True
        
        response = client.delete("/chat/conversations/conv-123")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        assert data["conversation_id"] == "conv-123"
    
    def test_delete_conversation_not_found(self, client, mock_conversation_manager):
        """Test deleting non-existent conversation."""
        mock_conversation_manager.delete_conversation.return_value = False
        
        # Similar to engine error test, this will raise an exception without middleware
        try:
            response = client.delete("/chat/conversations/conv-999")
            assert response.status_code == 404
        except Exception as e:
            # Expected - the HTTPException propagates without middleware
            assert "not found" in str(e)


class TestChatStats:
    """Test chat statistics endpoint."""
    
    def test_get_chat_stats(self, client, mock_conversation_manager):
        """Test getting chat statistics."""
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


class TestErrorHandling:
    """Test error handling in chat endpoints."""
    
    def test_validation_errors(self, client):
        """Test request validation errors."""
        # Test invalid chat message requests
        invalid_requests = [
            {},  # Missing message
            {"message": ""},  # Empty message
            {"message": "x" * 5001},  # Message too long
        ]
        
        for invalid_request in invalid_requests:
            response = client.post("/chat/message", json=invalid_request)
            assert response.status_code == 422
    
    def test_query_parameter_validation(self, client):
        """Test query parameter validation."""
        # Test invalid pagination parameters
        response = client.get("/chat/conversations?limit=-1")
        assert response.status_code == 422
        
        response = client.get("/chat/conversations?limit=101")
        assert response.status_code == 422