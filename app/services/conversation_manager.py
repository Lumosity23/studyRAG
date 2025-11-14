"""Conversation persistence and history management."""

import json
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
from pathlib import Path

from app.models.chat import (
    Conversation, ChatMessage, MessageRole, ConversationStatus,
    ConversationCreateRequest, ConversationListResponse, ConversationMessagesResponse
)
from app.core.config import get_settings
from app.core.exceptions import APIException


class ConversationNotFoundError(APIException):
    """Conversation not found error."""
    
    def __init__(self, conversation_id: str):
        super().__init__(
            "CHAT_003",
            f"Conversation '{conversation_id}' not found",
            404,
            {"conversation_id": conversation_id}
        )


class ConversationManager:
    """Manages conversation persistence and history."""
    
    def __init__(self, settings=None):
        """Initialize conversation manager."""
        self.settings = settings or get_settings()
        self.conversations_dir = Path(self.settings.PROCESSED_DIR) / "conversations"
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for active conversations
        self._conversation_cache: Dict[str, Conversation] = {}
        self._message_cache: Dict[str, List[ChatMessage]] = {}
        self._cache_lock = asyncio.Lock()
    
    async def create_conversation(
        self,
        request: ConversationCreateRequest
    ) -> Conversation:
        """Create a new conversation."""
        conversation_id = str(uuid.uuid4())
        
        # Generate title if not provided
        title = request.title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        conversation = Conversation(
            id=conversation_id,
            title=title,
            status=ConversationStatus.ACTIVE,
            model_name=request.model_name,
            system_prompt=request.system_prompt,
            metadata=request.metadata or {}
        )
        
        # Save to disk and cache
        await self._save_conversation(conversation)
        
        async with self._cache_lock:
            self._conversation_cache[conversation_id] = conversation
            self._message_cache[conversation_id] = []
        
        return conversation
    
    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Get a conversation by ID."""
        # Check cache first
        async with self._cache_lock:
            if conversation_id in self._conversation_cache:
                return self._conversation_cache[conversation_id]
        
        # Load from disk
        conversation = await self._load_conversation(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(conversation_id)
        
        # Cache it
        async with self._cache_lock:
            self._conversation_cache[conversation_id] = conversation
        
        return conversation
    
    async def list_conversations(
        self,
        status: Optional[ConversationStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> ConversationListResponse:
        """List conversations with optional filtering."""
        conversations = []
        
        # Load all conversation files
        for conv_file in self.conversations_dir.glob("*.json"):
            try:
                conversation = await self._load_conversation_from_file(conv_file)
                if conversation and (status is None or conversation.status == status):
                    conversations.append(conversation)
            except Exception:
                continue  # Skip corrupted files
        
        # Sort by last message time (most recent first)
        conversations.sort(
            key=lambda c: c.last_message_at or c.created_at,
            reverse=True
        )
        
        # Apply pagination
        total = len(conversations)
        conversations = conversations[offset:offset + limit]
        
        return ConversationListResponse(
            conversations=conversations,
            total=total
        )
    
    async def add_message(
        self,
        conversation_id: str,
        content: str,
        role: MessageRole,
        sources: Optional[List[Any]] = None,
        model_name: Optional[str] = None,
        generation_time: Optional[float] = None,
        context_used: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """Add a message to a conversation."""
        # Ensure conversation exists
        conversation = await self.get_conversation(conversation_id)
        
        # Create message
        message = ChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            content=content,
            role=role,
            sources=sources,
            model_name=model_name,
            generation_time=generation_time,
            context_used=context_used,
            metadata=metadata or {}
        )
        
        # Add to cache
        async with self._cache_lock:
            if conversation_id not in self._message_cache:
                self._message_cache[conversation_id] = await self._load_messages(conversation_id)
            self._message_cache[conversation_id].append(message)
        
        # Update conversation
        conversation.update_last_message(message.created_at)
        
        # Save both message and updated conversation
        await self._save_message(message)
        await self._save_conversation(conversation)
        
        return message
    
    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> ConversationMessagesResponse:
        """Get messages for a conversation."""
        conversation = await self.get_conversation(conversation_id)
        
        # Check cache first
        async with self._cache_lock:
            if conversation_id in self._message_cache:
                messages = self._message_cache[conversation_id]
            else:
                messages = await self._load_messages(conversation_id)
                self._message_cache[conversation_id] = messages
        
        # Apply pagination (most recent first)
        total_messages = len(messages)
        messages = list(reversed(messages))  # Reverse for chronological order
        messages = messages[offset:offset + limit]
        
        return ConversationMessagesResponse(
            conversation=conversation,
            messages=messages,
            total_messages=total_messages
        )
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        max_messages: int = 20
    ) -> List[ChatMessage]:
        """Get recent conversation history for context."""
        messages_response = await self.get_messages(conversation_id, limit=max_messages)
        return messages_response.messages
    
    async def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        status: Optional[ConversationStatus] = None,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Update conversation details."""
        conversation = await self.get_conversation(conversation_id)
        
        if title is not None:
            conversation.title = title
        if status is not None:
            conversation.status = status
        if model_name is not None:
            conversation.model_name = model_name
        if system_prompt is not None:
            conversation.system_prompt = system_prompt
        if metadata is not None:
            conversation.metadata.update(metadata)
        
        conversation.updated_at = datetime.now()
        
        await self._save_conversation(conversation)
        
        # Update cache
        async with self._cache_lock:
            self._conversation_cache[conversation_id] = conversation
        
        return conversation
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        try:
            # Mark as deleted instead of actually deleting
            conversation = await self.get_conversation(conversation_id)
            conversation.status = ConversationStatus.DELETED
            conversation.updated_at = datetime.now()
            
            await self._save_conversation(conversation)
            
            # Remove from cache
            async with self._cache_lock:
                self._conversation_cache.pop(conversation_id, None)
                self._message_cache.pop(conversation_id, None)
            
            return True
            
        except ConversationNotFoundError:
            return False
    
    async def cleanup_old_conversations(self, days: int = 30) -> int:
        """Clean up conversations older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        conversations_response = await self.list_conversations()
        
        for conversation in conversations_response.conversations:
            if (conversation.last_message_at or conversation.created_at) < cutoff_date:
                if conversation.status != ConversationStatus.DELETED:
                    await self.update_conversation(
                        conversation.id,
                        status=ConversationStatus.ARCHIVED
                    )
                    cleaned_count += 1
        
        return cleaned_count
    
    async def get_conversation_stats(self) -> Dict[str, Any]:
        """Get statistics about conversations."""
        conversations_response = await self.list_conversations()
        conversations = conversations_response.conversations
        
        total_conversations = len(conversations)
        active_conversations = len([c for c in conversations if c.status == ConversationStatus.ACTIVE])
        
        total_messages = sum(c.message_count for c in conversations)
        avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
        
        # Model usage stats
        model_usage = {}
        for conv in conversations:
            if conv.model_name:
                model_usage[conv.model_name] = model_usage.get(conv.model_name, 0) + 1
        
        return {
            "total_conversations": total_conversations,
            "active_conversations": active_conversations,
            "archived_conversations": len([c for c in conversations if c.status == ConversationStatus.ARCHIVED]),
            "deleted_conversations": len([c for c in conversations if c.status == ConversationStatus.DELETED]),
            "total_messages": total_messages,
            "avg_messages_per_conversation": round(avg_messages, 2),
            "model_usage": model_usage
        }
    
    async def _save_conversation(self, conversation: Conversation) -> None:
        """Save conversation to disk."""
        file_path = self.conversations_dir / f"{conversation.id}.json"
        
        data = {
            "conversation": conversation.model_dump(mode='json'),
            "saved_at": datetime.now().isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def _load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load conversation from disk."""
        file_path = self.conversations_dir / f"{conversation_id}.json"
        return await self._load_conversation_from_file(file_path)
    
    async def _load_conversation_from_file(self, file_path: Path) -> Optional[Conversation]:
        """Load conversation from a specific file."""
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return Conversation(**data["conversation"])
            
        except Exception:
            return None
    
    async def _save_message(self, message: ChatMessage) -> None:
        """Save message to disk."""
        messages_dir = self.conversations_dir / "messages" / message.conversation_id
        messages_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = messages_dir / f"{message.id}.json"
        
        data = {
            "message": message.model_dump(mode='json'),
            "saved_at": datetime.now().isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def _load_messages(self, conversation_id: str) -> List[ChatMessage]:
        """Load all messages for a conversation."""
        messages_dir = self.conversations_dir / "messages" / conversation_id
        
        if not messages_dir.exists():
            return []
        
        messages = []
        
        for message_file in messages_dir.glob("*.json"):
            try:
                with open(message_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                message = ChatMessage(**data["message"])
                messages.append(message)
                
            except Exception:
                continue  # Skip corrupted files
        
        # Sort by creation time
        messages.sort(key=lambda m: m.created_at)
        
        return messages