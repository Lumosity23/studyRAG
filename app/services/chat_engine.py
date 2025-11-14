"""Chat engine with RAG integration and conversation management."""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime

from app.models.chat import (
    ChatMessage, Conversation, MessageRole, ChatRequest, ChatResponse,
    StreamingChatResponse, ConversationCreateRequest
)
from app.models.search import SearchResult
from app.services.ollama_client import OllamaClient, OllamaModelError, OllamaConnectionError
from app.services.conversation_manager import ConversationManager
from app.services.prompt_templates import PromptBuilder, PromptTemplate, get_prompt_builder
from app.services.search_engine import SearchEngine
from app.core.config import get_settings
from app.core.exceptions import APIException


logger = logging.getLogger(__name__)


class ChatContextError(APIException):
    """Chat context error."""
    
    def __init__(self, message: str, details: Dict = None):
        super().__init__("CHAT_003", message, 400, details)


class ChatEngine:
    """Main chat engine with RAG integration and conversation management."""
    
    def __init__(
        self,
        search_engine: SearchEngine,
        ollama_client: Optional[OllamaClient] = None,
        conversation_manager: Optional[ConversationManager] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        settings=None
    ):
        """Initialize chat engine."""
        self.settings = settings or get_settings()
        self.search_engine = search_engine
        self.ollama_client = ollama_client or OllamaClient(self.settings)
        self.conversation_manager = conversation_manager or ConversationManager(self.settings)
        self.prompt_builder = prompt_builder or get_prompt_builder()
        
        # Default model and settings - check for demo mode first
        # Force read from environment variables (bypass cache)
        demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        llm_choice = os.getenv("LLM_CHOICE", "llama3.2")  # Default fallback
        
        logger.info(f"Chat engine init: DEMO_MODE={demo_mode}, LLM_CHOICE={llm_choice}")
        
        # Only use demo mode if explicitly requested
        if llm_choice == "demo" or (demo_mode and llm_choice in ["demo", "llama3.2"]):
            self.default_model = "demo"
            logger.info(f"Using demo mode: {self.default_model}")
        else:
            self.default_model = llm_choice
            logger.info(f"Using LLM model: {self.default_model}")
            
        self.max_context_tokens = self.settings.MAX_CONTEXT_TOKENS
        
    async def process_message(
        self,
        request: ChatRequest
    ) -> ChatResponse:
        """Process a chat message and generate RAG response."""
        start_time = time.time()
        
        try:
            # Get or create conversation
            if request.conversation_id:
                conversation = await self.conversation_manager.get_conversation(request.conversation_id)
            else:
                # Create new conversation with auto-generated title
                create_request = ConversationCreateRequest(
                    title=self._generate_conversation_title(request.message),
                    model_name=request.model_name or self.default_model,
                    system_prompt=request.system_prompt
                )
                conversation = await self.conversation_manager.create_conversation(create_request)
            
            # Add user message to conversation
            user_message = await self.conversation_manager.add_message(
                conversation.id,
                request.message,
                MessageRole.USER
            )
            
            # Get conversation history for context
            history = await self.conversation_manager.get_conversation_history(
                conversation.id,
                max_messages=10
            )
            
            # Perform semantic search for relevant context
            search_results = await self._retrieve_context(
                request.message,
                max_tokens=request.max_context_tokens or self.max_context_tokens
            )
            
            # Build context from search results
            context = self.prompt_builder.build_context_from_sources(
                search_results,
                max_tokens=request.max_context_tokens or self.max_context_tokens,
                include_metadata=True
            )
            
            # Generate response using Ollama
            model_name = request.model_name or conversation.model_name or self.default_model
            
            response_content, generation_stats = await self._generate_response(
                question=request.message,
                context=context,
                conversation_history=history[:-1],  # Exclude the just-added user message
                model_name=model_name,
                system_prompt=request.system_prompt or conversation.system_prompt
            )
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Add assistant message to conversation
            assistant_message = await self.conversation_manager.add_message(
                conversation.id,
                response_content,
                MessageRole.ASSISTANT,
                sources=search_results if request.include_sources else None,
                model_name=model_name,
                generation_time=generation_time,
                context_used=context if len(context) < 1000 else context[:1000] + "...",
                metadata={
                    "search_results_count": len(search_results),
                    "context_tokens": len(context) // 4,  # Rough estimate
                    **generation_stats
                }
            )
            
            # Update conversation with latest activity
            conversation = await self.conversation_manager.get_conversation(conversation.id)
            
            return ChatResponse(
                message=assistant_message,
                conversation=conversation,
                sources_used=search_results if request.include_sources else None,
                context_retrieved=context if len(context) < 500 else None,
                generation_stats={
                    "total_time": generation_time,
                    "model_used": model_name,
                    **generation_stats
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}", exc_info=True)
            
            # Try to add error message to conversation if it exists
            if 'conversation' in locals():
                try:
                    await self.conversation_manager.add_message(
                        conversation.id,
                        f"I apologize, but I encountered an error while processing your message: {str(e)}",
                        MessageRole.ASSISTANT,
                        metadata={"error": True, "error_message": str(e)}
                    )
                except Exception:
                    pass  # Don't fail if we can't save error message
            
            raise
    
    async def stream_message(
        self,
        request: ChatRequest
    ) -> AsyncGenerator[StreamingChatResponse, None]:
        """Stream a chat response in real-time."""
        start_time = time.time()
        
        try:
            # Get or create conversation (same as process_message)
            if request.conversation_id:
                conversation = await self.conversation_manager.get_conversation(request.conversation_id)
            else:
                create_request = ConversationCreateRequest(
                    title=self._generate_conversation_title(request.message),
                    model_name=request.model_name or self.default_model,
                    system_prompt=request.system_prompt
                )
                conversation = await self.conversation_manager.create_conversation(create_request)
            
            # Add user message
            user_message = await self.conversation_manager.add_message(
                conversation.id,
                request.message,
                MessageRole.USER
            )
            
            # Get context (same as process_message)
            history = await self.conversation_manager.get_conversation_history(
                conversation.id,
                max_messages=10
            )
            
            search_results = await self._retrieve_context(
                request.message,
                max_tokens=request.max_context_tokens or self.max_context_tokens
            )
            
            context = self.prompt_builder.build_context_from_sources(
                search_results,
                max_tokens=request.max_context_tokens or self.max_context_tokens,
                include_metadata=True
            )
            
            # Stream response
            model_name = request.model_name or conversation.model_name or self.default_model
            
            full_response = ""
            message_id = None
            
            async for chunk in self._stream_response(
                question=request.message,
                context=context,
                conversation_history=history[:-1],
                model_name=model_name,
                system_prompt=request.system_prompt or conversation.system_prompt
            ):
                if chunk.get("message", {}).get("content"):
                    content_delta = chunk["message"]["content"]
                    full_response += content_delta
                    
                    # Create message ID on first chunk
                    if message_id is None:
                        import uuid
                        message_id = str(uuid.uuid4())
                    
                    yield StreamingChatResponse(
                        conversation_id=conversation.id,
                        message_id=message_id,
                        content_delta=content_delta,
                        is_complete=False
                    )
                
                # Check if streaming is complete
                if chunk.get("done", False):
                    generation_time = time.time() - start_time
                    
                    # Save complete assistant message
                    if full_response and message_id:
                        assistant_message = await self.conversation_manager.add_message(
                            conversation.id,
                            full_response,
                            MessageRole.ASSISTANT,
                            sources=search_results if request.include_sources else None,
                            model_name=model_name,
                            generation_time=generation_time,
                            context_used=context if len(context) < 1000 else context[:1000] + "...",
                            metadata={
                                "search_results_count": len(search_results),
                                "context_tokens": len(context) // 4,
                                "streamed": True
                            }
                        )
                        
                        # Send final chunk with metadata
                        yield StreamingChatResponse(
                            conversation_id=conversation.id,
                            message_id=message_id,
                            content_delta="",
                            is_complete=True,
                            sources=search_results if request.include_sources else None,
                            generation_stats={
                                "total_time": generation_time,
                                "model_used": model_name,
                                "total_tokens": chunk.get("eval_count", 0),
                                "prompt_tokens": chunk.get("prompt_eval_count", 0)
                            }
                        )
                    break
            
        except Exception as e:
            logger.error(f"Error streaming chat message: {e}", exc_info=True)
            
            # Send error as final chunk
            import uuid
            error_message_id = str(uuid.uuid4())
            
            yield StreamingChatResponse(
                conversation_id=conversation.id if 'conversation' in locals() else "unknown",
                message_id=error_message_id,
                content_delta=f"I apologize, but I encountered an error: {str(e)}",
                is_complete=True
            )
    
    async def _retrieve_context(
        self,
        query: str,
        max_tokens: int = 4000
    ) -> List[SearchResult]:
        """Retrieve relevant context using semantic search."""
        try:
            # Perform semantic search
            from app.models.search import SearchQuery
            search_query = SearchQuery(
                query=query,
                top_k=10,
                min_similarity=0.3  # Lower threshold for more context
            )
            search_results = await self.search_engine.semantic_search(search_query)
            
            # Filter and optimize results for context
            filtered_results = []
            total_tokens = 0
            
            for result in search_results.results:
                # Estimate tokens for this chunk
                chunk_tokens = len(result.chunk.content) // 4
                
                if total_tokens + chunk_tokens <= max_tokens:
                    filtered_results.append(result)
                    total_tokens += chunk_tokens
                else:
                    break
            
            return filtered_results
            
        except Exception as e:
            logger.warning(f"Error retrieving context: {e}")
            return []
    
    async def _generate_response(
        self,
        question: str,
        context: str,
        conversation_history: List[ChatMessage],
        model_name: str,
        system_prompt: Optional[str] = None
    ) -> tuple[str, Dict[str, Any]]:
        """Generate response using Ollama."""
        try:
            # Build prompt
            template = PromptTemplate.RAG_CONVERSATIONAL if conversation_history else PromptTemplate.RAG_BASIC
            
            prompt = self.prompt_builder.build_rag_prompt(
                question=question,
                context=context,
                template=template,
                conversation_history=conversation_history
            )
            
            # Prepare messages for chat format
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({
                    "role": "system", 
                    "content": self.prompt_builder.get_system_prompt()
                })
            
            # Add conversation history
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                messages.append({
                    "role": "user" if msg.role == MessageRole.USER else "assistant",
                    "content": msg.content
                })
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            # Generate response
            full_response = ""
            generation_stats = {}
            
            async with self.ollama_client:
                async for chunk in self.ollama_client.chat(
                    model=model_name,
                    messages=messages,
                    stream=False
                ):
                    if chunk.get("message", {}).get("content"):
                        full_response += chunk["message"]["content"]
                    
                    if chunk.get("done"):
                        generation_stats = {
                            "total_tokens": chunk.get("eval_count", 0),
                            "prompt_tokens": chunk.get("prompt_eval_count", 0),
                            "eval_duration": chunk.get("eval_duration", 0),
                            "prompt_eval_duration": chunk.get("prompt_eval_duration", 0)
                        }
                        break
            
            return full_response.strip(), generation_stats
            
        except OllamaModelError as e:
            raise ChatContextError(f"Model error: {e.message}", e.details)
        except OllamaConnectionError as e:
            raise ChatContextError(f"Connection error: {e.message}", e.details)
        except Exception as e:
            raise ChatContextError(f"Generation error: {str(e)}")
    
    async def _stream_response(
        self,
        question: str,
        context: str,
        conversation_history: List[ChatMessage],
        model_name: str,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response using Ollama."""
        try:
            # Build prompt (same as _generate_response)
            template = PromptTemplate.RAG_CONVERSATIONAL if conversation_history else PromptTemplate.RAG_BASIC
            
            prompt = self.prompt_builder.build_rag_prompt(
                question=question,
                context=context,
                template=template,
                conversation_history=conversation_history
            )
            
            # Prepare messages
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({
                    "role": "system", 
                    "content": self.prompt_builder.get_system_prompt()
                })
            
            for msg in conversation_history[-5:]:
                messages.append({
                    "role": "user" if msg.role == MessageRole.USER else "assistant",
                    "content": msg.content
                })
            
            messages.append({"role": "user", "content": prompt})
            
            # Stream response
            async with self.ollama_client:
                async for chunk in self.ollama_client.chat(
                    model=model_name,
                    messages=messages,
                    stream=True
                ):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            raise
    
    def _generate_conversation_title(self, first_message: str) -> str:
        """Generate a conversation title from the first message."""
        # Simple title generation - take first few words
        words = first_message.strip().split()[:6]
        title = " ".join(words)
        
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title or f"Chat {datetime.now().strftime('%H:%M')}"
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available Ollama models."""
        try:
            async with self.ollama_client:
                models = await self.ollama_client.list_models()
                return [model.to_dict() for model in models]
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    async def validate_model(self, model_name: str) -> Dict[str, Any]:
        """Validate if a model is available and working."""
        try:
            async with self.ollama_client:
                return await self.ollama_client.validate_model(model_name)
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "available": False
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of chat engine components."""
        health_status = {
            "ollama": False,
            "search_engine": False,
            "conversation_manager": True,  # Always available (file-based)
            "overall": False
        }
        
        # Check Ollama
        try:
            async with self.ollama_client:
                health_status["ollama"] = await self.ollama_client.health_check()
        except Exception:
            pass
        
        # Check search engine
        try:
            # Simple test search
            # Simple test search with proper SearchQuery
            from app.models.search import SearchQuery
            test_query = SearchQuery(query="test", top_k=1)
            await self.search_engine.semantic_search(test_query)
            health_status["search_engine"] = True
        except Exception:
            pass
        
        health_status["overall"] = all([
            health_status["ollama"],
            health_status["search_engine"],
            health_status["conversation_manager"]
        ])
        
        return health_status