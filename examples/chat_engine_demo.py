"""Demo script for the chat engine functionality."""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.chat_engine import ChatEngine
from app.services.ollama_client import OllamaClient
from app.services.conversation_manager import ConversationManager
from app.services.prompt_templates import PromptBuilder
from app.models.chat import ChatRequest, ConversationCreateRequest
from app.core.config import get_settings


class MockSearchEngine:
    """Mock search engine for demo purposes."""
    
    async def semantic_search(self, query: str, top_k: int = 10, min_similarity: float = 0.3):
        """Mock semantic search that returns sample results."""
        from unittest.mock import MagicMock
        from app.models.search import SearchResult
        from app.models.chunk import Chunk
        from app.models.document import Document
        
        # Create mock search results based on query
        mock_chunk = MagicMock(spec=Chunk)
        mock_document = MagicMock(spec=Document)
        mock_result = MagicMock(spec=SearchResult)
        
        if "machine learning" in query.lower():
            mock_chunk.content = "Machine learning is a subset of artificial intelligence (AI) that enables computers to learn and improve from experience without being explicitly programmed."
            mock_document.filename = "ml_fundamentals.pdf"
        elif "python" in query.lower():
            mock_chunk.content = "Python is a high-level, interpreted programming language known for its simplicity and readability. It's widely used in data science, web development, and AI."
            mock_document.filename = "python_guide.pdf"
        else:
            mock_chunk.content = f"This is relevant information about: {query}"
            mock_document.filename = "general_knowledge.pdf"
        
        mock_chunk.id = "chunk1"
        mock_document.id = "doc1"
        
        mock_result.chunk = mock_chunk
        mock_result.document = mock_document
        mock_result.similarity_score = 0.85
        
        # Return mock search response
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        return mock_response


