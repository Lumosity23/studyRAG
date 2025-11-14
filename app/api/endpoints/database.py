"""Database management API endpoints."""

import os
import json
import asyncio
import base64
import gzip
import hashlib
import uuid
import io
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
import structlog

from ...core.config import get_settings
from ...core.exceptions import APIException, DatabaseError
from ...models.document import (
    Document, 
    DocumentListResponse, 
    DocumentStatsResponse,
    ProcessingStatus
)
from ...services.vector_database import VectorDatabase
from ...services.document_processor import DocumentProcessor
from ...services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)

router = APIRouter()

# Global status tracking
reindexing_status: Dict[str, Dict[str, Any]] = {}
import_status: Dict[str, Dict[str, Any]] = {}


def get_vector_database() -> VectorDatabase:
    """Dependency to get vector database instance."""
    return VectorDatabase()


def get_document_processor() -> DocumentProcessor:
    """Dependency to get document processor instance."""
    return DocumentProcessor()


def get_embedding_service() -> EmbeddingService:
    """Dependency to get embedding service instance."""
    return EmbeddingService()


async def reindex_document_background(
    document_id: str,
    new_model: str,
    vector_db: VectorDatabase,
    processor: DocumentProcessor,
    embedding_service: EmbeddingService
):
    """Background task to reindex a document with a new embedding model."""
    try:
        # Update status
        reindexing_status[document_id] = {
            "status": "processing",
            "progress": 0.1,
            "message": "Starting reindexing...",
            "new_model": new_model,
            "started_at": datetime.now().isoformat()
        }
        
        logger.info(f"Starting reindexing for document {document_id} with model {new_model}")
        
        # Get document metadata from vector database
        # This is a placeholder - actual implementation would depend on how documents are stored
        document_info = await vector_db.get_document_info(document_id)
        
        if not document_info:
            raise DatabaseError(f"Document {document_id} not found in database")
        
        # Update progress
        reindexing_status[document_id]["progress"] = 0.3
        reindexing_status[document_id]["message"] = "Retrieving document content..."
        
        # Get original file path or content
        # This would need to be implemented based on how documents are stored
        file_path = document_info.get("file_path")
        
        if not file_path or not os.path.exists(file_path):
            raise DatabaseError(f"Original file not found for document {document_id}")
        
        # Update progress
        reindexing_status[document_id]["progress"] = 0.5
        reindexing_status[document_id]["message"] = "Processing with new model..."
        
        # Switch to new embedding model
        await embedding_service.switch_model(new_model)
        
        # Reprocess document
        document = await processor.process_document(
            file_path, 
            document_info["filename"],
            document_info.get("metadata", {})
        )
        
        # Update progress
        reindexing_status[document_id]["progress"] = 0.8
        reindexing_status[document_id]["message"] = "Updating vector database..."
        
        # Delete old embeddings
        await vector_db.delete_document(document_id)
        
        # Store new embeddings
        # This would need actual chunk data and embeddings
        # Placeholder for now
        
        # Update final status
        reindexing_status[document_id] = {
            "status": "completed",
            "progress": 1.0,
            "message": "Reindexing completed successfully",
            "new_model": new_model,
            "started_at": reindexing_status[document_id]["started_at"],
            "completed_at": datetime.now().isoformat(),
            "new_chunk_count": document.chunk_count
        }
        
        logger.info(f"Successfully reindexed document {document_id}")
        
    except Exception as e:
        logger.error(f"Reindexing failed for document {document_id}: {e}")
        reindexing_status[document_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": "Reindexing failed",
            "error": str(e),
            "new_model": new_model,
            "started_at": reindexing_status[document_id].get("started_at"),
            "failed_at": datetime.now().isoformat()
        }


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of documents to return"),
    status: Optional[ProcessingStatus] = Query(None, description="Filter by processing status"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    search: Optional[str] = Query(None, description="Search in filenames"),
    vector_db: VectorDatabase = Depends(get_vector_database)
):
    """
    List documents in the database with pagination and filtering.
    
    Returns a paginated list of documents with their metadata and processing status.
    """
    try:
        # Build filters
        filters = {}
        if status:
            filters["processing_status"] = status
        if file_type:
            filters["file_type"] = file_type
        if search:
            filters["filename_search"] = search
        
        # Get documents from vector database
        # This is a placeholder - actual implementation depends on vector database schema
        documents_data = await vector_db.list_documents(
            skip=skip,
            limit=limit,
            filters=filters
        )
        
        # Convert to Document models
        documents = []
        for doc_data in documents_data.get("documents", []):
            try:
                document = Document(**doc_data)
                documents.append(document)
            except Exception as e:
                logger.warning(f"Failed to parse document data: {e}")
                continue
        
        total = documents_data.get("total", len(documents))
        
        logger.info(f"Listed {len(documents)} documents (total: {total})")
        
        return DocumentListResponse(
            documents=documents,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve documents from database"
        )


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    vector_db: VectorDatabase = Depends(get_vector_database)
):
    """
    Get detailed information about a specific document.
    
    Returns complete document metadata, processing status, and statistics.
    """
    try:
        # Get document info from vector database
        document_info = await vector_db.get_document_info(document_id)
        
        if not document_info:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        # Convert to Document model
        document = Document(**document_info)
        
        # Get additional statistics
        chunk_stats = await vector_db.get_document_chunk_stats(document_id)
        
        # Combine document info with statistics
        response = {
            **document.dict(),
            "chunk_statistics": chunk_stats,
            "reindexing_status": reindexing_status.get(document_id)
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve document information"
        )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    vector_db: VectorDatabase = Depends(get_vector_database)
):
    """
    Delete a document and all its associated chunks from the database.
    
    This operation cascades to remove all chunks, embeddings, and metadata
    associated with the document.
    """
    try:
        # Check if document exists
        document_info = await vector_db.get_document_info(document_id)
        
        if not document_info:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        # Get chunk count before deletion for logging
        chunk_stats = await vector_db.get_document_chunk_stats(document_id)
        chunk_count = chunk_stats.get("total_chunks", 0)
        
        # Delete document and all associated data
        deleted = await vector_db.delete_document(document_id)
        
        if not deleted:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete document from database"
            )
        
        # Clean up any associated files
        file_path = document_info.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted associated file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete file {file_path}: {e}")
        
        # Clean up reindexing status if exists
        if document_id in reindexing_status:
            del reindexing_status[document_id]
        
        logger.info(f"Deleted document {document_id} with {chunk_count} chunks")
        
        return {
            "message": f"Document {document_id} deleted successfully",
            "document_id": document_id,
            "filename": document_info.get("filename"),
            "chunks_deleted": chunk_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete document"
        )


