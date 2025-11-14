"""Chunk-related data models."""

from typing import Dict, Any, Optional, List
from pydantic import Field, field_validator, model_validator
from datetime import datetime

from .common import BaseModel, TimestampMixin, IDMixin, MetadataMixin


class Chunk(IDMixin, TimestampMixin, MetadataMixin):
    """Chunk model representing a piece of text from a document."""
    
    document_id: str = Field(
        ...,
        description="ID of the parent document"
    )
    
    content: str = Field(
        ...,
        min_length=1,
        description="Text content of the chunk"
    )
    
    start_index: int = Field(
        ...,
        ge=0,
        description="Starting character position in the original document"
    )
    
    end_index: int = Field(
        ...,
        ge=0,
        description="Ending character position in the original document"
    )
    
    chunk_index: int = Field(
        ...,
        ge=0,
        description="Sequential index of this chunk within the document"
    )
    
    embedding_vector: Optional[List[float]] = Field(
        None,
        description="Embedding vector for this chunk"
    )
    
    embedding_model: Optional[str] = Field(
        None,
        description="Name of the embedding model used"
    )
    
    token_count: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated token count of the content"
    )
    
    section_title: Optional[str] = Field(
        None,
        description="Title of the section this chunk belongs to"
    )
    
    page_number: Optional[int] = Field(
        None,
        ge=1,
        description="Page number where this chunk appears (for PDFs)"
    )
    
    language: Optional[str] = Field(
        None,
        description="Detected language of the chunk content"
    )
    
    similarity_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Similarity score (used in search results)"
    )
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        """Validate content is not empty or whitespace only."""
        if not v or v.isspace():
            raise ValueError("Content cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator("embedding_vector")
    @classmethod
    def validate_embedding_vector(cls, v):
        """Validate embedding vector dimensions."""
        if v is not None:
            if not isinstance(v, list) or len(v) == 0:
                raise ValueError("Embedding vector must be a non-empty list")
            if not all(isinstance(x, (int, float)) for x in v):
                raise ValueError("Embedding vector must contain only numbers")
        return v
    
    @model_validator(mode="after")
    def validate_indices(self):
        """Validate that end_index is greater than start_index."""
        if self.end_index <= self.start_index:
            raise ValueError("end_index must be greater than start_index")
        return self
    
    @property
    def content_length(self) -> int:
        """Get the length of the content."""
        return len(self.content)
    
    @property
    def character_range(self) -> tuple:
        """Get the character range as a tuple."""
        return (self.start_index, self.end_index)
    
    @property
    def has_embedding(self) -> bool:
        """Check if chunk has an embedding vector."""
        return self.embedding_vector is not None and len(self.embedding_vector) > 0
    
    def get_preview(self, max_length: int = 200) -> str:
        """Get a preview of the chunk content."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
    
    def to_search_result_dict(self) -> Dict[str, Any]:
        """Convert chunk to search result dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "content_preview": self.get_preview(),
            "similarity_score": self.similarity_score,
            "chunk_index": self.chunk_index,
            "section_title": self.section_title,
            "page_number": self.page_number,
            "character_range": self.character_range,
            "metadata": self.metadata
        }


class ChunkCreateRequest(BaseModel):
    """Request model for creating a chunk."""
    
    document_id: str = Field(..., description="ID of the parent document")
    content: str = Field(..., min_length=1, description="Text content of the chunk")
    start_index: int = Field(..., ge=0, description="Starting character position")
    end_index: int = Field(..., ge=0, description="Ending character position")
    chunk_index: int = Field(..., ge=0, description="Sequential index within document")
    section_title: Optional[str] = Field(None, description="Section title")
    page_number: Optional[int] = Field(None, ge=1, description="Page number")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ChunkUpdateRequest(BaseModel):
    """Request model for updating a chunk."""
    
    content: Optional[str] = Field(None, min_length=1, description="Updated content")
    section_title: Optional[str] = Field(None, description="Updated section title")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class ChunkResponse(BaseModel):
    """Response model for chunk operations."""
    
    chunk: Chunk = Field(..., description="The chunk data")
    document_filename: Optional[str] = Field(None, description="Parent document filename")


class ChunkListResponse(BaseModel):
    """Response model for chunk listing."""
    
    chunks: List[Chunk] = Field(..., description="List of chunks")
    total: int = Field(..., description="Total number of chunks")
    document_id: Optional[str] = Field(None, description="Document ID filter applied")


class ChunkStatsResponse(BaseModel):
    """Response model for chunk statistics."""
    
    total_chunks: int = Field(..., description="Total number of chunks")
    avg_chunk_size: float = Field(..., description="Average chunk size in characters")
    total_tokens: Optional[int] = Field(None, description="Total estimated tokens")
    by_document: Dict[str, int] = Field(..., description="Chunk count by document")
    by_language: Dict[str, int] = Field(..., description="Chunk count by language")


class EmbeddingRequest(BaseModel):
    """Request model for generating embeddings."""
    
    chunk_ids: List[str] = Field(..., description="List of chunk IDs to generate embeddings for")
    model_name: str = Field(..., description="Name of the embedding model to use")
    batch_size: Optional[int] = Field(32, ge=1, le=100, description="Batch size for processing")


class EmbeddingResponse(BaseModel):
    """Response model for embedding generation."""
    
    success_count: int = Field(..., description="Number of successfully processed chunks")
    error_count: int = Field(..., description="Number of chunks that failed processing")
    model_name: str = Field(..., description="Name of the embedding model used")
    processing_time: float = Field(..., description="Total processing time in seconds")
    errors: Optional[List[str]] = Field(None, description="List of error messages")