async def demo_chat_engine():
    """Demonstrate chat engine functionality."""
    print("🤖 StudyRAG Chat Engine Demo")
    print("=" * 50)
    
    # Initialize settings
    settings = get_settings()
    
    # Create components
    print("📚 Initializing chat engine components...")
    
    # Use mock search engine for demo
    search_engine = MockSearchEngine()
    
    # Create real components
    conversation_manager = ConversationManager(settings)
    prompt_builder = PromptBuilder()
    
    # Note: OllamaClient would need a real Ollama server running
    # For demo purposes, we'll mock it
    class MockOllamaClient:
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        
        async def chat(self, model: str, messages: list, stream: bool = False):
            # Mock response based on the last user message
            last_message = messages[-1]["content"] if messages else ""
            
            if "machine learning" in last_message.lower():
                response = "Machine learning is indeed a fascinating field! Based on the documents, it's a subset of AI that allows computers to learn from data without explicit programming. It has applications in many areas like image recognition, natural language processing, and predictive analytics."
            elif "python" in last_message.lower():
                response = "Python is an excellent choice for programming! According to the documentation, it's known for its simplicity and readability. It's particularly popular in data science and AI development due to its extensive libraries like NumPy, Pandas, and TensorFlow."
            else:
                response = f"That's an interesting question about '{last_message}'. Based on the available documents, I can provide some relevant information, though you might want to ask more specific questions for detailed answers."
            
            yield {
                "message": {"content": response},
                "done": True,
                "eval_count": len(response.split()),
                "prompt_eval_count": len(last_message.split()) if last_message else 0
            }
    
    ollama_client = MockOllamaClient()
    
    # Create chat engine
    chat_engine = ChatEngine(
        search_engine=search_engine,
        ollama_client=ollama_client,
        conversation_manager=conversation_manager,
        prompt_builder=prompt_builder,
        settings=settings
    )
    
    print("✅ Chat engine initialized successfully!")
    print()
    
    # Demo 1: Create a new conversation
    print("🆕 Demo 1: Creating a new conversation")
    print("-" * 30)
    
    request1 = ChatRequest(
        message="What is machine learning and how does it work?",
        conversation_id=None,
        include_sources=True
    )
    
    print(f"User: {request1.message}")
    
    try:
        response1 = await chat_engine.process_message(request1)
        print(f"Assistant: {response1.message.content}")
        print(f"📊 Sources used: {len(response1.sources_used) if response1.sources_used else 0}")
        print(f"💬 Conversation ID: {response1.conversation.id}")
        print(f"📝 Message count: {response1.conversation.message_count}")
        print()
        
        conversation_id = response1.conversation.id
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Demo 2: Continue the conversation
    print("🔄 Demo 2: Continuing the conversation")
    print("-" * 30)
    
    request2 = ChatRequest(
        message="Can you give me an example of machine learning in Python?",
        conversation_id=conversation_id,
        include_sources=True
    )
    
    print(f"User: {request2.message}")
    
    try:
        response2 = await chat_engine.process_message(request2)
        print(f"Assistant: {response2.message.content}")
        print(f"📊 Sources used: {len(response2.sources_used) if response2.sources_used else 0}")
        print(f"📝 Total messages in conversation: {response2.conversation.message_count}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Demo 3: Show conversation history
    print("📜 Demo 3: Conversation history")
    print("-" * 30)
    
    try:
        messages_response = await conversation_manager.get_messages(conversation_id)
        
        print(f"Conversation: {messages_response.conversation.title}")
        print(f"Total messages: {messages_response.total_messages}")
        print()
        
        for i, msg in enumerate(messages_response.messages, 1):
            role_emoji = "👤" if msg.role == "user" else "🤖"
            print(f"{i}. {role_emoji} {msg.role.title()}: {msg.get_content_preview(80)}")
            if msg.sources and len(msg.sources) > 0:
                print(f"   📚 Sources: {msg.sources[0].document.filename}")
        print()
        
    except Exception as e:
        print(f"❌ Error getting conversation history: {e}")
    
    # Demo 4: Show prompt building
    print("🔧 Demo 4: Prompt building demonstration")
    print("-" * 30)
    
    try:
        # Get conversation history
        history = await conversation_manager.get_conversation_history(conversation_id, max_messages=5)
        
        # Build a sample prompt
        sample_prompt = prompt_builder.build_rag_prompt(
            question="What are the main types of machine learning?",
            context="Machine learning can be categorized into supervised learning, unsupervised learning, and reinforcement learning.",
            conversation_history=history
        )
        
        print("Sample RAG prompt structure:")
        print("```")
        print(sample_prompt[:500] + "..." if len(sample_prompt) > 500 else sample_prompt)
        print("```")
        print()
        
    except Exception as e:
        print(f"❌ Error building prompt: {e}")
    
    # Demo 5: Available templates
    print("📋 Demo 5: Available prompt templates")
    print("-" * 30)
    
    try:
        template_info = prompt_builder.get_template_info()
        
        for template_name, info in template_info.items():
            print(f"• {template_name}: {info['description']}")
        print()
        
    except Exception as e:
        print(f"❌ Error getting template info: {e}")
    
    # Demo 6: Conversation statistics
    print("📈 Demo 6: Conversation statistics")
    print("-" * 30)
    
    try:
        stats = await conversation_manager.get_conversation_stats()
        
        print(f"Total conversations: {stats['total_conversations']}")
        print(f"Active conversations: {stats['active_conversations']}")
        print(f"Total messages: {stats['total_messages']}")
        print(f"Average messages per conversation: {stats['avg_messages_per_conversation']}")
        print()
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
    
    print("🎉 Demo completed successfully!")
    print()
    print("💡 Next steps:")
    print("- Connect to a real Ollama server for actual LLM responses")
    print("- Integrate with the search engine for real document retrieval")
    print("- Add the chat engine to FastAPI endpoints")
    print("- Implement WebSocket support for real-time streaming")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_chat_engine())