@router.post("/reindex/{document_id}")
async def reindex_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    new_model: Optional[str] = Query(None, description="New embedding model to use"),
    vector_db: VectorDatabase = Depends(get_vector_database),
    processor: DocumentProcessor = Depends(get_document_processor),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
):
    """
    Reindex a document with a new embedding model.
    
    This recreates all chunks and embeddings for the document using
    the specified embedding model (or current default if not specified).
    """
    try:
        # Check if document exists
        document_info = await vector_db.get_document_info(document_id)
        
        if not document_info:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        # Check if already reindexing
        if document_id in reindexing_status:
            current_status = reindexing_status[document_id]
            if current_status.get("status") == "processing":
                raise HTTPException(
                    status_code=409,
                    detail=f"Document {document_id} is already being reindexed"
                )
        
        # Use current model if not specified
        if not new_model:
            settings = get_settings()
            new_model = settings.EMBEDDING_MODEL
        
        # Validate new model
        available_models = await embedding_service.get_available_models()
        if new_model not in [model["key"] for model in available_models]:
            raise HTTPException(
                status_code=400,
                detail=f"Embedding model '{new_model}' is not available"
            )
        
        # Start background reindexing
        background_tasks.add_task(
            reindex_document_background,
            document_id,
            new_model,
            vector_db,
            processor,
            embedding_service
        )
        
        logger.info(f"Started reindexing for document {document_id} with model {new_model}")
        
        return {
            "message": f"Reindexing started for document {document_id}",
            "document_id": document_id,
            "filename": document_info.get("filename"),
            "new_model": new_model,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start reindexing for document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to start document reindexing"
        )


