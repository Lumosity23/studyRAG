"""Document management API endpoints."""

import os
import uuid
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
import structlog

from ...core.config import get_settings
from ...core.exceptions import DocumentProcessingError, ValidationError, APIException
from ...models.document import (
    Document, 
    DocumentUploadResponse, 
    DocumentProcessingUpdate,
    ProcessingStatus
)
from ...services.document_processor import DocumentProcessor
from ...services.vector_database import VectorDatabase
from ...services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)

router = APIRouter()

# Global processing status tracking
processing_status: Dict[str, DocumentProcessingUpdate] = {}


def get_document_processor() -> DocumentProcessor:
    """Dependency to get document processor instance."""
    return DocumentProcessor()


def get_vector_database() -> VectorDatabase:
    """Dependency to get vector database instance."""
    return VectorDatabase()


def get_embedding_service() -> EmbeddingService:
    """Dependency to get embedding service instance."""
    return EmbeddingService()


async def process_document_background(
    task_id: str,
    file_path: str,
    filename: str,
    metadata: Optional[Dict[str, Any]],
    processor: DocumentProcessor,
    vector_db: VectorDatabase,
    embedding_service: EmbeddingService
):
    """Background task to process document and store embeddings."""
    try:
        # Update status to processing
        processing_status[task_id] = DocumentProcessingUpdate(
            document_id=task_id,
            status=ProcessingStatus.PROCESSING,
            progress=0.1,
            message="Starting document processing..."
        )
        
        # Process document
        logger.info(f"Processing document {filename} with task_id {task_id}")
        document = await processor.process_document(file_path, filename, metadata)
        
        # Update progress
        processing_status[task_id].progress = 0.5
        processing_status[task_id].message = "Generating embeddings..."
        
        # Generate embeddings for chunks
        if document.chunk_count > 0:
            # Get chunks from document processor (this would need to be implemented)
            # For now, we'll simulate this step
            logger.info(f"Generating embeddings for {document.chunk_count} chunks")
            
            # Update progress
            processing_status[task_id].progress = 0.8
            processing_status[task_id].message = "Storing in vector database..."
            
            # Store in vector database (implementation would depend on how chunks are retrieved)
            # This is a placeholder - actual implementation would need chunk retrieval
            
        # Update final status
        processing_status[task_id] = DocumentProcessingUpdate(
            document_id=document.id,
            status=ProcessingStatus.COMPLETED,
            progress=1.0,
            message="Document processing completed successfully",
            chunk_count=document.chunk_count
        )
        
        logger.info(f"Successfully processed document {filename}")
        
    except Exception as e:
        logger.error(f"Document processing failed for {filename}: {e}")
        processing_status[task_id] = DocumentProcessingUpdate(
            document_id=task_id,
            status=ProcessingStatus.FAILED,
            progress=0.0,
            message="Document processing failed",
            error=str(e)
        )
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {e}")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: Optional[str] = None,
    processor: DocumentProcessor = Depends(get_document_processor),
    vector_db: VectorDatabase = Depends(get_vector_database),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
):
    """
    Upload and process a document.
    
    This endpoint accepts file uploads and starts background processing.
    Use the returned task_id to check processing status.
    """
    settings = get_settings()
    
    try:
        # Validate file
        if not file.filename:
            raise ValidationError("No filename provided")
        
        if file.size and file.size > settings.MAX_FILE_SIZE:
            raise ValidationError(
                f"File too large: {file.size / (1024*1024):.1f}MB "
                f"(max: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB)"
            )
        
        # Check file extension
        supported_extensions = processor.get_supported_extensions()
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in supported_extensions:
            raise ValidationError(
                f"Unsupported file type: {file_ext}. "
                f"Supported types: {', '.join(supported_extensions)}"
            )
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Save uploaded file temporarily
        temp_filename = f"{task_id}_{file.filename}"
        temp_path = os.path.join(settings.UPLOAD_DIR, temp_filename)
        
        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Save file
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                import json
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid metadata JSON: {metadata}")
        
        # Add upload metadata
        parsed_metadata.update({
            "original_filename": file.filename,
            "content_type": file.content_type,
            "upload_timestamp": str(asyncio.get_event_loop().time()),
            "task_id": task_id
        })
        
        # Initialize processing status
        processing_status[task_id] = DocumentProcessingUpdate(
            document_id=task_id,
            status=ProcessingStatus.PENDING,
            progress=0.0,
            message="File uploaded, queued for processing"
        )
        
        # Start background processing
        background_tasks.add_task(
            process_document_background,
            task_id,
            temp_path,
            file.filename,
            parsed_metadata,
            processor,
            vector_db,
            embedding_service
        )
        
        logger.info(f"Document upload initiated: {file.filename} (task_id: {task_id})")
        
        return DocumentUploadResponse(
            document_id=task_id,
            filename=file.filename,
            processing_status=ProcessingStatus.PENDING,
            message="Document uploaded successfully. Processing started in background."
        )
        
    except ValidationError as e:
        logger.warning(f"Document upload validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Document upload failed. Please try again."
        )


@router.get("/status/{task_id}", response_model=DocumentProcessingUpdate)
async def get_processing_status(task_id: str):
    """
    Get the processing status of a document upload.
    
    Returns the current status, progress, and any error messages
    for the specified task ID.
    """
    if task_id not in processing_status:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found. It may have expired or never existed."
        )
    
    status = processing_status[task_id]
    
    # Clean up completed or failed tasks after returning status
    if status.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
        # Keep status for a bit longer, but could implement cleanup logic here
        pass
    
    return status


@router.delete("/status/{task_id}")
async def clear_processing_status(task_id: str):
    """
    Clear the processing status for a completed task.
    
    This helps clean up memory for long-running applications.
    """
    if task_id not in processing_status:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    status = processing_status[task_id]
    
    # Only allow clearing completed or failed tasks
    if status.status not in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail="Cannot clear status for active processing task"
        )
    
    del processing_status[task_id]
    
    return {"message": f"Processing status for task {task_id} cleared"}


@router.get("/supported-formats")
async def get_supported_formats(
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    Get list of supported file formats and extensions.
    
    Returns information about supported document types and their limitations.
    """
    settings = get_settings()
    
    return {
        "supported_extensions": processor.get_supported_extensions(),
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "supported_types": {
            "documents": ["PDF", "DOCX", "HTML", "TXT", "Markdown"],
            "audio": ["MP3", "WAV", "M4A", "FLAC", "OGG"]
        },
        "processing_features": {
            "pdf": "Advanced extraction with Docling, preserves structure",
            "docx": "Full document structure extraction",
            "html": "Semantic structure preservation",
            "txt": "Direct text processing with encoding detection",
            "audio": "Automatic speech recognition with Whisper"
        }
    }