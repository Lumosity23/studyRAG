"""Tests for prompt templates and prompt builder."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from app.services.prompt_templates import (
    PromptBuilder, PromptTemplate, get_prompt_builder
)
from app.models.chat import ChatMessage, MessageRole


@pytest.fixture
def prompt_builder():
    """Create prompt builder for testing."""
    return PromptBuilder()


@pytest.fixture
def sample_messages():
    """Create sample chat messages for testing."""
    return [
        ChatMessage(
            id="1",
            conversation_id="conv1",
            content="What is machine learning?",
            role=MessageRole.USER,
            created_at=datetime(2024, 1, 1, 10, 0)
        ),
        ChatMessage(
            id="2",
            conversation_id="conv1",
            content="Machine learning is a subset of artificial intelligence...",
            role=MessageRole.ASSISTANT,
            created_at=datetime(2024, 1, 1, 10, 1)
        ),
        ChatMessage(
            id="3",
            conversation_id="conv1",
            content="Can you give me an example?",
            role=MessageRole.USER,
            created_at=datetime(2024, 1, 1, 10, 2)
        )
    ]


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    from app.models.search import SearchResult
    from app.models.chunk import Chunk
    from app.models.document import Document, DocumentType
    
    # Create mock objects
    doc = MagicMock(spec=Document)
    doc.filename = "ml_guide.pdf"
    doc.document_type = DocumentType.PDF
    
    chunk1 = MagicMock(spec=Chunk)
    chunk1.content = "Machine learning is a method of data analysis that automates analytical model building."
    chunk1.chunk_index = 1
    
    chunk2 = MagicMock(spec=Chunk)
    chunk2.content = "Supervised learning uses labeled training data to learn a mapping function."
    chunk2.chunk_index = 2
    
    result1 = MagicMock(spec=SearchResult)
    result1.chunk = chunk1
    result1.document = doc
    result1.similarity_score = 0.85
    
    result2 = MagicMock(spec=SearchResult)
    result2.chunk = chunk2
    result2.document = doc
    result2.similarity_score = 0.78
    
    return [result1, result2]


class TestPromptBuilder:
    """Test PromptBuilder class."""
    
    def test_initialization(self, prompt_builder):
        """Test prompt builder initialization."""
        assert prompt_builder is not None
        assert len(prompt_builder.templates) > 0
        assert PromptTemplate.SYSTEM_DEFAULT in prompt_builder.templates
        assert PromptTemplate.RAG_BASIC in prompt_builder.templates
    
    def test_get_system_prompt_default(self, prompt_builder):
        """Test getting default system prompt."""
        system_prompt = prompt_builder.get_system_prompt()
        
        assert "StudyRAG" in system_prompt
        assert "assistant" in system_prompt.lower()
        assert "documents" in system_prompt.lower()
    
    def test_get_system_prompt_specific_template(self, prompt_builder):
        """Test getting specific system prompt template."""
        system_prompt = prompt_builder.get_system_prompt(PromptTemplate.SYSTEM_DEFAULT)
        
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
    
    def test_build_rag_prompt_basic(self, prompt_builder):
        """Test building basic RAG prompt."""
        question = "What is machine learning?"
        context = "Machine learning is a subset of AI that enables computers to learn."
        
        prompt = prompt_builder.build_rag_prompt(
            question=question,
            context=context,
            template=PromptTemplate.RAG_BASIC
        )
        
        assert question in prompt
        assert context in prompt
        assert "Context:" in prompt or "context" in prompt.lower()
        assert "Question:" in prompt or "question" in prompt.lower()
    
    def test_build_rag_prompt_detailed(self, prompt_builder):
        """Test building detailed RAG prompt."""
        question = "Explain neural networks"
        context = "Neural networks are computing systems inspired by biological neural networks."
        
        prompt = prompt_builder.build_rag_prompt(
            question=question,
            context=context,
            template=PromptTemplate.RAG_DETAILED
        )
        
        assert question in prompt
        assert context in prompt
        assert "comprehensive" in prompt.lower() or "detailed" in prompt.lower()
    
    def test_build_rag_prompt_conversational(self, prompt_builder, sample_messages):
        """Test building conversational RAG prompt."""
        question = "Can you elaborate on that?"
        context = "Deep learning uses neural networks with multiple layers."
        
        prompt = prompt_builder.build_rag_prompt(
            question=question,
            context=context,
            template=PromptTemplate.RAG_CONVERSATIONAL,
            conversation_history=sample_messages
        )
        
        assert question in prompt
        assert context in prompt
        assert "conversation" in prompt.lower()
        # Should include some history
        assert "machine learning" in prompt.lower()
    
    def test_build_rag_prompt_with_additional_context(self, prompt_builder):
        """Test building prompt with additional context variables."""
        question = "What is AI?"
        context = "AI is artificial intelligence."
        additional_context = {"user_name": "John", "topic": "AI basics"}
        
        # Add a custom template that uses additional variables
        custom_template = "User {user_name} asked about {topic}:\nContext: {context}\nQuestion: {question}"
        prompt_builder.add_custom_template("custom", custom_template)
        
        prompt = prompt_builder.build_rag_prompt(
            question=question,
            context=context,
            template="custom",
            additional_context=additional_context
        )
        
        assert "John" in prompt
        assert "AI basics" in prompt
        assert question in prompt
        assert context in prompt
    
    def test_build_rag_prompt_fallback(self, prompt_builder):
        """Test prompt building fallback to basic template."""
        question = "Test question"
        context = "Test context"
        
        # Use invalid template
        prompt = prompt_builder.build_rag_prompt(
            question=question,
            context=context,
            template="invalid_template"
        )
        
        # Should fallback to basic template
        assert question in prompt
        assert context in prompt
    
    def test_format_conversation_history(self, prompt_builder, sample_messages):
        """Test conversation history formatting."""
        history_text = prompt_builder._format_conversation_history(sample_messages)
        
        assert "User:" in history_text
        assert "Assistant:" in history_text
        assert "machine learning" in history_text.lower()
        assert "example" in history_text.lower()
    
    def test_format_conversation_history_empty(self, prompt_builder):
        """Test formatting empty conversation history."""
        history_text = prompt_builder._format_conversation_history([])
        
        assert "No previous conversation" in history_text
    
    def test_format_conversation_history_limit(self, prompt_builder):
        """Test conversation history limiting."""
        # Create more than 10 messages
        messages = []
        for i in range(15):
            messages.append(ChatMessage(
                id=str(i),
                conversation_id="conv1",
                content=f"Message {i}",
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                created_at=datetime(2024, 1, 1, 10, i)
            ))
        
        history_text = prompt_builder._format_conversation_history(messages)
        
        # Should only include last 10 messages
        lines = [line for line in history_text.split('\n') if line.strip()]
        assert len(lines) <= 10
        
        # Should include the most recent messages
        assert "Message 14" in history_text
        assert "Message 5" in history_text
        assert "Message 4" not in history_text  # Should be excluded
    
    def test_build_context_from_sources(self, prompt_builder, sample_search_results):
        """Test building context from search results."""
        context = prompt_builder.build_context_from_sources(
            sample_search_results,
            max_tokens=1000,
            include_metadata=True
        )
        
        assert "Machine learning is a method" in context
        assert "Supervised learning uses" in context
        assert "ml_guide.pdf" in context  # Metadata should be included
        assert "Section 1" in context or "Section 2" in context
    
    def test_build_context_from_sources_no_metadata(self, prompt_builder, sample_search_results):
        """Test building context without metadata."""
        context = prompt_builder.build_context_from_sources(
            sample_search_results,
            max_tokens=1000,
            include_metadata=False
        )
        
        assert "Machine learning is a method" in context
        assert "Supervised learning uses" in context
        assert "ml_guide.pdf" not in context  # Metadata should not be included
    
    def test_build_context_from_sources_empty(self, prompt_builder):
        """Test building context from empty search results."""
        context = prompt_builder.build_context_from_sources([])
        
        assert "No relevant documents found" in context
    
    def test_build_context_from_sources_token_limit(self, prompt_builder, sample_search_results):
        """Test context building with token limits."""
        # Set very low token limit
        context = prompt_builder.build_context_from_sources(
            sample_search_results,
            max_tokens=10,  # Very low limit
            include_metadata=True
        )
        
        # Should include at least some content or indicate limitation
        assert len(context) > 0
    
    def test_optimize_prompt_length_no_change(self, prompt_builder):
        """Test prompt optimization when no change needed."""
        short_prompt = "This is a short prompt that doesn't need optimization."
        
        optimized = prompt_builder.optimize_prompt_length(short_prompt, max_tokens=1000)
        
        assert optimized == short_prompt
    
    def test_optimize_prompt_length_truncation(self, prompt_builder):
        """Test prompt optimization with truncation."""
        # Create a long prompt
        long_context = "This is a very long context. " * 100
        long_prompt = f"Context:\n{long_context}\n\nQuestion: What is this about?"
        
        optimized = prompt_builder.optimize_prompt_length(long_prompt, max_tokens=100)
        
        # Should be shorter than original
        assert len(optimized) < len(long_prompt)
        # Should still contain the question
        assert "Question:" in optimized
        assert "What is this about?" in optimized
    
    def test_add_custom_template(self, prompt_builder):
        """Test adding custom template."""
        custom_template = "Custom template: {question} - {context}"
        
        prompt_builder.add_custom_template("my_template", custom_template)
        
        assert "my_template" in prompt_builder.templates
        assert prompt_builder.templates["my_template"] == custom_template
    
    def test_get_template_info(self, prompt_builder):
        """Test getting template information."""
        template_info = prompt_builder.get_template_info()
        
        assert isinstance(template_info, dict)
        assert PromptTemplate.RAG_BASIC.value in template_info
        assert PromptTemplate.RAG_DETAILED.value in template_info
        
        # Check structure of template info
        basic_info = template_info[PromptTemplate.RAG_BASIC.value]
        assert "name" in basic_info
        assert "description" in basic_info
        assert "variables" in basic_info
        assert isinstance(basic_info["variables"], list)
    
    def test_extract_template_variables(self, prompt_builder):
        """Test extracting variables from template."""
        template = "Hello {name}, your {item} is ready. Context: {context}"
        
        variables = prompt_builder._extract_template_variables(template)
        
        assert "name" in variables
        assert "item" in variables
        assert "context" in variables
        assert len(variables) == 3
    
    def test_get_template_description(self, prompt_builder):
        """Test getting template descriptions."""
        desc = prompt_builder._get_template_description(PromptTemplate.RAG_BASIC)
        assert isinstance(desc, str)
        assert len(desc) > 0
        
        desc = prompt_builder._get_template_description(PromptTemplate.RAG_DETAILED)
        assert isinstance(desc, str)
        assert len(desc) > 0


class TestGlobalPromptBuilder:
    """Test global prompt builder functions."""
    
    def test_get_prompt_builder(self):
        """Test getting global prompt builder instance."""
        builder1 = get_prompt_builder()
        builder2 = get_prompt_builder()
        
        # Should return the same instance
        assert builder1 is builder2
        assert isinstance(builder1, PromptBuilder)
    
    def test_global_builder_functionality(self):
        """Test that global builder works correctly."""
        builder = get_prompt_builder()
        
        # Test basic functionality
        prompt = builder.build_rag_prompt(
            question="Test question",
            context="Test context"
        )
        
        assert "Test question" in prompt
        assert "Test context" in prompt