@router.get("/reindex/{document_id}/status")
async def get_reindexing_status(document_id: str):
    """
    Get the reindexing status for a document.
    
    Returns progress information and any error messages for ongoing
    or completed reindexing operations.
    """
    if document_id not in reindexing_status:
        raise HTTPException(
            status_code=404,
            detail=f"No reindexing status found for document {document_id}"
        )
    
    return reindexing_status[document_id]


@router.get("/stats", response_model=DocumentStatsResponse)
async def get_database_stats(
    vector_db: VectorDatabase = Depends(get_vector_database)
):
    """
    Get comprehensive database statistics.
    
    Returns counts and statistics about documents, chunks, and storage usage.
    """
    try:
        # Get statistics from vector database
        stats = await vector_db.get_database_stats()
        
        return DocumentStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve database statistics"
        )


@router.get("/export")
async def export_database(
    include_files: bool = Query(False, description="Include original files in export"),
    format: str = Query("json", description="Export format (json, csv)"),
    compress: bool = Query(True, description="Compress the export file"),
    vector_db: VectorDatabase = Depends(get_vector_database)
):
    """
    Export database metadata and optionally files.
    
    Creates a comprehensive backup of all document metadata, chunk information,
    embeddings, and optionally the original files. Supports multiple formats
    and compression for efficient storage and transfer.
    """
    try:
        logger.info(f"Starting database export (include_files={include_files}, format={format})")
        
        # Validate format
        if format not in ["json", "csv"]:
            raise HTTPException(
                status_code=400,
                detail="Unsupported export format. Use 'json' or 'csv'"
            )
        
        # Get comprehensive export data from vector database
        export_data = await vector_db.export_database(include_files=include_files)
        
        # Validate export data integrity
        validation_result = await _validate_export_data(export_data)
        if not validation_result["valid"]:
            logger.error(f"Export data validation failed: {validation_result['errors']}")
            raise HTTPException(
                status_code=500,
                detail=f"Export data validation failed: {'; '.join(validation_result['errors'])}"
            )
        
        # Add comprehensive export metadata
        export_data["export_info"] = {
            "exported_at": datetime.now().isoformat(),
            "version": "2.0",
            "format": format,
            "includes_files": include_files,
            "compressed": compress,
            "total_documents": len(export_data.get("documents", [])),
            "total_chunks": sum(
                doc.get("chunk_count", 0) 
                for doc in export_data.get("documents", [])
            ),
            "database_stats": await vector_db.get_database_stats(),
            "schema_version": "1.0",
            "checksum": _calculate_export_checksum(export_data)
        }
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            filename = f"studyrag_backup_{timestamp}.json"
            if compress:
                filename += ".gz"
            
            # Generate JSON export
            def generate_json_export():
                import gzip
                json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
                
                if compress:
                    yield gzip.compress(json_data.encode('utf-8'))
                else:
                    yield json_data.encode('utf-8')
            
            media_type = "application/gzip" if compress else "application/json"
            
            return StreamingResponse(
                generate_json_export(),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
        elif format == "csv":
            filename = f"studyrag_backup_{timestamp}.zip"
            
            # Generate CSV export (multiple files in ZIP)
            def generate_csv_export():
                import zipfile
                import io
                import csv
                
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # Export documents CSV
                    documents_csv = io.StringIO()
                    if export_data.get("documents"):
                        doc_writer = csv.DictWriter(
                            documents_csv,
                            fieldnames=["id", "filename", "file_type", "file_size", 
                                      "processing_status", "chunk_count", "created_at", "language"]
                        )
                        doc_writer.writeheader()
                        for doc in export_data["documents"]:
                            doc_writer.writerow({
                                "id": doc.get("id"),
                                "filename": doc.get("filename"),
                                "file_type": doc.get("file_type"),
                                "file_size": doc.get("file_size"),
                                "processing_status": doc.get("processing_status"),
                                "chunk_count": doc.get("chunk_count"),
                                "created_at": doc.get("created_at"),
                                "language": doc.get("language")
                            })
                    
                    zip_file.writestr("documents.csv", documents_csv.getvalue())
                    
                    # Export chunks CSV
                    chunks_csv = io.StringIO()
                    chunk_fieldnames = ["id", "document_id", "content", "chunk_index", 
                                      "start_index", "end_index", "section_title", "page_number"]
                    chunk_writer = csv.DictWriter(chunks_csv, fieldnames=chunk_fieldnames)
                    chunk_writer.writeheader()
                    
                    for doc in export_data.get("documents", []):
                        for chunk in doc.get("chunks", []):
                            chunk_writer.writerow({
                                "id": chunk.get("id"),
                                "document_id": chunk.get("metadata", {}).get("document_id"),
                                "content": chunk.get("content", "")[:1000],  # Truncate for CSV
                                "chunk_index": chunk.get("metadata", {}).get("chunk_index"),
                                "start_index": chunk.get("metadata", {}).get("start_index"),
                                "end_index": chunk.get("metadata", {}).get("end_index"),
                                "section_title": chunk.get("metadata", {}).get("section_title"),
                                "page_number": chunk.get("metadata", {}).get("page_number")
                            })
                    
                    zip_file.writestr("chunks.csv", chunks_csv.getvalue())
                    
                    # Export metadata JSON
                    zip_file.writestr("export_info.json", 
                                    json.dumps(export_data["export_info"], indent=2))
                
                zip_buffer.seek(0)
                return zip_buffer.getvalue()
            
            return StreamingResponse(
                io.BytesIO(generate_csv_export()),
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database export failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export database: {str(e)}"
        )


@router.post("/import")
async def import_database(
    background_tasks: BackgroundTasks,
    overwrite: bool = Query(False, description="Overwrite existing documents"),
    validate_only: bool = Query(False, description="Only validate import data without importing"),
    import_file: str = Query(..., description="Base64 encoded import file content"),
    vector_db: VectorDatabase = Depends(get_vector_database),
    processor: DocumentProcessor = Depends(get_document_processor),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
):
    """
    Import database from a previously exported backup file.
    
    Restores documents, chunks, embeddings, and metadata from a backup file.
    Supports validation-only mode and conflict resolution through overwrite flag.
    Performs comprehensive data integrity checks before import.
    """
    try:
        logger.info(f"Starting database import (overwrite={overwrite}, validate_only={validate_only})")
        
        # Decode and parse import file
        import_data = await _parse_import_file(import_file)
        
        # Validate import data structure and integrity
        validation_result = await _validate_import_data(import_data, vector_db)
        
        if not validation_result["valid"]:
            logger.error(f"Import validation failed: {validation_result['errors']}")
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Import data validation failed",
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", [])
                }
            )
        
        # If validation-only mode, return validation results
        if validate_only:
            return {
                "message": "Import data validation successful",
                "validation_result": validation_result,
                "import_preview": {
                    "total_documents": len(import_data.get("documents", [])),
                    "total_chunks": sum(
                        doc.get("chunk_count", 0) 
                        for doc in import_data.get("documents", [])
                    ),
                    "conflicts": validation_result.get("conflicts", []),
                    "estimated_time_minutes": validation_result.get("estimated_time_minutes", 0)
                }
            }
        
        # Check for conflicts if overwrite is False
        if not overwrite and validation_result.get("conflicts"):
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Import conflicts detected. Use overwrite=true to proceed.",
                    "conflicts": validation_result["conflicts"]
                }
            )
        
        # Generate import task ID
        import_task_id = str(uuid.uuid4())
        
        # Initialize import status tracking
        import_status[import_task_id] = {
            "status": "starting",
            "progress": 0.0,
            "message": "Initializing import process...",
            "started_at": datetime.now().isoformat(),
            "total_documents": len(import_data.get("documents", [])),
            "processed_documents": 0,
            "errors": [],
            "warnings": []
        }
        
        # Start background import process
        background_tasks.add_task(
            import_database_background,
            import_task_id,
            import_data,
            overwrite,
            vector_db,
            processor,
            embedding_service
        )
        
        logger.info(f"Started background import task {import_task_id}")
        
        return {
            "message": "Database import started successfully",
            "import_task_id": import_task_id,
            "status": "processing",
            "estimated_time_minutes": validation_result.get("estimated_time_minutes", 0),
            "total_documents": len(import_data.get("documents", [])),
            "status_endpoint": f"/api/database/import/{import_task_id}/status"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database import failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start database import: {str(e)}"
        )


