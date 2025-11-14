"""Search-related data models."""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import Field, field_validator, model_validator
from datetime import datetime

from .common import BaseModel, TimestampMixin
from .chunk import Chunk
from .document import Document


class SearchType(str, Enum):
    """Types of search operations."""
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    LEXICAL = "lexical"


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class SearchQuery(BaseModel):
    """Model for search query parameters."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query text"
    )
    
    search_type: SearchType = Field(
        default=SearchType.SEMANTIC,
        description="Type of search to perform"
    )
    
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    
    min_similarity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for results"
    )
    
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional filters to apply"
    )
    
    document_ids: Optional[List[str]] = Field(
        None,
        description="Limit search to specific documents"
    )
    
    document_types: Optional[List[str]] = Field(
        None,
        description="Limit search to specific document types"
    )
    
    languages: Optional[List[str]] = Field(
        None,
        description="Limit search to specific languages"
    )
    
    date_from: Optional[datetime] = Field(
        None,
        description="Search documents created after this date"
    )
    
    date_to: Optional[datetime] = Field(
        None,
        description="Search documents created before this date"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="Whether to include metadata in results"
    )
    
    highlight: bool = Field(
        default=True,
        description="Whether to highlight matching text in results"
    )
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        """Validate search query."""
        if not v or v.isspace():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()
    
    @model_validator(mode="after")
    def validate_date_range(self):
        """Validate date range."""
        if self.date_to and self.date_from:
            if self.date_to <= self.date_from:
                raise ValueError("date_to must be after date_from")
        return self


class SearchResult(BaseModel):
    """Model for individual search result."""
    
    chunk: Chunk = Field(..., description="The matching chunk")
    document: Document = Field(..., description="The parent document")
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score between query and chunk"
    )
    highlighted_content: Optional[str] = Field(
        None,
        description="Content with highlighted matching terms"
    )
    context_before: Optional[str] = Field(
        None,
        description="Text context before the matching chunk"
    )
    context_after: Optional[str] = Field(
        None,
        description="Text context after the matching chunk"
    )
    rank: Optional[int] = Field(
        None,
        ge=1,
        description="Rank of this result in the search results"
    )
    
    @property
    def relevance_category(self) -> str:
        """Categorize relevance based on similarity score."""
        if self.similarity_score >= 0.9:
            return "very_high"
        elif self.similarity_score >= 0.8:
            return "high"
        elif self.similarity_score >= 0.7:
            return "medium"
        elif self.similarity_score >= 0.6:
            return "low"
        else:
            return "very_low"
    
    def to_summary(self) -> Dict[str, Any]:
        """Get a summary representation of the search result."""
        return {
            "chunk_id": self.chunk.id,
            "document_id": self.document.id,
            "document_filename": self.document.filename,
            "similarity_score": self.similarity_score,
            "relevance_category": self.relevance_category,
            "content_preview": self.chunk.get_preview(150),
            "section_title": self.chunk.section_title,
            "page_number": self.chunk.page_number,
            "rank": self.rank
        }


class SearchResponse(TimestampMixin):
    """Model for search response."""
    
    query: str = Field(..., description="Original search query")
    search_type: SearchType = Field(..., description="Type of search performed")
    results: List[SearchResult] = Field(..., description="List of search results")
    total_results: int = Field(..., description="Total number of results found")
    search_time: float = Field(..., description="Search execution time in seconds")
    filters_applied: Optional[Dict[str, Any]] = Field(
        None,
        description="Filters that were applied to the search"
    )
    
    @property
    def has_results(self) -> bool:
        """Check if search returned any results."""
        return len(self.results) > 0
    
    @property
    def avg_similarity(self) -> float:
        """Calculate average similarity score of results."""
        if not self.results:
            return 0.0
        return sum(result.similarity_score for result in self.results) / len(self.results)
    
    @property
    def top_similarity(self) -> float:
        """Get the highest similarity score."""
        if not self.results:
            return 0.0
        return max(result.similarity_score for result in self.results)


class SearchSuggestion(BaseModel):
    """Model for search suggestions."""
    
    suggestion: str = Field(..., description="Suggested search term")
    frequency: int = Field(..., ge=0, description="Frequency of this term in documents")
    category: Optional[str] = Field(None, description="Category of the suggestion")
    
    
class SearchSuggestionsResponse(BaseModel):
    """Response model for search suggestions."""
    
    query: str = Field(..., description="Original query for suggestions")
    suggestions: List[SearchSuggestion] = Field(..., description="List of suggestions")
    total_suggestions: int = Field(..., description="Total number of suggestions")


class SearchStats(BaseModel):
    """Model for search statistics."""
    
    total_searches: int = Field(..., description="Total number of searches performed")
    avg_search_time: float = Field(..., description="Average search time in seconds")
    avg_results_per_search: float = Field(..., description="Average number of results per search")
    most_common_queries: List[Dict[str, Any]] = Field(
        ...,
        description="Most frequently searched queries"
    )
    search_types_distribution: Dict[str, int] = Field(
        ...,
        description="Distribution of search types used"
    )
    
    
class ContextRetrievalRequest(BaseModel):
    """Request model for retrieving context for RAG."""
    
    query: str = Field(..., min_length=1, description="Query to find context for")
    max_tokens: int = Field(
        default=4000,
        ge=100,
        le=8000,
        description="Maximum number of tokens in the context"
    )
    max_chunks: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of chunks to include"
    )
    min_similarity: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for chunks"
    )
    document_ids: Optional[List[str]] = Field(
        None,
        description="Limit context to specific documents"
    )
    
    
class ContextRetrievalResponse(BaseModel):
    """Response model for context retrieval."""
    
    context: str = Field(..., description="Retrieved context text")
    chunks_used: List[SearchResult] = Field(..., description="Chunks included in context")
    total_tokens: int = Field(..., description="Estimated total tokens in context")
    retrieval_time: float = Field(..., description="Time taken to retrieve context")
    truncated: bool = Field(..., description="Whether context was truncated due to token limit")