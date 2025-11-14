"""Prompt engineering system with templates for RAG responses."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from app.models.chat import ChatMessage, MessageRole


class PromptTemplate(str, Enum):
    """Available prompt templates."""
    
    RAG_BASIC = "rag_basic"
    RAG_DETAILED = "rag_detailed"
    RAG_CONVERSATIONAL = "rag_conversational"
    RAG_ANALYTICAL = "rag_analytical"
    RAG_CREATIVE = "rag_creative"
    SYSTEM_DEFAULT = "system_default"


class PromptBuilder:
    """Builder for constructing prompts with templates and context."""
    
    def __init__(self):
        """Initialize prompt builder with templates."""
        self.templates = {
            PromptTemplate.SYSTEM_DEFAULT: """You are StudyRAG, an intelligent assistant specialized in helping users understand and analyze documents. You have access to a knowledge base of documents and can provide accurate, contextual responses based on the available information.

Key guidelines:
- Always base your responses on the provided context from the documents
- If information is not available in the context, clearly state this limitation
- Provide specific citations and references when possible
- Be concise but comprehensive in your explanations
- Maintain a helpful and professional tone
- If asked about topics outside the document context, politely redirect to document-related queries""",

            PromptTemplate.RAG_BASIC: """Based on the following context from the documents, please answer the user's question:

Context:
{context}

Question: {question}

