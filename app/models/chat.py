"""Chat-related data models."""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import Field, field_validator
from datetime import datetime

from .common import BaseModel, TimestampMixin, IDMixin, MetadataMixin
from .search import SearchResult


class MessageRole(str, Enum):
    """Chat message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationStatus(str, Enum):
    """Conversation status."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ChatMessage(IDMixin, TimestampMixin, MetadataMixin):
    """Chat message model."""
    
    conversation_id: str = Field(
        ...,
        description="ID of the conversation this message belongs to"
    )
    
    content: str = Field(
        ...,
        min_length=1,
        description="Content of the message"
    )
    
    role: MessageRole = Field(
        ...,
        description="Role of the message sender (user, assistant, system)"
    )
    
    sources: Optional[List[SearchResult]] = Field(
        None,
        description="Source documents/chunks used to generate this message (for assistant messages)"
    )
    
    model_name: Optional[str] = Field(
        None,
        description="Name of the model used to generate this message (for assistant messages)"
    )
    
    token_count: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated token count of the message content"
    )
    
    generation_time: Optional[float] = Field(
        None,
        ge=0.0,
        description="Time taken to generate this message in seconds (for assistant messages)"
    )
    
    context_used: Optional[str] = Field(
        None,
        description="Context that was used to generate this message (for assistant messages)"
    )
    
    confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score of the generated response (for assistant messages)"
    )
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        """Validate message content."""
        if not v or v.isspace():
            raise ValueError("Message content cannot be empty or whitespace only")
        return v.strip()
    
    @property
    def is_user_message(self) -> bool:
        """Check if this is a user message."""
        return self.role == MessageRole.USER
    
    @property
    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message."""
        return self.role == MessageRole.ASSISTANT
    
    @property
    def has_sources(self) -> bool:
        """Check if message has source citations."""
        return self.sources is not None and len(self.sources) > 0
    
    def get_content_preview(self, max_length: int = 100) -> str:
        """Get a preview of the message content."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
    
    def to_summary(self) -> Dict[str, Any]:
        """Get a summary representation of the message."""
        return {
            "id": self.id,
            "role": self.role,
            "content_preview": self.get_content_preview(),
            "created_at": self.created_at,
            "has_sources": self.has_sources,
            "source_count": len(self.sources) if self.sources else 0,
            "token_count": self.token_count,
            "generation_time": self.generation_time
        }


class Conversation(IDMixin, TimestampMixin, MetadataMixin):
    """Conversation model representing a chat session."""
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Title of the conversation"
    )
    
    status: ConversationStatus = Field(
        default=ConversationStatus.ACTIVE,
        description="Status of the conversation"
    )
    
    message_count: int = Field(
        default=0,
        ge=0,
        description="Number of messages in this conversation"
    )
    
    last_message_at: Optional[datetime] = Field(
        None,
        description="Timestamp of the last message in this conversation"
    )
    
    model_name: Optional[str] = Field(
        None,
        description="Default model used for this conversation"
    )
    
    system_prompt: Optional[str] = Field(
        None,
        description="System prompt used for this conversation"
    )
    
    total_tokens: Optional[int] = Field(
        None,
        ge=0,
        description="Total tokens used in this conversation"
    )
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        """Validate conversation title."""
        if not v or v.isspace():
            raise ValueError("Conversation title cannot be empty or whitespace only")
        return v.strip()
    
    @property
    def is_active(self) -> bool:
        """Check if conversation is active."""
        return self.status == ConversationStatus.ACTIVE
    
    @property
    def has_messages(self) -> bool:
        """Check if conversation has messages."""
        return self.message_count > 0
    
    def update_last_message(self, message_timestamp: datetime) -> None:
        """Update last message timestamp and increment message count."""
        self.last_message_at = message_timestamp
        self.message_count += 1
        self.updated_at = datetime.now()
    
    def to_summary(self) -> Dict[str, Any]:
        """Get a summary representation of the conversation."""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "message_count": self.message_count,
            "created_at": self.created_at,
            "last_message_at": self.last_message_at,
            "model_name": self.model_name,
            "total_tokens": self.total_tokens
        }


class ChatRequest(BaseModel):
    """Request model for sending a chat message."""
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User message content"
    )
    
    conversation_id: Optional[str] = Field(
        None,
        description="ID of existing conversation (if continuing a conversation)"
    )
    
    model_name: Optional[str] = Field(
        None,
        description="Specific model to use for this message"
    )
    
    system_prompt: Optional[str] = Field(
        None,
        description="Custom system prompt for this message"
    )
    
    max_context_tokens: Optional[int] = Field(
        None,
        ge=100,
        le=8000,
        description="Maximum tokens to use for context retrieval"
    )
    
    include_sources: bool = Field(
        default=True,
        description="Whether to include source citations in the response"
    )
    
    stream: bool = Field(
        default=False,
        description="Whether to stream the response"
    )


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    
    message: ChatMessage = Field(..., description="The assistant's response message")
    conversation: Conversation = Field(..., description="Updated conversation information")
    sources_used: Optional[List[SearchResult]] = Field(
        None,
        description="Sources that were used to generate the response"
    )
    context_retrieved: Optional[str] = Field(
        None,
        description="Context that was retrieved for generating the response"
    )
    generation_stats: Optional[Dict[str, Any]] = Field(
        None,
        description="Statistics about the response generation"
    )


class ConversationCreateRequest(BaseModel):
    """Request model for creating a new conversation."""
    
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Title for the conversation (auto-generated if not provided)"
    )
    
    model_name: Optional[str] = Field(
        None,
        description="Default model to use for this conversation"
    )
    
    system_prompt: Optional[str] = Field(
        None,
        description="System prompt for this conversation"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for the conversation"
    )


class ConversationListResponse(BaseModel):
    """Response model for listing conversations."""
    
    conversations: List[Conversation] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")


class ConversationMessagesResponse(BaseModel):
    """Response model for getting conversation messages."""
    
    conversation: Conversation = Field(..., description="Conversation information")
    messages: List[ChatMessage] = Field(..., description="List of messages in the conversation")
    total_messages: int = Field(..., description="Total number of messages")


class ChatStats(BaseModel):
    """Model for chat statistics."""
    
    total_conversations: int = Field(..., description="Total number of conversations")
    total_messages: int = Field(..., description="Total number of messages")
    avg_messages_per_conversation: float = Field(..., description="Average messages per conversation")
    total_tokens_used: int = Field(..., description="Total tokens used across all conversations")
    avg_response_time: float = Field(..., description="Average response generation time")
    model_usage: Dict[str, int] = Field(..., description="Usage count by model")
    
    
class StreamingChatResponse(BaseModel):
    """Model for streaming chat response chunks."""
    
    conversation_id: str = Field(..., description="ID of the conversation")
    message_id: str = Field(..., description="ID of the message being streamed")
    content_delta: str = Field(..., description="Incremental content for this chunk")
    is_complete: bool = Field(default=False, description="Whether this is the final chunk")
    sources: Optional[List[SearchResult]] = Field(
        None,
        description="Sources (included only in the final chunk)"
    )
    generation_stats: Optional[Dict[str, Any]] = Field(
        None,
        description="Generation statistics (included only in the final chunk)"
    )