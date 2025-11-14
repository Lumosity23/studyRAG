"""Tests for conversation manager."""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.services.conversation_manager import (
    ConversationManager, ConversationNotFoundError
)
from app.models.chat import (
    Conversation, ChatMessage, MessageRole, ConversationStatus,
    ConversationCreateRequest, ConversationListResponse
)
from app.core.config import Settings


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_settings(temp_dir):
    """Mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.PROCESSED_DIR = str(temp_dir)
    return settings


@pytest.fixture
def conversation_manager(mock_settings):
    """Create conversation manager for testing."""
    return ConversationManager(mock_settings)


@pytest.fixture
def sample_conversation_request():
    """Create sample conversation request."""
    return ConversationCreateRequest(
        title="Test Conversation",
        model_name="llama2",
        system_prompt="You are a helpful assistant.",
        metadata={"test": True}
    )


class TestConversationManager:
    """Test ConversationManager class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, conversation_manager, temp_dir):
        """Test conversation manager initialization."""
        assert conversation_manager is not None
        
        # Check that conversations directory was created
        conversations_dir = temp_dir / "conversations"
        assert conversations_dir.exists()
        assert conversations_dir.is_dir()
    
    @pytest.mark.asyncio
    async def test_create_conversation(self, conversation_manager, sample_conversation_request):
        """Test creating a new conversation."""
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        assert conversation is not None
        assert conversation.title == "Test Conversation"
        assert conversation.model_name == "llama2"
        assert conversation.system_prompt == "You are a helpful assistant."
        assert conversation.status == ConversationStatus.ACTIVE
        assert conversation.message_count == 0
        assert conversation.metadata["test"] is True
        
        # Check that conversation was saved to disk
        conv_file = conversation_manager.conversations_dir / f"{conversation.id}.json"
        assert conv_file.exists()
    
    @pytest.mark.asyncio
    async def test_create_conversation_auto_title(self, conversation_manager):
        """Test creating conversation with auto-generated title."""
        request = ConversationCreateRequest()
        conversation = await conversation_manager.create_conversation(request)
        
        assert conversation.title is not None
        assert len(conversation.title) > 0
        assert "Conversation" in conversation.title
    
    @pytest.mark.asyncio
    async def test_get_conversation(self, conversation_manager, sample_conversation_request):
        """Test getting a conversation by ID."""
        # Create conversation
        created_conv = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Get conversation
        retrieved_conv = await conversation_manager.get_conversation(created_conv.id)
        
        assert retrieved_conv.id == created_conv.id
        assert retrieved_conv.title == created_conv.title
        assert retrieved_conv.model_name == created_conv.model_name
    
    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, conversation_manager):
        """Test getting non-existent conversation."""
        with pytest.raises(ConversationNotFoundError) as exc_info:
            await conversation_manager.get_conversation("nonexistent-id")
        
        assert "not found" in str(exc_info.value)
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_conversation_caching(self, conversation_manager, sample_conversation_request):
        """Test conversation caching."""
        # Create conversation
        created_conv = await conversation_manager.create_conversation(sample_conversation_request)
        
        # First get should load from disk
        conv1 = await conversation_manager.get_conversation(created_conv.id)
        
        # Second get should use cache
        conv2 = await conversation_manager.get_conversation(created_conv.id)
        
        assert conv1 is conv2  # Should be same object from cache
    
    @pytest.mark.asyncio
    async def test_list_conversations_empty(self, conversation_manager):
        """Test listing conversations when none exist."""
        response = await conversation_manager.list_conversations()
        
        assert isinstance(response, ConversationListResponse)
        assert len(response.conversations) == 0
        assert response.total == 0
    
    @pytest.mark.asyncio
    async def test_list_conversations_with_data(self, conversation_manager):
        """Test listing conversations with data."""
        # Create multiple conversations
        requests = [
            ConversationCreateRequest(title=f"Conv {i}", model_name="llama2")
            for i in range(3)
        ]
        
        created_convs = []
        for request in requests:
            conv = await conversation_manager.create_conversation(request)
            created_convs.append(conv)
        
        # List conversations
        response = await conversation_manager.list_conversations()
        
        assert len(response.conversations) == 3
        assert response.total == 3
        
        # Should be sorted by creation time (most recent first)
        titles = [conv.title for conv in response.conversations]
        assert "Conv 2" in titles
        assert "Conv 1" in titles
        assert "Conv 0" in titles
    
    @pytest.mark.asyncio
    async def test_list_conversations_with_status_filter(self, conversation_manager):
        """Test listing conversations with status filter."""
        # Create conversations with different statuses
        active_request = ConversationCreateRequest(title="Active Conv")
        active_conv = await conversation_manager.create_conversation(active_request)
        
        archived_request = ConversationCreateRequest(title="Archived Conv")
        archived_conv = await conversation_manager.create_conversation(archived_request)
        
        # Update one to archived status
        await conversation_manager.update_conversation(
            archived_conv.id,
            status=ConversationStatus.ARCHIVED
        )
        
        # List only active conversations
        active_response = await conversation_manager.list_conversations(
            status=ConversationStatus.ACTIVE
        )
        
        assert len(active_response.conversations) == 1
        assert active_response.conversations[0].title == "Active Conv"
        
        # List only archived conversations
        archived_response = await conversation_manager.list_conversations(
            status=ConversationStatus.ARCHIVED
        )
        
        assert len(archived_response.conversations) == 1
        assert archived_response.conversations[0].title == "Archived Conv"
    
    @pytest.mark.asyncio
    async def test_list_conversations_pagination(self, conversation_manager):
        """Test conversation listing with pagination."""
        # Create multiple conversations
        for i in range(5):
            request = ConversationCreateRequest(title=f"Conv {i}")
            await conversation_manager.create_conversation(request)
        
        # Test pagination
        page1 = await conversation_manager.list_conversations(limit=2, offset=0)
        assert len(page1.conversations) == 2
        assert page1.total == 5
        
        page2 = await conversation_manager.list_conversations(limit=2, offset=2)
        assert len(page2.conversations) == 2
        assert page2.total == 5
        
        # Ensure different conversations
        page1_ids = {conv.id for conv in page1.conversations}
        page2_ids = {conv.id for conv in page2.conversations}
        assert page1_ids.isdisjoint(page2_ids)
    
    @pytest.mark.asyncio
    async def test_add_message(self, conversation_manager, sample_conversation_request):
        """Test adding a message to conversation."""
        # Create conversation
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Add user message
        message = await conversation_manager.add_message(
            conversation.id,
            "Hello, how are you?",
            MessageRole.USER
        )
        
        assert message is not None
        assert message.conversation_id == conversation.id
        assert message.content == "Hello, how are you?"
        assert message.role == MessageRole.USER
        assert message.created_at is not None
        
        # Check that conversation was updated
        updated_conv = await conversation_manager.get_conversation(conversation.id)
        assert updated_conv.message_count == 1
        assert updated_conv.last_message_at is not None
    
    @pytest.mark.asyncio
    async def test_add_message_with_metadata(self, conversation_manager, sample_conversation_request):
        """Test adding message with additional metadata."""
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Mock search results for sources
        mock_sources = [MagicMock()]
        
        message = await conversation_manager.add_message(
            conversation.id,
            "This is an AI response.",
            MessageRole.ASSISTANT,
            sources=mock_sources,
            model_name="llama2",
            generation_time=1.5,
            context_used="Some context",
            metadata={"confidence": 0.95}
        )
        
        assert message.sources == mock_sources
        assert message.model_name == "llama2"
        assert message.generation_time == 1.5
        assert message.context_used == "Some context"
        assert message.metadata["confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_get_messages(self, conversation_manager, sample_conversation_request):
        """Test getting messages for a conversation."""
        # Create conversation
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Add multiple messages
        messages_data = [
            ("Hello", MessageRole.USER),
            ("Hi there!", MessageRole.ASSISTANT),
            ("How are you?", MessageRole.USER),
            ("I'm doing well, thanks!", MessageRole.ASSISTANT)
        ]
        
        for content, role in messages_data:
            await conversation_manager.add_message(conversation.id, content, role)
        
        # Get messages
        response = await conversation_manager.get_messages(conversation.id)
        
        assert len(response.messages) == 4
        assert response.total_messages == 4
        assert response.conversation.id == conversation.id
        
        # Check message order (should be chronological)
        assert response.messages[0].content == "Hello"
        assert response.messages[1].content == "Hi there!"
        assert response.messages[2].content == "How are you?"
        assert response.messages[3].content == "I'm doing well, thanks!"
    
    @pytest.mark.asyncio
    async def test_get_messages_pagination(self, conversation_manager, sample_conversation_request):
        """Test getting messages with pagination."""
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Add multiple messages
        for i in range(5):
            await conversation_manager.add_message(
                conversation.id,
                f"Message {i}",
                MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            )
        
        # Test pagination
        page1 = await conversation_manager.get_messages(conversation.id, limit=2, offset=0)
        assert len(page1.messages) == 2
        assert page1.total_messages == 5
        
        page2 = await conversation_manager.get_messages(conversation.id, limit=2, offset=2)
        assert len(page2.messages) == 2
        assert page2.total_messages == 5
    
    @pytest.mark.asyncio
    async def test_get_conversation_history(self, conversation_manager, sample_conversation_request):
        """Test getting conversation history for context."""
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Add messages
        for i in range(25):  # More than default limit
            await conversation_manager.add_message(
                conversation.id,
                f"Message {i}",
                MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            )
        
        # Get history with default limit
        history = await conversation_manager.get_conversation_history(conversation.id)
        
        assert len(history) <= 20  # Default max_messages
        
        # Get history with custom limit
        history_limited = await conversation_manager.get_conversation_history(
            conversation.id,
            max_messages=5
        )
        
        assert len(history_limited) <= 5
    
    @pytest.mark.asyncio
    async def test_update_conversation(self, conversation_manager, sample_conversation_request):
        """Test updating conversation details."""
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Update conversation
        updated_conv = await conversation_manager.update_conversation(
            conversation.id,
            title="Updated Title",
            status=ConversationStatus.ARCHIVED,
            model_name="new_model",
            system_prompt="New system prompt",
            metadata={"updated": True}
        )
        
        assert updated_conv.title == "Updated Title"
        assert updated_conv.status == ConversationStatus.ARCHIVED
        assert updated_conv.model_name == "new_model"
        assert updated_conv.system_prompt == "New system prompt"
        assert updated_conv.metadata["updated"] is True
        assert updated_conv.metadata["test"] is True  # Original metadata preserved
        assert updated_conv.updated_at > conversation.updated_at
    
    @pytest.mark.asyncio
    async def test_update_conversation_partial(self, conversation_manager, sample_conversation_request):
        """Test partial conversation update."""
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Update only title
        updated_conv = await conversation_manager.update_conversation(
            conversation.id,
            title="New Title Only"
        )
        
        assert updated_conv.title == "New Title Only"
        assert updated_conv.model_name == conversation.model_name  # Unchanged
        assert updated_conv.system_prompt == conversation.system_prompt  # Unchanged
    
    @pytest.mark.asyncio
    async def test_delete_conversation(self, conversation_manager, sample_conversation_request):
        """Test deleting a conversation."""
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Delete conversation
        result = await conversation_manager.delete_conversation(conversation.id)
        assert result is True
        
        # Conversation should be marked as deleted, not actually removed
        deleted_conv = await conversation_manager.get_conversation(conversation.id)
        assert deleted_conv.status == ConversationStatus.DELETED
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(self, conversation_manager):
        """Test deleting non-existent conversation."""
        result = await conversation_manager.delete_conversation("nonexistent-id")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cleanup_old_conversations(self, conversation_manager):
        """Test cleaning up old conversations."""
        # Create old conversation
        old_request = ConversationCreateRequest(title="Old Conv")
        old_conv = await conversation_manager.create_conversation(old_request)
        
        # Manually set old timestamp
        old_conv.created_at = datetime.now() - timedelta(days=35)
        old_conv.last_message_at = datetime.now() - timedelta(days=35)
        await conversation_manager._save_conversation(old_conv)
        
        # Create recent conversation
        recent_request = ConversationCreateRequest(title="Recent Conv")
        recent_conv = await conversation_manager.create_conversation(recent_request)
        
        # Cleanup conversations older than 30 days
        cleaned_count = await conversation_manager.cleanup_old_conversations(days=30)
        
        assert cleaned_count == 1
        
        # Check that old conversation was archived
        updated_old = await conversation_manager.get_conversation(old_conv.id)
        assert updated_old.status == ConversationStatus.ARCHIVED
        
        # Check that recent conversation is still active
        updated_recent = await conversation_manager.get_conversation(recent_conv.id)
        assert updated_recent.status == ConversationStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_get_conversation_stats(self, conversation_manager):
        """Test getting conversation statistics."""
        # Create conversations with different statuses and models
        requests = [
            ConversationCreateRequest(title="Active 1", model_name="llama2"),
            ConversationCreateRequest(title="Active 2", model_name="llama2"),
            ConversationCreateRequest(title="Archived 1", model_name="codellama"),
        ]
        
        conversations = []
        for request in requests:
            conv = await conversation_manager.create_conversation(request)
            conversations.append(conv)
        
        # Archive one conversation
        await conversation_manager.update_conversation(
            conversations[2].id,
            status=ConversationStatus.ARCHIVED
        )
        
        # Add messages to conversations
        await conversation_manager.add_message(conversations[0].id, "Hello", MessageRole.USER)
        await conversation_manager.add_message(conversations[0].id, "Hi", MessageRole.ASSISTANT)
        await conversation_manager.add_message(conversations[1].id, "Test", MessageRole.USER)
        
        # Get stats
        stats = await conversation_manager.get_conversation_stats()
        
        assert stats["total_conversations"] == 3
        assert stats["active_conversations"] == 2
        assert stats["archived_conversations"] == 1
        assert stats["deleted_conversations"] == 0
        assert stats["total_messages"] == 3
        assert stats["avg_messages_per_conversation"] == 1.0
        assert stats["model_usage"]["llama2"] == 2
        assert stats["model_usage"]["codellama"] == 1
    
    @pytest.mark.asyncio
    async def test_message_caching(self, conversation_manager, sample_conversation_request):
        """Test message caching functionality."""
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Add message
        await conversation_manager.add_message(conversation.id, "Test", MessageRole.USER)
        
        # First get should load from disk
        response1 = await conversation_manager.get_messages(conversation.id)
        
        # Second get should use cache
        response2 = await conversation_manager.get_messages(conversation.id)
        
        assert len(response1.messages) == len(response2.messages)
        assert response1.messages[0].content == response2.messages[0].content
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, conversation_manager, sample_conversation_request):
        """Test concurrent access to conversation manager."""
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Simulate concurrent message additions
        async def add_messages(start_idx):
            for i in range(start_idx, start_idx + 5):
                await conversation_manager.add_message(
                    conversation.id,
                    f"Message {i}",
                    MessageRole.USER
                )
        
        # Run concurrent tasks
        await asyncio.gather(
            add_messages(0),
            add_messages(5),
            add_messages(10)
        )
        
        # Check that all messages were added
        response = await conversation_manager.get_messages(conversation.id)
        assert len(response.messages) == 15
    
    @pytest.mark.asyncio
    async def test_file_persistence(self, conversation_manager, sample_conversation_request, temp_dir):
        """Test that data persists to files correctly."""
        conversation = await conversation_manager.create_conversation(sample_conversation_request)
        
        # Add message
        message = await conversation_manager.add_message(
            conversation.id,
            "Test message",
            MessageRole.USER
        )
        
        # Check conversation file exists
        conv_file = temp_dir / "conversations" / f"{conversation.id}.json"
        assert conv_file.exists()
        
        # Check message file exists
        msg_file = temp_dir / "conversations" / "messages" / conversation.id / f"{message.id}.json"
        assert msg_file.exists()
        
        # Create new manager instance to test loading from disk
        new_manager = ConversationManager(conversation_manager.settings)
        
        # Should be able to load conversation
        loaded_conv = await new_manager.get_conversation(conversation.id)
        assert loaded_conv.title == conversation.title
        
        # Should be able to load messages
        messages_response = await new_manager.get_messages(conversation.id)
        assert len(messages_response.messages) == 1
        assert messages_response.messages[0].content == "Test message"