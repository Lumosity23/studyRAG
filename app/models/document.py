"""Document-related data models."""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import Field, field_validator
from datetime import datetime

from .common import BaseModel, TimestampMixin, IDMixin, MetadataMixin


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    TXT = "txt"


class ProcessingStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(IDMixin, TimestampMixin, MetadataMixin):
    """Document model representing an uploaded and processed document."""
    
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename of the uploaded document"
    )
    
    file_type: DocumentType = Field(
        ...,
        description="Type of the document (PDF, DOCX, HTML, TXT)"
    )
    
    file_size: int = Field(
        ...,
        ge=0,
        description="Size of the file in bytes"
    )
    
    file_path: Optional[str] = Field(
        None,
        description="Path to the stored file on disk"
    )
    
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING,
        description="Current processing status of the document"
    )
    
    processing_error: Optional[str] = Field(
        None,
        description="Error message if processing failed"
    )
    
    chunk_count: int = Field(
        default=0,
        ge=0,
        description="Number of chunks created from this document"
    )
    
    embedding_model: Optional[str] = Field(
        None,
        description="Name of the embedding model used for this document"
    )
    
    content_preview: Optional[str] = Field(
        None,
        max_length=500,
        description="Preview of the document content (first 500 characters)"
    )
    
    language: Optional[str] = Field(
        None,
        description="Detected language of the document content"
    )
    
    page_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of pages (for PDF documents)"
    )
    
    word_count: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated word count of the document"
    )
    
    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v):
        """Validate filename format."""
        if not v or v.isspace():
            raise ValueError("Filename cannot be empty or whitespace")
        
        # Check for invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        if any(char in v for char in invalid_chars):
            raise ValueError(f"Filename contains invalid characters: {invalid_chars}")
        
        return v.strip()
    
    @field_validator("file_type", mode="before")
    @classmethod
    def validate_file_type(cls, v):
        """Validate and normalize file type."""
        if isinstance(v, str):
            # Extract from filename if needed
            if '.' in v:
                v = v.split('.')[-1].lower()
            return v.lower()
        return v
    
    @field_validator("processing_status")
    @classmethod
    def validate_processing_status_transition(cls, v):
        """Validate processing status transitions."""
        # This could be enhanced to check valid state transitions
        return v
    
    @property
    def is_processed(self) -> bool:
        """Check if document is successfully processed."""
        return self.processing_status == ProcessingStatus.COMPLETED
    
    @property
    def has_chunks(self) -> bool:
        """Check if document has chunks."""
        return self.chunk_count > 0
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)
    
    def update_processing_status(
        self,
        status: ProcessingStatus,
        error: Optional[str] = None,
        chunk_count: Optional[int] = None
    ) -> None:
        """Update processing status and related fields."""
        self.processing_status = status
        self.updated_at = datetime.now()
        
        if error:
            self.processing_error = error
        
        if chunk_count is not None:
            self.chunk_count = chunk_count
    
    def to_summary(self) -> Dict[str, Any]:
        """Get a summary representation of the document."""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size_mb": round(self.file_size_mb, 2),
            "processing_status": self.processing_status,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at,
            "language": self.language,
            "page_count": self.page_count,
            "word_count": self.word_count
        }


class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    
    filename: str = Field(..., description="Name of the file being uploaded")
    file_type: DocumentType = Field(..., description="Type of the document")
    file_size: int = Field(..., ge=0, description="Size of the file in bytes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    
    document_id: str = Field(..., description="ID of the uploaded document")
    filename: str = Field(..., description="Name of the uploaded file")
    processing_status: ProcessingStatus = Field(..., description="Initial processing status")
    message: str = Field(..., description="Upload status message")


class DocumentProcessingUpdate(BaseModel):
    """Model for document processing status updates."""
    
    document_id: str = Field(..., description="ID of the document being processed")
    status: ProcessingStatus = Field(..., description="Current processing status")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="Processing progress (0-1)")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if processing failed")
    chunk_count: Optional[int] = Field(None, ge=0, description="Number of chunks created")


class DocumentListResponse(BaseModel):
    """Response model for document listing."""
    
    documents: List[Document] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    
    
class DocumentStatsResponse(BaseModel):
    """Response model for document statistics."""
    
    total_documents: int = Field(..., description="Total number of documents")
    total_chunks: int = Field(..., description="Total number of chunks")
    total_size_mb: float = Field(..., description="Total size in megabytes")
    by_type: Dict[str, int] = Field(..., description="Document count by type")
    by_status: Dict[str, int] = Field(..., description="Document count by status")
    by_language: Dict[str, int] = Field(..., description="Document count by language")