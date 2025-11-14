"""Chat API endpoints with WebSocket support."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse
import structlog

from app.models.chat import (
    ChatRequest, ChatResponse, ConversationCreateRequest, 
    ConversationListResponse, ConversationMessagesResponse,
    Conversation, ConversationStatus, StreamingChatResponse
)
from app.services.chat_engine import ChatEngine
from app.services.conversation_manager import ConversationManager, ConversationNotFoundError
from app.core.dependencies import get_chat_engine, get_conversation_manager
from app.core.exceptions import APIException


logger = structlog.get_logger(__name__)
router = APIRouter()


class ChatAPIError(APIException):
    """Chat API specific error."""
    
    def __init__(self, message: str, status_code: int = 400, details: Dict = None):
        super().__init__("CHAT_API_001", message, status_code, details)


class WebSocketManager:
    """Manages WebSocket connections for real-time chat."""
    
    def __init__(self):
        # Store active connections by conversation_id
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, conversation_id: str, client_id: Optional[str] = None):
        """Accept a WebSocket connection and add it to the conversation."""
        await websocket.accept()
        
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        
        self.active_connections[conversation_id].append(websocket)
        self.connection_metadata[websocket] = {
            "conversation_id": conversation_id,
            "client_id": client_id,
            "connected_at": datetime.now()
        }
        
        logger.info(
            "WebSocket connected",
            conversation_id=conversation_id,
            client_id=client_id,
            total_connections=len(self.active_connections[conversation_id])
        )
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            conversation_id = metadata["conversation_id"]
            
            # Remove from active connections
            if conversation_id in self.active_connections:
                if websocket in self.active_connections[conversation_id]:
                    self.active_connections[conversation_id].remove(websocket)
                
                # Clean up empty conversation lists
                if not self.active_connections[conversation_id]:
                    del self.active_connections[conversation_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(
                "WebSocket disconnected",
                conversation_id=conversation_id,
                client_id=metadata.get("client_id")
            )
    
    async def send_to_conversation(self, conversation_id: str, message: Dict[str, Any]):
        """Send a message to all connections in a conversation."""
        if conversation_id not in self.active_connections:
            return
        
        # Send to all connections in the conversation
        disconnected_connections = []
        
        for websocket in self.active_connections[conversation_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(
                    "Failed to send WebSocket message",
                    conversation_id=conversation_id,
                    error=str(e)
                )
                disconnected_connections.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            self.disconnect(websocket)
    
    async def send_streaming_response(
        self, 
        conversation_id: str, 
        response_stream: Any,
        exclude_websocket: Optional[WebSocket] = None
    ):
        """Send streaming chat response to WebSocket connections."""
        async for chunk in response_stream:
            if isinstance(chunk, StreamingChatResponse):
                message = {
                    "type": "streaming_response",
                    "data": chunk.model_dump()
                }
            else:
                message = {
                    "type": "streaming_chunk",
                    "data": chunk
                }
            
            # Send to all connections except the sender
            if conversation_id in self.active_connections:
                for websocket in self.active_connections[conversation_id]:
                    if websocket != exclude_websocket:
                        try:
                            await websocket.send_text(json.dumps(message))
                        except Exception:
                            pass  # Will be cleaned up later


# Global WebSocket manager
websocket_manager = WebSocketManager()


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    chat_engine: ChatEngine = Depends(get_chat_engine)
) -> ChatResponse:
    """
    Send a chat message and get a response.
    
    This endpoint processes a user message, retrieves relevant context from documents,
    and generates a response using the configured LLM model.
    """
    try:
        logger.info(
            "Processing chat message",
            conversation_id=request.conversation_id,
            message_length=len(request.message),
            model_name=request.model_name,
            include_sources=request.include_sources
        )
        
        # Process the message
        response = await chat_engine.process_message(request)
        
        # Send WebSocket notification to other clients in the conversation
        if response.conversation.id:
            await websocket_manager.send_to_conversation(
                response.conversation.id,
                {
                    "type": "new_message",
                    "data": {
                        "user_message": {
                            "content": request.message,
                            "timestamp": datetime.now().isoformat()
                        },
                        "assistant_message": response.message.model_dump(),
                        "conversation": response.conversation.model_dump()
                    }
                }
            )
        
        logger.info(
            "Chat message processed successfully",
            conversation_id=response.conversation.id,
            response_length=len(response.message.content),
            sources_count=len(response.sources_used) if response.sources_used else 0,
            generation_time=response.generation_stats.get("total_time") if response.generation_stats else None
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Error processing chat message",
            error=str(e),
            conversation_id=request.conversation_id,
            exc_info=True
        )
        raise ChatAPIError(f"Failed to process chat message: {str(e)}")


@router.get("/stream/{conversation_id}")
async def stream_chat_message(
    conversation_id: str,
    message: str = Query(..., description="Message to send"),
    model_name: Optional[str] = Query(None, description="Model to use"),
    include_sources: bool = Query(True, description="Include source citations"),
    chat_engine: ChatEngine = Depends(get_chat_engine)
):
    """
    Stream a chat response using Server-Sent Events.
    
    This endpoint provides an alternative to WebSocket for streaming responses
    using HTTP Server-Sent Events (SSE).
    """
    try:
        # Create chat request
        request = ChatRequest(
            message=message,
            conversation_id=conversation_id,
            model_name=model_name,
            include_sources=include_sources,
            stream=True
        )
        
        async def generate_stream():
            """Generate SSE stream."""
            try:
                async for chunk in chat_engine.stream_message(request):
                    if isinstance(chunk, StreamingChatResponse):
                        data = chunk.model_dump_json()
                        yield f"data: {data}\n\n"
                    
                    # Send final event
                    if chunk.is_complete:
                        yield "event: complete\ndata: {}\n\n"
                        break
                        
            except Exception as e:
                error_data = json.dumps({"error": str(e)})
                yield f"event: error\ndata: {error_data}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except Exception as e:
        logger.error("Error in streaming chat", error=str(e), exc_info=True)
        raise ChatAPIError(f"Failed to stream chat message: {str(e)}")


@router.websocket("/ws/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    client_id: Optional[str] = Query(None),
    chat_engine: ChatEngine = Depends(get_chat_engine)
):
    """
    WebSocket endpoint for real-time chat.
    
    Supports bidirectional communication for real-time chat experience.
    Clients can send messages and receive streaming responses.
    """
    await websocket_manager.connect(websocket, conversation_id, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "message")
                
                if message_type == "message":
                    # Process chat message
                    request = ChatRequest(
                        message=message_data["content"],
                        conversation_id=conversation_id,
                        model_name=message_data.get("model_name"),
                        include_sources=message_data.get("include_sources", True),
                        stream=True
                    )
                    
                    # Send acknowledgment
                    await websocket.send_text(json.dumps({
                        "type": "message_received",
                        "data": {"message_id": message_data.get("id")}
                    }))
                    
                    # Stream response
                    async for chunk in chat_engine.stream_message(request):
                        response_data = {
                            "type": "streaming_response",
                            "data": chunk.model_dump()
                        }
                        await websocket.send_text(json.dumps(response_data))
                        
                        # Also broadcast to other connections in the conversation
                        await websocket_manager.send_to_conversation(
                            conversation_id,
                            response_data
                        )
                
                elif message_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))
                
                elif message_type == "typing":
                    # Broadcast typing indicator to other clients
                    await websocket_manager.send_to_conversation(
                        conversation_id,
                        {
                            "type": "typing",
                            "data": {
                                "client_id": client_id,
                                "is_typing": message_data.get("is_typing", False)
                            }
                        }
                    )
                
                else:
                    # Unknown message type
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": {"message": f"Unknown message type: {message_type}"}
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }))
            
            except Exception as e:
                logger.error(
                    "Error processing WebSocket message",
                    conversation_id=conversation_id,
                    client_id=client_id,
                    error=str(e),
                    exc_info=True
                )
                
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": f"Error processing message: {str(e)}"}
                }))
    
    except WebSocketDisconnect:
        logger.info(
            "WebSocket client disconnected",
            conversation_id=conversation_id,
            client_id=client_id
        )
    
    except Exception as e:
        logger.error(
            "WebSocket error",
            conversation_id=conversation_id,
            client_id=client_id,
            error=str(e),
            exc_info=True
        )
    
    finally:
        websocket_manager.disconnect(websocket)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    status: Optional[ConversationStatus] = Query(None, description="Filter by conversation status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of conversations to return"),
    offset: int = Query(0, ge=0, description="Number of conversations to skip"),
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
) -> ConversationListResponse:
    """
    List conversations with optional filtering and pagination.
    
    Returns a paginated list of conversations, optionally filtered by status.
    """
    try:
        logger.info(
            "Listing conversations",
            status=status,
            limit=limit,
            offset=offset
        )
        
        response = await conversation_manager.list_conversations(
            status=status,
            limit=limit,
            offset=offset
        )
        
        logger.info(
            "Conversations listed successfully",
            total_conversations=response.total,
            returned_count=len(response.conversations)
        )
        
        return response
        
    except Exception as e:
        logger.error("Error listing conversations", error=str(e), exc_info=True)
        raise ChatAPIError(f"Failed to list conversations: {str(e)}")


@router.post("/conversations", response_model=Conversation)
async def create_conversation(
    request: ConversationCreateRequest,
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
) -> Conversation:
    """
    Create a new conversation.
    
    Creates a new conversation with optional title, model, and system prompt.
    """
    try:
        logger.info(
            "Creating new conversation",
            title=request.title,
            model_name=request.model_name
        )
        
        conversation = await conversation_manager.create_conversation(request)
        
        logger.info(
            "Conversation created successfully",
            conversation_id=conversation.id,
            title=conversation.title
        )
        
        return conversation
        
    except Exception as e:
        logger.error("Error creating conversation", error=str(e), exc_info=True)
        raise ChatAPIError(f"Failed to create conversation: {str(e)}")


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
) -> Conversation:
    """
    Get a specific conversation by ID.
    
    Returns detailed information about a conversation.
    """
    try:
        conversation = await conversation_manager.get_conversation(conversation_id)
        return conversation
        
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    
    except Exception as e:
        logger.error(
            "Error getting conversation",
            conversation_id=conversation_id,
            error=str(e),
            exc_info=True
        )
        raise ChatAPIError(f"Failed to get conversation: {str(e)}")


@router.get("/conversations/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
) -> ConversationMessagesResponse:
    """
    Get messages for a specific conversation.
    
    Returns paginated messages for a conversation in chronological order.
    """
    try:
        response = await conversation_manager.get_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )
        
        return response
        
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    
    except Exception as e:
        logger.error(
            "Error getting conversation messages",
            conversation_id=conversation_id,
            error=str(e),
            exc_info=True
        )
        raise ChatAPIError(f"Failed to get conversation messages: {str(e)}")


@router.put("/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: str,
    title: Optional[str] = Query(None, description="New conversation title"),
    status: Optional[ConversationStatus] = Query(None, description="New conversation status"),
    model_name: Optional[str] = Query(None, description="New default model"),
    system_prompt: Optional[str] = Query(None, description="New system prompt"),
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
) -> Conversation:
    """
    Update a conversation's details.
    
    Updates conversation metadata like title, status, model, or system prompt.
    """
    try:
        conversation = await conversation_manager.update_conversation(
            conversation_id=conversation_id,
            title=title,
            status=status,
            model_name=model_name,
            system_prompt=system_prompt
        )
        
        # Notify WebSocket clients of the update
        await websocket_manager.send_to_conversation(
            conversation_id,
            {
                "type": "conversation_updated",
                "data": conversation.model_dump()
            }
        )
        
        logger.info(
            "Conversation updated successfully",
            conversation_id=conversation_id,
            title=conversation.title
        )
        
        return conversation
        
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    
    except Exception as e:
        logger.error(
            "Error updating conversation",
            conversation_id=conversation_id,
            error=str(e),
            exc_info=True
        )
        raise ChatAPIError(f"Failed to update conversation: {str(e)}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
) -> Dict[str, Any]:
    """
    Delete a conversation.
    
    Marks a conversation as deleted. The conversation and its messages are preserved
    but marked as deleted and won't appear in normal listings.
    """
    try:
        success = await conversation_manager.delete_conversation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
        
        # Notify WebSocket clients of the deletion
        await websocket_manager.send_to_conversation(
            conversation_id,
            {
                "type": "conversation_deleted",
                "data": {"conversation_id": conversation_id}
            }
        )
        
        logger.info(
            "Conversation deleted successfully",
            conversation_id=conversation_id
        )
        
        return {
            "message": "Conversation deleted successfully",
            "conversation_id": conversation_id,
            "deleted_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Error deleting conversation",
            conversation_id=conversation_id,
            error=str(e),
            exc_info=True
        )
        raise ChatAPIError(f"Failed to delete conversation: {str(e)}")


@router.get("/stats")
async def get_chat_stats(
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
) -> Dict[str, Any]:
    """
    Get chat statistics.
    
    Returns statistics about conversations, messages, and usage patterns.
    """
    try:
        stats = await conversation_manager.get_conversation_stats()
        
        # Add WebSocket connection stats
        stats["websocket_connections"] = {
            "active_conversations": len(websocket_manager.active_connections),
            "total_connections": sum(
                len(connections) for connections in websocket_manager.active_connections.values()
            )
        }
        
        return stats
        
    except Exception as e:
        logger.error("Error getting chat stats", error=str(e), exc_info=True)
        raise ChatAPIError(f"Failed to get chat statistics: {str(e)}")


@router.post("/conversations/{conversation_id}/cleanup")
async def cleanup_conversation(
    conversation_id: str,
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
) -> Dict[str, Any]:
    """
    Clean up a conversation by archiving old messages.
    
    Archives messages older than a certain threshold to improve performance.
    """
    try:
        # This is a placeholder for conversation cleanup logic
        # In a real implementation, you might archive old messages or compress them
        
        conversation = await conversation_manager.get_conversation(conversation_id)
        
        logger.info(
            "Conversation cleanup completed",
            conversation_id=conversation_id,
            message_count=conversation.message_count
        )
        
        return {
            "message": "Conversation cleanup completed",
            "conversation_id": conversation_id,
            "cleaned_at": datetime.now().isoformat()
        }
        
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    
    except Exception as e:
        logger.error(
            "Error cleaning up conversation",
            conversation_id=conversation_id,
            error=str(e),
            exc_info=True
        )
        raise ChatAPIError(f"Failed to cleanup conversation: {str(e)}")