Please provide a clear and accurate answer based on the context above. If the context doesn't contain enough information to fully answer the question, please indicate what information is missing.""",

            PromptTemplate.RAG_DETAILED: """You are analyzing documents to answer a user's question. Here is the relevant context:

DOCUMENT CONTEXT:
{context}

USER QUESTION: {question}

Please provide a comprehensive answer that:
1. Directly addresses the user's question
2. References specific information from the context
3. Explains any relevant connections or implications
4. Indicates if additional information would be helpful
5. Cites the source documents when possible

Answer:""",

            PromptTemplate.RAG_CONVERSATIONAL: """Continue this conversation by answering the user's latest question using the provided document context.

CONVERSATION HISTORY:
{conversation_history}

RELEVANT CONTEXT FROM DOCUMENTS:
{context}

LATEST QUESTION: {question}

Please respond naturally as part of the ongoing conversation, incorporating the document context to provide an accurate and helpful answer.""",

            PromptTemplate.RAG_ANALYTICAL: """Analyze the following documents to provide an in-depth response to the user's question.

DOCUMENT CONTEXT:
{context}

ANALYSIS REQUEST: {question}

Please provide:
1. A thorough analysis based on the available information
2. Key insights and patterns from the documents
3. Any limitations in the available data
4. Recommendations or next steps if applicable
5. Specific references to support your analysis

Analysis:""",

            PromptTemplate.RAG_CREATIVE: """Using the document context as a foundation, provide a creative and engaging response to the user's question.

CONTEXT FROM DOCUMENTS:
{context}

CREATIVE PROMPT: {question}

Please craft a response that:
- Stays grounded in the factual information from the documents
- Presents the information in an engaging and accessible way
- Uses examples, analogies, or storytelling when appropriate
- Maintains accuracy while being creative in presentation

Response:"""
        }
    
    def get_system_prompt(self, template: PromptTemplate = PromptTemplate.SYSTEM_DEFAULT) -> str:
        """Get system prompt for the conversation."""
        if template == PromptTemplate.SYSTEM_DEFAULT:
            return self.templates[PromptTemplate.SYSTEM_DEFAULT]
        return self.templates.get(template, self.templates[PromptTemplate.SYSTEM_DEFAULT])
    
    def build_rag_prompt(
        self,
        question: str,
        context: str,
        template: PromptTemplate = PromptTemplate.RAG_BASIC,
        conversation_history: Optional[List[ChatMessage]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a RAG prompt using the specified template."""
        
        if template not in self.templates:
            template = PromptTemplate.RAG_BASIC
        
        prompt_template = self.templates[template]
        
        # Prepare template variables
        template_vars = {
            "question": question.strip(),
            "context": context.strip()
        }
        
        # Add conversation history if needed
        if conversation_history and "{conversation_history}" in prompt_template:
            history_text = self._format_conversation_history(conversation_history)
            template_vars["conversation_history"] = history_text
        
        # Add any additional context
        if additional_context:
            template_vars.update(additional_context)
        
        try:
            return prompt_template.format(**template_vars)
        except KeyError as e:
            # Fallback to basic template if formatting fails
            return self.templates[PromptTemplate.RAG_BASIC].format(
                question=question,
                context=context
            )
    
    def _format_conversation_history(self, messages: List[ChatMessage]) -> str:
        """Format conversation history for inclusion in prompts."""
        if not messages:
            return "No previous conversation."
        
        formatted_messages = []
        for msg in messages[-10:]:  # Limit to last 10 messages
            role_label = "User" if msg.role == MessageRole.USER else "Assistant"
            timestamp = msg.created_at.strftime("%H:%M")
            formatted_messages.append(f"[{timestamp}] {role_label}: {msg.content}")
        
        return "\n".join(formatted_messages)
    
    def build_context_from_sources(
        self,
        search_results: List[Any],
        max_tokens: int = 4000,
        include_metadata: bool = True
    ) -> str:
        """Build context string from search results."""
        if not search_results:
            return "No relevant documents found."
        
        context_parts = []
        current_tokens = 0
        
        for i, result in enumerate(search_results):
            # Estimate tokens (rough approximation)
            chunk_content = result.chunk.content
            metadata_text = ""
            
            if include_metadata:
                doc_name = result.document.filename
                chunk_idx = getattr(result.chunk, 'chunk_index', i + 1)
                metadata_text = f"[Source: {doc_name}, Section {chunk_idx}]\n"
            
            full_text = metadata_text + chunk_content
            estimated_tokens = len(full_text) // 4  # Rough estimate
            
            if current_tokens + estimated_tokens > max_tokens:
                break
            
            context_parts.append(full_text)
            current_tokens += estimated_tokens
        
        if not context_parts:
            return "Context too large to include."
        
        return "\n\n---\n\n".join(context_parts)
    
    def optimize_prompt_length(
        self,
        prompt: str,
        max_tokens: int = 8000,
        preserve_question: bool = True
    ) -> str:
        """Optimize prompt length to fit within token limits."""
        estimated_tokens = len(prompt) // 4
        
        if estimated_tokens <= max_tokens:
            return prompt
        
        # If prompt is too long, try to truncate context while preserving structure
        lines = prompt.split('\n')
        
        # Find context section
        context_start = -1
        context_end = -1
        
        for i, line in enumerate(lines):
            if 'context' in line.lower() and ':' in line:
                context_start = i + 1
            elif context_start != -1 and line.strip() and not line.startswith(' '):
                context_end = i
                break
        
        if context_start != -1:
            # Truncate context section
            context_lines = lines[context_start:context_end] if context_end != -1 else lines[context_start:]
            
            # Keep first and last parts, truncate middle
            target_context_tokens = max_tokens - (len('\n'.join(lines[:context_start] + lines[context_end:])) // 4)
            
            if len(context_lines) > 10:
                # Keep first 5 and last 5 lines of context
                truncated_context = (
                    context_lines[:5] + 
                    ["\n[... content truncated for length ...]\n"] + 
                    context_lines[-5:]
                )
                
                lines[context_start:context_end] = truncated_context
        
        return '\n'.join(lines)
    
    def add_custom_template(self, name: str, template: str) -> None:
        """Add a custom prompt template."""
        self.templates[name] = template
    
    def get_template_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available templates."""
        return {
            template.value: {
                "name": template.value,
                "description": self._get_template_description(template),
                "variables": self._extract_template_variables(self.templates[template])
            }
            for template in PromptTemplate
        }
    
    def _get_template_description(self, template: PromptTemplate) -> str:
        """Get description for a template."""
        descriptions = {
            PromptTemplate.RAG_BASIC: "Simple, direct RAG responses",
            PromptTemplate.RAG_DETAILED: "Comprehensive analysis with structured output",
            PromptTemplate.RAG_CONVERSATIONAL: "Natural conversation flow with context",
            PromptTemplate.RAG_ANALYTICAL: "In-depth analysis and insights",
            PromptTemplate.RAG_CREATIVE: "Creative and engaging presentation",
            PromptTemplate.SYSTEM_DEFAULT: "Default system instructions"
        }
        return descriptions.get(template, "Custom template")
    
    def _extract_template_variables(self, template: str) -> List[str]:
        """Extract variables from a template string."""
        import re
        variables = re.findall(r'\{(\w+)\}', template)
        return list(set(variables))


# Global prompt builder instance
prompt_builder = PromptBuilder()


def get_prompt_builder() -> PromptBuilder:
    """Get the global prompt builder instance."""
    return prompt_builder