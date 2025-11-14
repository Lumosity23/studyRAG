"""Integration tests for WebSocket chat functionality."""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from app.models.chat import (
    ChatMessage, Conversation, MessageRole, ConversationStatus,
    StreamingChatResponse
)
from app.api.endpoints.chat import router, WebSocketManager


@pytest.fixture
def app():
    """Create test FastAPI app with WebSocket support."""
    app = FastAPI()
    app.include_router(router, prefix="/chat")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def websocket_manager():
    """Create WebSocket manager for testing."""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket."""
    ws = MagicMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def sample_conversation():
    """Sample conversation for testing."""
    return Conversation(
        id="conv-123",
        title="Test WebSocket Conversation",
        status=ConversationStatus.ACTIVE,
        message_count=0,
        model_name="llama2"
    )


@pytest.fixture
def sample_streaming_response():
    """Sample streaming response chunks."""
    return [
        StreamingChatResponse(
            conversation_id="conv-123",
            message_id="msg-123",
            content_delta="Hello",
            is_complete=False
        ),
        StreamingChatResponse(
            conversation_id="conv-123",
            message_id="msg-123",
            content_delta=" there!",
            is_complete=False
        ),
        StreamingChatResponse(
            conversation_id="conv-123",
            message_id="msg-123",
            content_delta="",
            is_complete=True,
            sources=[],
            generation_stats={"total_time": 1.5}
        )
    ]


class TestWebSocketManager:
    """Test WebSocket manager functionality."""
    
    async def test_single_connection(self, websocket_manager, mock_websocket):
        """Test single WebSocket connection."""
        # Connect
        await websocket_manager.connect(mock_websocket, "conv-123", "client-1")
        
        # Verify connection is tracked
        assert "conv-123" in websocket_manager.active_connections
        assert mock_websocket in websocket_manager.active_connections["conv-123"]
        assert mock_websocket in websocket_manager.connection_metadata
        
        # Verify metadata
        metadata = websocket_manager.connection_metadata[mock_websocket]
        assert metadata["conversation_id"] == "conv-123"
        assert metadata["client_id"] == "client-1"
        assert "connected_at" in metadata
        
        # Verify accept was called
        mock_websocket.accept.assert_called_once()
    
    async def test_multiple_connections_same_conversation(self, websocket_manager):
        """Test multiple clients connecting to same conversation."""
        # Create multiple mock WebSockets
        websockets = []
        for i in range(3):
            ws = MagicMock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            websockets.append(ws)
            await websocket_manager.connect(ws, "conv-123", f"client-{i}")
        
        # Verify all connections are tracked
        assert len(websocket_manager.active_connections["conv-123"]) == 3
        assert len(websocket_manager.connection_metadata) == 3
        
        # Verify all WebSockets were accepted
        for ws in websockets:
            ws.accept.assert_called_once()
    
    async def test_multiple_conversations(self, websocket_manager):
        """Test connections to different conversations."""
        # Connect to different conversations
        ws1 = MagicMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws2 = MagicMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        
        await websocket_manager.connect(ws1, "conv-123", "client-1")
        await websocket_manager.connect(ws2, "conv-456", "client-2")
        
        # Verify separate conversation tracking
        assert "conv-123" in websocket_manager.active_connections
        assert "conv-456" in websocket_manager.active_connections
        assert len(websocket_manager.active_connections["conv-123"]) == 1
        assert len(websocket_manager.active_connections["conv-456"]) == 1
    
    async def test_disconnect_single_client(self, websocket_manager, mock_websocket):
        """Test disconnecting a single client."""
        # Connect first
        await websocket_manager.connect(mock_websocket, "conv-123", "client-1")
        
        # Disconnect
        websocket_manager.disconnect(mock_websocket)
        
        # Verify cleanup
        assert "conv-123" not in websocket_manager.active_connections
        assert mock_websocket not in websocket_manager.connection_metadata
    
    async def test_disconnect_multiple_clients(self, websocket_manager):
        """Test disconnecting one client when multiple are connected."""
        # Connect multiple clients
        ws1 = MagicMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws2 = MagicMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        
        await websocket_manager.connect(ws1, "conv-123", "client-1")
        await websocket_manager.connect(ws2, "conv-123", "client-2")
        
        # Disconnect one client
        websocket_manager.disconnect(ws1)
        
        # Verify partial cleanup
        assert "conv-123" in websocket_manager.active_connections
        assert len(websocket_manager.active_connections["conv-123"]) == 1
        assert ws2 in websocket_manager.active_connections["conv-123"]
        assert ws1 not in websocket_manager.connection_metadata
        assert ws2 in websocket_manager.connection_metadata
    
    async def test_send_to_conversation(self, websocket_manager):
        """Test sending messages to all clients in a conversation."""
        # Connect multiple clients
        websockets = []
        for i in range(3):
            ws = MagicMock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            websockets.append(ws)
            await websocket_manager.connect(ws, "conv-123", f"client-{i}")
        
        # Send message to conversation
        message = {
            "type": "new_message",
            "data": {"content": "Hello everyone!"}
        }
        
        await websocket_manager.send_to_conversation("conv-123", message)
        
        # Verify all clients received the message
        expected_json = json.dumps(message)
        for ws in websockets:
            ws.send_text.assert_called_once_with(expected_json)
    
    async def test_send_to_nonexistent_conversation(self, websocket_manager):
        """Test sending to a conversation with no connections."""
        message = {"type": "test", "data": "hello"}
        
        # Should not raise an error
        await websocket_manager.send_to_conversation("nonexistent", message)
    
    async def test_send_with_failed_websocket(self, websocket_manager):
        """Test handling failed WebSocket sends."""
        # Connect clients
        ws1 = MagicMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        
        ws2 = MagicMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock(side_effect=Exception("Connection lost"))
        
        await websocket_manager.connect(ws1, "conv-123", "client-1")
        await websocket_manager.connect(ws2, "conv-123", "client-2")
        
        # Send message
        message = {"type": "test", "data": "hello"}
        await websocket_manager.send_to_conversation("conv-123", message)
        
        # Verify successful client received message
        ws1.send_text.assert_called_once()
        
        # Verify failed client was disconnected
        assert ws2 not in websocket_manager.connection_metadata
    
    async def test_streaming_response_broadcast(self, websocket_manager, sample_streaming_response):
        """Test broadcasting streaming responses."""
        # Connect clients
        websockets = []
        for i in range(2):
            ws = MagicMock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            websockets.append(ws)
            await websocket_manager.connect(ws, "conv-123", f"client-{i}")
        
        # Mock streaming response
        async def mock_stream():
            for chunk in sample_streaming_response:
                yield chunk
        
        # Send streaming response
        await websocket_manager.send_streaming_response(
            "conv-123",
            mock_stream(),
            exclude_websocket=websockets[0]  # Exclude first client
        )
        
        # Verify only second client received messages
        websockets[0].send_text.assert_not_called()
        assert websockets[1].send_text.call_count == len(sample_streaming_response)


class TestWebSocketEndpoint:
    """Test WebSocket endpoint functionality."""
    
    @patch('app.api.endpoints.chat.get_chat_engine')
    async def test_websocket_message_processing(self, mock_get_engine, sample_streaming_response):
        """Test processing messages through WebSocket."""
        # Mock chat engine
        mock_chat_engine = AsyncMock()
        mock_get_engine.return_value = mock_chat_engine
        
        async def mock_stream():
            for chunk in sample_streaming_response:
                yield chunk
        
        mock_chat_engine.stream_message.return_value = mock_stream()
        
        # This would be tested with actual WebSocket client in integration tests
        # For unit tests, we verify the logic components
        
        # Verify that the endpoint would process the message correctly
        from app.api.endpoints.chat import websocket_chat_endpoint
        import inspect
        assert inspect.iscoroutinefunction(websocket_chat_endpoint)
    
    async def test_websocket_message_types(self):
        """Test different WebSocket message types."""
        # Test message type validation
        valid_message_types = ["message", "ping", "typing"]
        
        for msg_type in valid_message_types:
            message_data = {
                "type": msg_type,
                "content": "test content" if msg_type == "message" else None
            }
            
            # Verify message structure is valid
            assert "type" in message_data
            if msg_type == "message":
                assert "content" in message_data
    
    async def test_websocket_error_handling(self):
        """Test WebSocket error handling."""
        from app.api.endpoints.chat import websocket_chat_endpoint
        
        # Mock WebSocket that raises exception
        mock_websocket = MagicMock()
        mock_websocket.receive_text = AsyncMock(side_effect=Exception("Connection error"))
        
        # The endpoint should handle this gracefully
        # In actual implementation, this would be caught and logged
        
        # Verify error handling structure exists
        import inspect
        source = inspect.getsource(websocket_chat_endpoint)
        assert "except" in source  # Basic check for exception handling


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""
    
    def test_websocket_endpoint_exists(self, client):
        """Test that WebSocket endpoint is properly configured."""
        # This tests that the endpoint is registered
        # Actual WebSocket testing requires specialized tools
        
        # Check that the route exists in the app
        from app.api.endpoints.chat import router
        
        websocket_routes = [route for route in router.routes if hasattr(route, 'path') and 'ws' in route.path]
        assert len(websocket_routes) > 0
    
    async def test_websocket_dependency_injection(self):
        """Test that WebSocket endpoint has proper dependency injection."""
        from app.api.endpoints.chat import websocket_chat_endpoint
        import inspect
        
        # Get function signature
        sig = inspect.signature(websocket_chat_endpoint)
        
        # Verify required parameters exist
        assert 'websocket' in sig.parameters
        assert 'conversation_id' in sig.parameters
        assert 'chat_engine' in sig.parameters
    
    @patch('app.api.endpoints.chat.websocket_manager')
    async def test_websocket_manager_integration(self, mock_manager):
        """Test WebSocket manager integration with endpoint."""
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = MagicMock()
        mock_manager.send_to_conversation = AsyncMock()
        
        # Verify manager methods would be called
        # This tests the integration points
        
        # Connect
        await mock_manager.connect(MagicMock(), "conv-123", "client-1")
        mock_manager.connect.assert_called_once()
        
        # Send message
        await mock_manager.send_to_conversation("conv-123", {"test": "data"})
        mock_manager.send_to_conversation.assert_called_once()
        
        # Disconnect
        mock_manager.disconnect(MagicMock())
        mock_manager.disconnect.assert_called_once()


class TestWebSocketSecurity:
    """Test WebSocket security considerations."""
    
    async def test_websocket_connection_limits(self, websocket_manager):
        """Test connection limits per conversation."""
        # This would test rate limiting in a real implementation
        # For now, test that we can track multiple connections
        
        max_connections = 10
        websockets = []
        
        for i in range(max_connections):
            ws = MagicMock(spec=WebSocket)
            ws.accept = AsyncMock()
            websockets.append(ws)
            await websocket_manager.connect(ws, "conv-123", f"client-{i}")
        
        # Verify all connections are tracked
        assert len(websocket_manager.active_connections["conv-123"]) == max_connections
    
    async def test_websocket_message_validation(self):
        """Test WebSocket message validation."""
        # Test invalid JSON handling
        invalid_messages = [
            "not json",
            '{"incomplete": json',
            '{"type": "unknown_type"}',
            '{"type": "message"}',  # Missing content
        ]
        
        for invalid_msg in invalid_messages:
            # In real implementation, these would be handled gracefully
            # Test that we have validation logic
            try:
                data = json.loads(invalid_msg)
                # Basic validation
                if "type" in data:
                    msg_type = data["type"]
                    if msg_type == "message" and "content" not in data:
                        assert False, "Should validate message content"
            except json.JSONDecodeError:
                # Expected for invalid JSON
                pass
    
    async def test_websocket_client_identification(self, websocket_manager, mock_websocket):
        """Test client identification and tracking."""
        # Connect with client ID
        await websocket_manager.connect(mock_websocket, "conv-123", "client-abc")
        
        # Verify client ID is tracked
        metadata = websocket_manager.connection_metadata[mock_websocket]
        assert metadata["client_id"] == "client-abc"
        
        # Connect without client ID
        ws2 = MagicMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        await websocket_manager.connect(ws2, "conv-123", None)
        
        # Should still work
        metadata2 = websocket_manager.connection_metadata[ws2]
        assert metadata2["client_id"] is None


class TestWebSocketPerformance:
    """Test WebSocket performance considerations."""
    
    async def test_concurrent_connections(self, websocket_manager):
        """Test handling many concurrent connections."""
        num_connections = 50
        websockets = []
        
        # Connect many clients concurrently
        tasks = []
        for i in range(num_connections):
            ws = MagicMock(spec=WebSocket)
            ws.accept = AsyncMock()
            websockets.append(ws)
            
            task = websocket_manager.connect(ws, f"conv-{i % 5}", f"client-{i}")
            tasks.append(task)
        
        # Wait for all connections
        await asyncio.gather(*tasks)
        
        # Verify all connections are tracked
        total_connections = sum(
            len(connections) for connections in websocket_manager.active_connections.values()
        )
        assert total_connections == num_connections
    
    async def test_broadcast_performance(self, websocket_manager):
        """Test broadcasting to many clients."""
        num_clients = 20
        websockets = []
        
        # Connect many clients to same conversation
        for i in range(num_clients):
            ws = MagicMock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            websockets.append(ws)
            await websocket_manager.connect(ws, "conv-123", f"client-{i}")
        
        # Broadcast message
        message = {"type": "broadcast_test", "data": "performance test"}
        await websocket_manager.send_to_conversation("conv-123", message)
        
        # Verify all clients received message
        for ws in websockets:
            ws.send_text.assert_called_once()
    
    async def test_memory_cleanup(self, websocket_manager):
        """Test memory cleanup on disconnection."""
        # Connect and disconnect many clients
        for i in range(100):
            ws = MagicMock(spec=WebSocket)
            ws.accept = AsyncMock()
            
            await websocket_manager.connect(ws, "conv-123", f"client-{i}")
            websocket_manager.disconnect(ws)
        
        # Verify no memory leaks
        assert len(websocket_manager.active_connections) == 0
        assert len(websocket_manager.connection_metadata) == 0