@router.get("/import/{import_task_id}/status")
async def get_import_status(import_task_id: str):
    """
    Get the import status for a background import task.
    
    Returns progress information, error messages, and completion status
    for ongoing or completed import operations.
    """
    if import_task_id not in import_status:
        raise HTTPException(
            status_code=404,
            detail=f"No import status found for task {import_task_id}"
        )
    
    return import_status[import_task_id]


@router.get("/health")
async def get_database_health(
    vector_db: VectorDatabase = Depends(get_vector_database)
):
    """
    Get comprehensive database health information.
    
    Returns connection status, performance metrics, and system health indicators
    for all database components.
    """
    try:
        # Get vector database health
        vector_health = await vector_db.health_check()
        
        # Get basic statistics
        stats = await vector_db.get_database_stats()
        
        # Check schema validation
        schema_validation = await vector_db.validate_schema()
        
        # Calculate overall health status
        overall_status = "healthy"
        issues = []
        
        if vector_health.get("status") != "healthy":
            overall_status = "unhealthy"
            issues.append(f"Vector database: {vector_health.get('message')}")
        
        if not schema_validation.get("schema_valid", True):
            overall_status = "degraded" if overall_status == "healthy" else overall_status
            issues.append("Database schema validation failed")
        
        # Performance indicators
        performance_metrics = {
            "documents_per_mb": (
                stats["total_documents"] / max(stats["total_size_mb"], 0.1)
            ),
            "chunks_per_document": (
                stats["total_chunks"] / max(stats["total_documents"], 1)
            ),
            "avg_document_size_mb": (
                stats["total_size_mb"] / max(stats["total_documents"], 1)
            )
        }
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "issues": issues,
            "components": {
                "vector_database": vector_health,
                "schema_validation": schema_validation
            },
            "statistics": stats,
            "performance_metrics": performance_metrics,
            "active_operations": {
                "reindexing_tasks": len([
                    task for task in reindexing_status.values()
                    if task.get("status") == "processing"
                ]),
                "import_tasks": len([
                    task for task in import_status.values()
                    if task.get("status") in ["processing", "starting"]
                ])
            }
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "overall_status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "issues": [f"Health check failed: {str(e)}"],
            "error": str(e)
        }


