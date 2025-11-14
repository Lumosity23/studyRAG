"""Common base models and mixins."""

from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


class BaseModel(PydanticBaseModel):
    """Base model with common configuration."""
    
    model_config = ConfigDict(
        # Allow population by field name and alias
        populate_by_name=True,
        # Use enum values instead of names
        use_enum_values=True,
        # Validate assignment
        validate_assignment=True,
        # Forbid extra fields
        extra="forbid",
        # Serialize datetime as ISO format
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class TimestampMixin(BaseModel):
    """Mixin for models that need timestamp fields."""
    
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the record was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the record was last updated"
    )


class IDMixin(BaseModel):
    """Mixin for models that need ID fields."""
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier"
    )


class MetadataMixin(BaseModel):
    """Mixin for models that need metadata fields."""
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata as key-value pairs"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error_code: str = Field(..., description="Unique error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")


class SuccessResponse(BaseModel):
    """Standard success response model."""
    
    success: bool = Field(True, description="Success indicator")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    
    items: list = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    
    @classmethod
    def create(
        cls,
        items: list,
        total: int,
        pagination: PaginationParams
    ) -> "PaginatedResponse":
        """Create paginated response from items and pagination params."""
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1
        )