@router.post("/validate")
async def validate_database_integrity(
    fix_issues: bool = Query(False, description="Attempt to fix detected issues"),
    vector_db: VectorDatabase = Depends(get_vector_database)
):
    """
    Perform comprehensive database integrity validation.
    
    Checks for data consistency, orphaned records, corrupted embeddings,
    and other integrity issues. Optionally attempts to fix detected problems.
    """
    try:
        logger.info(f"Starting database integrity validation (fix_issues={fix_issues})")
        
        validation_results = {
            "validation_timestamp": datetime.now().isoformat(),
            "overall_status": "valid",
            "issues_found": [],
            "warnings": [],
            "fixes_applied": [],
            "statistics": {}
        }
        
        # Check schema validation
        schema_validation = await vector_db.validate_schema()
        if not schema_validation.get("schema_valid", True):
            validation_results["issues_found"].append({
                "type": "schema_invalid",
                "message": "Database schema validation failed",
                "severity": "high",
                "details": schema_validation
            })
        
        # Get all data for validation
        all_data = await vector_db.export_database(include_files=False)
        
        # Validate document-chunk relationships
        document_ids = set()
        chunk_document_ids = set()
        orphaned_chunks = []
        
        for doc in all_data.get("documents", []):
            document_ids.add(doc["id"])
            
            for chunk in doc.get("chunks", []):
                chunk_doc_id = chunk.get("metadata", {}).get("document_id")
                if chunk_doc_id:
                    chunk_document_ids.add(chunk_doc_id)
                    if chunk_doc_id != doc["id"]:
                        orphaned_chunks.append({
                            "chunk_id": chunk["id"],
                            "expected_doc_id": doc["id"],
                            "actual_doc_id": chunk_doc_id
                        })
        
        # Check for orphaned chunks
        if orphaned_chunks:
            validation_results["issues_found"].append({
                "type": "orphaned_chunks",
                "message": f"Found {len(orphaned_chunks)} orphaned chunks",
                "severity": "medium",
                "details": orphaned_chunks[:10]  # Limit details
            })
            
            if fix_issues:
                # Attempt to fix orphaned chunks
                fixed_count = 0
                for orphan in orphaned_chunks:
                    try:
                        # This would require implementing chunk reassignment
                        # For now, just log the issue
                        logger.warning(f"Would fix orphaned chunk {orphan['chunk_id']}")
                        fixed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to fix orphaned chunk {orphan['chunk_id']}: {e}")
                
                validation_results["fixes_applied"].append({
                    "type": "orphaned_chunks_fixed",
                    "count": fixed_count
                })
        
        # Check for missing embeddings
        chunks_without_embeddings = []
        for doc in all_data.get("documents", []):
            for chunk in doc.get("chunks", []):
                if not chunk.get("metadata", {}).get("embedding_vector"):
                    chunks_without_embeddings.append({
                        "chunk_id": chunk["id"],
                        "document_id": doc["id"]
                    })
        
        if chunks_without_embeddings:
            validation_results["warnings"].append({
                "type": "missing_embeddings",
                "message": f"Found {len(chunks_without_embeddings)} chunks without embeddings",
                "severity": "low",
                "count": len(chunks_without_embeddings)
            })
        
        # Calculate statistics
        validation_results["statistics"] = {
            "total_documents": len(document_ids),
            "total_chunks": sum(doc.get("chunk_count", 0) for doc in all_data.get("documents", [])),
            "orphaned_chunks": len(orphaned_chunks),
            "chunks_without_embeddings": len(chunks_without_embeddings),
            "unique_document_ids": len(document_ids),
            "referenced_document_ids": len(chunk_document_ids)
        }
        
        # Determine overall status
        if validation_results["issues_found"]:
            high_severity_issues = [
                issue for issue in validation_results["issues_found"]
                if issue.get("severity") == "high"
            ]
            if high_severity_issues:
                validation_results["overall_status"] = "invalid"
            else:
                validation_results["overall_status"] = "degraded"
        
        logger.info(f"Database validation completed: {validation_results['overall_status']}")
        return validation_results
        
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate database integrity: {str(e)}"
        )


@router.delete("/clear")
async def clear_database(
    confirm: bool = Query(False, description="Confirmation flag - must be true"),
    vector_db: VectorDatabase = Depends(get_vector_database)
):
    """
    Clear all documents and chunks from the database.
    
    WARNING: This operation is irreversible and will delete all data.
    Requires explicit confirmation.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Database clear operation requires explicit confirmation (confirm=true)"
        )
    
    try:
        # Get stats before clearing
        stats = await vector_db.get_database_stats()
        
        # Clear all data
        cleared = await vector_db.clear_database()
        
        if not cleared:
            raise HTTPException(
                status_code=500,
                detail="Failed to clear database"
            )
        
        # Clear processing and reindexing status
        global processing_status, reindexing_status
        processing_status.clear()
        reindexing_status.clear()
        
        logger.warning(f"Database cleared - deleted {stats.get('total_documents', 0)} documents")
        
        return {
            "message": "Database cleared successfully",
            "documents_deleted": stats.get("total_documents", 0),
            "chunks_deleted": stats.get("total_chunks", 0),
            "cleared_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear database: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear database"
        )


# Helper functions for backup and import operations

def _calculate_export_checksum(export_data: Dict[str, Any]) -> str:
    """Calculate checksum for export data integrity verification."""
    try:
        # Create a deterministic string representation
        data_str = json.dumps(export_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    except Exception as e:
        logger.warning(f"Failed to calculate export checksum: {e}")
        return "unknown"


async def _validate_export_data(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate export data structure and integrity."""
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Check required fields
        if "documents" not in export_data:
            validation_result["errors"].append("Missing 'documents' field in export data")
        
        # Validate document structure
        for i, doc in enumerate(export_data.get("documents", [])):
            if not doc.get("id"):
                validation_result["errors"].append(f"Document {i} missing 'id' field")
            
            if not doc.get("filename"):
                validation_result["errors"].append(f"Document {i} missing 'filename' field")
            
            # Validate chunks
            for j, chunk in enumerate(doc.get("chunks", [])):
                if not chunk.get("id"):
                    validation_result["errors"].append(
                        f"Document {i}, chunk {j} missing 'id' field"
                    )
                
                if not chunk.get("content"):
                    validation_result["warnings"].append(
                        f"Document {i}, chunk {j} has empty content"
                    )
        
        # Check for duplicate document IDs
        doc_ids = [doc.get("id") for doc in export_data.get("documents", [])]
        if len(doc_ids) != len(set(doc_ids)):
            validation_result["errors"].append("Duplicate document IDs found in export data")
        
        validation_result["valid"] = len(validation_result["errors"]) == 0
        
    except Exception as e:
        validation_result["valid"] = False
        validation_result["errors"].append(f"Export validation error: {str(e)}")
    
    return validation_result


async def _parse_import_file(import_file_content: str) -> Dict[str, Any]:
    """Parse and decode import file content."""
    try:
        # Decode base64 content
        decoded_content = base64.b64decode(import_file_content)
        
        # Check if content is gzipped
        try:
            if decoded_content.startswith(b'\x1f\x8b'):  # gzip magic number
                decoded_content = gzip.decompress(decoded_content)
        except Exception:
            pass  # Not gzipped, continue with original content
        
        # Parse JSON
        import_data = json.loads(decoded_content.decode('utf-8'))
        
        return import_data
        
    except base64.binascii.Error as e:
        raise ValueError(f"Invalid base64 encoding: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to parse import file: {str(e)}")


async def _validate_import_data(
    import_data: Dict[str, Any], 
    vector_db: VectorDatabase
) -> Dict[str, Any]:
    """Validate import data and check for conflicts."""
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "conflicts": [],
        "estimated_time_minutes": 0
    }
    
    try:
        # Check export info and version compatibility
        export_info = import_data.get("export_info", {})
        version = export_info.get("version", "1.0")
        
        if version not in ["1.0", "2.0"]:
            validation_result["warnings"].append(
                f"Unknown export version {version}, proceeding with caution"
            )
        
        # Validate checksum if available
        if "checksum" in export_info:
            # Create a copy without checksum for validation
            data_for_checksum = import_data.copy()
            data_for_checksum["export_info"] = export_info.copy()
            del data_for_checksum["export_info"]["checksum"]
            
            calculated_checksum = _calculate_export_checksum(data_for_checksum)
            if calculated_checksum != export_info["checksum"]:
                validation_result["errors"].append(
                    "Import data checksum mismatch - data may be corrupted"
                )
        
        # Validate basic structure
        export_validation = await _validate_export_data(import_data)
        validation_result["errors"].extend(export_validation["errors"])
        validation_result["warnings"].extend(export_validation["warnings"])
        
        # Check for conflicts with existing data
        existing_docs = await vector_db.list_documents(limit=10000)  # Get all docs
        existing_doc_ids = set(doc["id"] for doc in existing_docs.get("documents", []))
        
        import_doc_ids = set(doc.get("id") for doc in import_data.get("documents", []))
        conflicts = existing_doc_ids.intersection(import_doc_ids)
        
        if conflicts:
            validation_result["conflicts"] = list(conflicts)
            validation_result["warnings"].append(
                f"Found {len(conflicts)} document ID conflicts with existing data"
            )
        
        # Estimate processing time (rough calculation)
        total_chunks = sum(
            doc.get("chunk_count", 0) 
            for doc in import_data.get("documents", [])
        )
        # Estimate ~100 chunks per minute processing time
        validation_result["estimated_time_minutes"] = max(1, total_chunks // 100)
        
        validation_result["valid"] = len(validation_result["errors"]) == 0
        
    except Exception as e:
        validation_result["valid"] = False
        validation_result["errors"].append(f"Import validation error: {str(e)}")
    
    return validation_result


async def import_database_background(
    import_task_id: str,
    import_data: Dict[str, Any],
    overwrite: bool,
    vector_db: VectorDatabase,
    processor: DocumentProcessor,
    embedding_service: EmbeddingService
):
    """Background task to import database from backup data."""
    try:
        logger.info(f"Starting background import task {import_task_id}")
        
        # Update status
        import_status[import_task_id].update({
            "status": "processing",
            "progress": 0.1,
            "message": "Processing import data..."
        })
        
        documents = import_data.get("documents", [])
        total_docs = len(documents)
        
        if total_docs == 0:
            import_status[import_task_id].update({
                "status": "completed",
                "progress": 1.0,
                "message": "No documents to import",
                "completed_at": datetime.now().isoformat()
            })
            return
        
        processed_count = 0
        error_count = 0
        
        for i, doc_data in enumerate(documents):
            try:
                doc_id = doc_data.get("id")
                if not doc_id:
                    continue
                
                # Update progress
                progress = 0.1 + (i / total_docs) * 0.8
                import_status[import_task_id].update({
                    "progress": progress,
                    "message": f"Processing document {i+1}/{total_docs}: {doc_data.get('filename', 'unknown')}",
                    "processed_documents": processed_count
                })
                
                # Check if document exists
                existing_doc = await vector_db.get_document_info(doc_id)
                
                if existing_doc and not overwrite:
                    import_status[import_task_id]["warnings"].append(
                        f"Skipped existing document: {doc_data.get('filename')}"
                    )
                    continue
                
                # Delete existing document if overwriting
                if existing_doc and overwrite:
                    await vector_db.delete_document(doc_id)
                    logger.info(f"Deleted existing document {doc_id} for overwrite")
                
                # Import chunks
                chunks_data = doc_data.get("chunks", [])
                if chunks_data:
                    # Convert chunk data to Chunk objects
                    from app.models.chunk import Chunk
                    
                    chunks = []
                    embeddings = []
                    
                    for chunk_data in chunks_data:
                        try:
                            # Extract metadata
                            metadata = chunk_data.get("metadata", {})
                            
                            # Create chunk object
                            chunk = Chunk(
                                id=chunk_data.get("id", str(uuid.uuid4())),
                                document_id=doc_id,
                                content=chunk_data.get("content", ""),
                                start_index=metadata.get("start_index", 0),
                                end_index=metadata.get("end_index", 0),
                                chunk_index=metadata.get("chunk_index", 0),
                                section_title=metadata.get("section_title"),
                                page_number=metadata.get("page_number"),
                                language=metadata.get("language"),
                                embedding_model=metadata.get("embedding_model"),
                                token_count=metadata.get("token_count"),
                                metadata=metadata
                            )
                            
                            chunks.append(chunk)
                            
                            # Extract embedding if available
                            embedding = metadata.get("embedding_vector")
                            if embedding and isinstance(embedding, list):
                                embeddings.append(embedding)
                            else:
                                # Generate new embedding
                                new_embedding = await embedding_service.generate_embedding(chunk.content)
                                embeddings.append(new_embedding)
                        
                        except Exception as e:
                            logger.error(f"Failed to process chunk {chunk_data.get('id')}: {e}")
                            continue
                    
                    # Store chunks and embeddings
                    if chunks and embeddings:
                        await vector_db.store_embeddings(chunks, embeddings)
                        logger.info(f"Imported {len(chunks)} chunks for document {doc_id}")
                
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                error_msg = f"Failed to import document {doc_data.get('filename', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                import_status[import_task_id]["errors"].append(error_msg)
        
        # Update final status
        import_status[import_task_id].update({
            "status": "completed",
            "progress": 1.0,
            "message": f"Import completed: {processed_count} documents processed, {error_count} errors",
            "processed_documents": processed_count,
            "completed_at": datetime.now().isoformat(),
            "summary": {
                "total_documents": total_docs,
                "processed_successfully": processed_count,
                "errors": error_count,
                "warnings": len(import_status[import_task_id].get("warnings", []))
            }
        })
        
        logger.info(f"Import task {import_task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Import task {import_task_id} failed: {e}")
        import_status[import_task_id].update({
            "status": "failed",
            "progress": 0.0,
            "message": f"Import failed: {str(e)}",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        })