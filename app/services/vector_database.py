"""ChromaDB vector database service for StudyRAG application."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api.models.Collection import Collection
from chromadb.errors import ChromaError, NotFoundError

from app.core.config import get_settings
from app.core.exceptions import VectorDatabaseError, ValidationError
from app.models.chunk import Chunk
from app.models.document import Document

logger = logging.getLogger(__name__)


class VectorDatabaseService:
    """ChromaDB vector database service with connection management and health checks."""
    
    def __init__(self, settings=None):
        """Initialize the vector database service.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings or get_settings()
        self._client = None
        self._collection = None
        self._is_connected = False
        
    async def connect(self) -> None:
        """Establish connection to ChromaDB."""
        try:
            # Create ChromaDB client
            if self.settings.CHROMA_HOST == "localhost":
                # Use persistent client for local development
                self._client = chromadb.PersistentClient(
                    path="./chroma_db",
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            else:
                # Use HTTP client for remote ChromaDB
                self._client = chromadb.HttpClient(
                    host=self.settings.CHROMA_HOST,
                    port=self.settings.CHROMA_PORT,
                    settings=ChromaSettings(
                        anonymized_telemetry=False
                    )
                )
            
            # Get or create collection
            await self._ensure_collection()
            self._is_connected = True
            
            logger.info(f"Connected to ChromaDB at {self.settings.chroma_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise VectorDatabaseError(f"Connection failed: {str(e)}")
    
    async def disconnect(self) -> None:
        """Disconnect from ChromaDB."""
        self._client = None
        self._collection = None
        self._is_connected = False
        logger.info("Disconnected from ChromaDB")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on ChromaDB connection.
        
        Returns:
            Health status information
        """
        try:
            if not self._is_connected or not self._client:
                return {
                    "status": "unhealthy",
                    "message": "Not connected to ChromaDB",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Test basic operations
            collection_count = await self._get_collection_count()
            
            return {
                "status": "healthy",
                "message": "ChromaDB is operational",
                "collection_name": self.settings.CHROMA_COLLECTION_NAME,
                "document_count": collection_count,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Create a new collection.
        
        Args:
            name: Collection name
            metadata: Optional collection metadata
            
        Returns:
            True if successful
        """
        try:
            await self._ensure_connected()
            
            collection_metadata = metadata or {
                "description": f"StudyRAG collection: {name}",
                "created_at": datetime.now().isoformat()
            }
            
            self._client.create_collection(
                name=name,
                metadata=collection_metadata
            )
            
            logger.info(f"Created collection: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            raise VectorDatabaseError(f"Collection creation failed: {str(e)}")
    
    async def store_embeddings(
        self,
        chunks: List[Chunk],
        embeddings: List[List[float]]
    ) -> List[str]:
        """Store chunk embeddings in the vector database.
        
        Args:
            chunks: List of chunk objects
            embeddings: List of embedding vectors
            
        Returns:
            List of stored chunk IDs
        """
        try:
            await self._ensure_connected()
            
            if len(chunks) != len(embeddings):
                raise ValidationError("Number of chunks must match number of embeddings")
            
            if not chunks:
                return []
            
            # Prepare data for ChromaDB
            ids = []
            documents = []
            embedding_vectors = []
            metadatas = []
            
            for chunk, embedding in zip(chunks, embeddings):
                # Validate embedding dimensions
                if not embedding or not isinstance(embedding, list):
                    raise ValidationError(f"Invalid embedding for chunk {chunk.id}")
                
                ids.append(chunk.id)
                documents.append(chunk.content)
                embedding_vectors.append(embedding)
                
                # Prepare metadata (ChromaDB requires string, int, float, or bool values)
                metadata = {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "start_index": chunk.start_index,
                    "end_index": chunk.end_index,
                    "content_length": len(chunk.content),
                    "embedding_model": chunk.embedding_model or "unknown",
                    "created_at": chunk.created_at.isoformat(),
                    "section_title": chunk.section_title or "",
                    "page_number": chunk.page_number or 0,
                    "language": chunk.language or "unknown",
                    "token_count": chunk.token_count or 0
                }
                
                # Add custom metadata
                for key, value in chunk.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        metadata[f"custom_{key}"] = value
                    else:
                        metadata[f"custom_{key}"] = str(value)
                
                metadatas.append(metadata)
            
            # Store in ChromaDB
            self._collection.add(
                ids=ids,
                documents=documents,
                embeddings=embedding_vectors,
                metadatas=metadatas
            )
            
            logger.info(f"Stored {len(chunks)} embeddings in ChromaDB")
            return ids
            
        except Exception as e:
            logger.error(f"Failed to store embeddings: {e}")
            raise VectorDatabaseError(f"Storage failed: {str(e)}")
    
    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of search results with similarity scores
        """
        try:
            await self._ensure_connected()
            
            if not query_embedding or not isinstance(query_embedding, list):
                raise ValidationError("Invalid query embedding")
            
            # Prepare ChromaDB query
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": top_k
            }
            
            # Add filters if provided
            if filters:
                where_clause = self._build_where_clause(filters)
                if where_clause:
                    query_params["where"] = where_clause
            
            # Execute search
            results = self._collection.query(**query_params)
            
            # Format results
            search_results = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    # Convert distance to similarity (ChromaDB returns cosine distance)
                    distance = results["distances"][0][i]
                    similarity = 1.0 - distance
                    
                    # Apply similarity threshold
                    if similarity < min_similarity:
                        continue
                    
                    result = {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "similarity_score": similarity,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                    }
                    
                    search_results.append(result)
            
            logger.info(f"Found {len(search_results)} similar embeddings")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise VectorDatabaseError(f"Search failed: {str(e)}")
    
    async def delete_by_document_id(self, document_id: str) -> int:
        """Delete all chunks belonging to a document.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            Number of deleted chunks
        """
        try:
            await self._ensure_connected()
            
            # First, get all chunks for this document
            results = self._collection.get(
                where={"document_id": document_id}
            )
            
            if not results["ids"]:
                logger.info(f"No chunks found for document {document_id}")
                return 0
            
            # Delete the chunks
            self._collection.delete(
                where={"document_id": document_id}
            )
            
            deleted_count = len(results["ids"])
            logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete chunks for document {document_id}: {e}")
            raise VectorDatabaseError(f"Deletion failed: {str(e)}")
    
    async def delete_by_ids(self, chunk_ids: List[str]) -> int:
        """Delete chunks by their IDs.
        
        Args:
            chunk_ids: List of chunk IDs to delete
            
        Returns:
            Number of deleted chunks
        """
        try:
            await self._ensure_connected()
            
            if not chunk_ids:
                return 0
            
            # Delete chunks
            self._collection.delete(ids=chunk_ids)
            
            logger.info(f"Deleted {len(chunk_ids)} chunks by ID")
            return len(chunk_ids)
            
        except Exception as e:
            logger.error(f"Failed to delete chunks by IDs: {e}")
            raise VectorDatabaseError(f"Deletion failed: {str(e)}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics.
        
        Returns:
            Collection statistics
        """
        try:
            await self._ensure_connected()
            
            count = await self._get_collection_count()
            
            # Get sample of metadata to analyze
            sample_results = self._collection.get(limit=100)
            
            stats = {
                "total_chunks": count,
                "collection_name": self.settings.CHROMA_COLLECTION_NAME,
                "documents_count": len(set(
                    meta.get("document_id", "") 
                    for meta in sample_results.get("metadatas", [])
                )) if sample_results.get("metadatas") else 0,
                "embedding_models": list(set(
                    meta.get("embedding_model", "unknown")
                    for meta in sample_results.get("metadatas", [])
                )) if sample_results.get("metadatas") else [],
                "languages": list(set(
                    meta.get("language", "unknown")
                    for meta in sample_results.get("metadatas", [])
                )) if sample_results.get("metadatas") else []
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            raise VectorDatabaseError(f"Stats retrieval failed: {str(e)}")
    
    async def reset_collection(self) -> bool:
        """Reset (clear) the collection.
        
        Returns:
            True if successful
        """
        try:
            await self._ensure_connected()
            
            # Delete and recreate collection
            try:
                self._client.delete_collection(self.settings.CHROMA_COLLECTION_NAME)
            except NotFoundError:
                pass  # Collection doesn't exist, that's fine
            
            await self._ensure_collection()
            
            logger.info(f"Reset collection: {self.settings.CHROMA_COLLECTION_NAME}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise VectorDatabaseError(f"Collection reset failed: {str(e)}")
    
    async def validate_schema(self) -> Dict[str, Any]:
        """Validate the database schema and structure.
        
        Returns:
            Validation results
        """
        try:
            await self._ensure_connected()
            
            # Check collection exists
            collections = self._client.list_collections()
            collection_names = [col.name for col in collections]
            
            validation_results = {
                "collection_exists": self.settings.CHROMA_COLLECTION_NAME in collection_names,
                "collection_name": self.settings.CHROMA_COLLECTION_NAME,
                "total_collections": len(collections),
                "validation_timestamp": datetime.now().isoformat()
            }
            
            if validation_results["collection_exists"]:
                # Check sample data structure
                sample = self._collection.get(limit=1)
                if sample["metadatas"]:
                    required_fields = [
                        "document_id", "chunk_index", "start_index", "end_index",
                        "content_length", "embedding_model", "created_at"
                    ]
                    
                    sample_metadata = sample["metadatas"][0]
                    validation_results["schema_valid"] = all(
                        field in sample_metadata for field in required_fields
                    )
                    validation_results["sample_metadata_keys"] = list(sample_metadata.keys())
                else:
                    validation_results["schema_valid"] = True  # Empty collection is valid
                    validation_results["sample_metadata_keys"] = []
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {
                "collection_exists": False,
                "schema_valid": False,
                "error": str(e),
                "validation_timestamp": datetime.now().isoformat()
            }
    
    # Private methods
    
    async def _ensure_connected(self) -> None:
        """Ensure connection to ChromaDB."""
        if not self._is_connected or not self._client:
            await self.connect()
    
    async def _ensure_collection(self) -> None:
        """Ensure collection exists."""
        try:
            self._collection = self._client.get_collection(
                name=self.settings.CHROMA_COLLECTION_NAME
            )
        except NotFoundError:
            # Collection doesn't exist, create it
            self._collection = self._client.create_collection(
                name=self.settings.CHROMA_COLLECTION_NAME,
                metadata={
                    "description": "StudyRAG document chunks collection",
                    "created_at": datetime.now().isoformat()
                }
            )
            logger.info(f"Created new collection: {self.settings.CHROMA_COLLECTION_NAME}")
    
    async def _get_collection_count(self) -> int:
        """Get total count of items in collection."""
        try:
            return self._collection.count()
        except Exception as e:
            logger.error(f"Failed to get collection count: {e}")
            return 0
    
    def _build_where_clause(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build ChromaDB where clause from filters.
        
        Args:
            filters: Filter dictionary
            
        Returns:
            ChromaDB where clause or None
        """
        if not filters:
            return None
        
        where_clause = {}
        
        for key, value in filters.items():
            if key == "document_id" and value:
                where_clause["document_id"] = value
            elif key == "embedding_model" and value:
                where_clause["embedding_model"] = value
            elif key == "language" and value:
                where_clause["language"] = value
            elif key == "min_chunk_index" and isinstance(value, int):
                where_clause["chunk_index"] = {"$gte": value}
            elif key == "max_chunk_index" and isinstance(value, int):
                if "chunk_index" in where_clause:
                    where_clause["chunk_index"]["$lte"] = value
                else:
                    where_clause["chunk_index"] = {"$lte": value}
        
        return where_clause if where_clause else None


    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """List documents with pagination and filtering.
        
        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            filters: Optional filters
            
        Returns:
            Dictionary with documents list and total count
        """
        try:
            await self._ensure_connected()
            
            # Get all chunks and group by document_id
            all_results = self._collection.get()
            
            if not all_results["metadatas"]:
                return {"documents": [], "total": 0}
            
            # Group chunks by document_id
            documents_dict = {}
            for i, metadata in enumerate(all_results["metadatas"]):
                doc_id = metadata.get("document_id")
                if not doc_id:
                    continue
                
                if doc_id not in documents_dict:
                    # Create document from first chunk metadata
                    documents_dict[doc_id] = {
                        "id": doc_id,
                        "filename": metadata.get("custom_filename", f"document_{doc_id}"),
                        "file_type": metadata.get("custom_file_type", "unknown"),
                        "file_size": metadata.get("custom_file_size", 0),
                        "processing_status": metadata.get("custom_processing_status", "completed"),
                        "chunk_count": 0,
                        "embedding_model": metadata.get("embedding_model", "unknown"),
                        "created_at": metadata.get("created_at", datetime.now().isoformat()),
                        "updated_at": metadata.get("created_at", datetime.now().isoformat()),
                        "language": metadata.get("language", "unknown"),
                        "metadata": {}
                    }
                
                documents_dict[doc_id]["chunk_count"] += 1
            
            # Convert to list and apply filters
            documents_list = list(documents_dict.values())
            
            # Apply filters
            if filters:
                if filters.get("processing_status"):
                    documents_list = [
                        doc for doc in documents_list 
                        if doc["processing_status"] == filters["processing_status"]
                    ]
                if filters.get("file_type"):
                    documents_list = [
                        doc for doc in documents_list 
                        if doc["file_type"] == filters["file_type"]
                    ]
                if filters.get("filename_search"):
                    search_term = filters["filename_search"].lower()
                    documents_list = [
                        doc for doc in documents_list 
                        if search_term in doc["filename"].lower()
                    ]
            
            # Apply pagination
            total = len(documents_list)
            documents_list = documents_list[skip:skip + limit]
            
            return {
                "documents": documents_list,
                "total": total
            }
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise VectorDatabaseError(f"Document listing failed: {str(e)}")
    
    async def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document information or None if not found
        """
        try:
            await self._ensure_connected()
            
            # Get all chunks for this document
            results = self._collection.get(
                where={"document_id": document_id}
            )
            
            if not results["metadatas"]:
                return None
            
            # Build document info from first chunk metadata
            first_metadata = results["metadatas"][0]
            
            document_info = {
                "id": document_id,
                "filename": first_metadata.get("custom_filename", f"document_{document_id}"),
                "file_type": first_metadata.get("custom_file_type", "unknown"),
                "file_size": first_metadata.get("custom_file_size", 0),
                "file_path": first_metadata.get("custom_file_path"),
                "processing_status": first_metadata.get("custom_processing_status", "completed"),
                "chunk_count": len(results["ids"]),
                "embedding_model": first_metadata.get("embedding_model", "unknown"),
                "created_at": first_metadata.get("created_at", datetime.now().isoformat()),
                "updated_at": first_metadata.get("created_at", datetime.now().isoformat()),
                "language": first_metadata.get("language", "unknown"),
                "metadata": {}
            }
            
            return document_info
            
        except Exception as e:
            logger.error(f"Failed to get document info for {document_id}: {e}")
            raise VectorDatabaseError(f"Document info retrieval failed: {str(e)}")
    
    async def get_document_chunk_stats(self, document_id: str) -> Dict[str, Any]:
        """Get chunk statistics for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Chunk statistics
        """
        try:
            await self._ensure_connected()
            
            # Get all chunks for this document
            results = self._collection.get(
                where={"document_id": document_id}
            )
            
            if not results["metadatas"]:
                return {"total_chunks": 0}
            
            # Calculate statistics
            total_chunks = len(results["ids"])
            total_content_length = sum(
                meta.get("content_length", 0) 
                for meta in results["metadatas"]
            )
            
            languages = set(
                meta.get("language", "unknown") 
                for meta in results["metadatas"]
            )
            
            return {
                "total_chunks": total_chunks,
                "total_content_length": total_content_length,
                "languages": list(languages),
                "embedding_model": results["metadatas"][0].get("embedding_model", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Failed to get chunk stats for {document_id}: {e}")
            return {"total_chunks": 0}
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if successful
        """
        try:
            deleted_count = await self.delete_by_document_id(document_id)
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics.
        
        Returns:
            Database statistics
        """
        try:
            await self._ensure_connected()
            
            # Get all data for analysis
            all_results = self._collection.get()
            
            if not all_results["metadatas"]:
                return {
                    "total_documents": 0,
                    "total_chunks": 0,
                    "total_size_mb": 0.0,
                    "by_type": {},
                    "by_status": {},
                    "by_language": {}
                }
            
            # Group by document_id to count documents
            documents = set()
            total_size = 0
            by_type = {}
            by_status = {}
            by_language = {}
            
            for metadata in all_results["metadatas"]:
                doc_id = metadata.get("document_id")
                if doc_id:
                    documents.add(doc_id)
                
                # File size (only count once per document)
                file_size = metadata.get("custom_file_size", 0)
                if isinstance(file_size, (int, float)):
                    total_size += file_size
                
                # Count by type
                file_type = metadata.get("custom_file_type", "unknown")
                by_type[file_type] = by_type.get(file_type, 0) + 1
                
                # Count by status
                status = metadata.get("custom_processing_status", "completed")
                by_status[status] = by_status.get(status, 0) + 1
                
                # Count by language
                language = metadata.get("language", "unknown")
                by_language[language] = by_language.get(language, 0) + 1
            
            return {
                "total_documents": len(documents),
                "total_chunks": len(all_results["ids"]),
                "total_size_mb": total_size / (1024 * 1024),
                "by_type": by_type,
                "by_status": by_status,
                "by_language": by_language
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise VectorDatabaseError(f"Database stats retrieval failed: {str(e)}")
    
    async def export_database(self, include_files: bool = False) -> Dict[str, Any]:
        """Export database contents.
        
        Args:
            include_files: Whether to include file contents
            
        Returns:
            Export data
        """
        try:
            await self._ensure_connected()
            
            # Get all data
            all_results = self._collection.get()
            
            export_data = {
                "documents": [],
                "chunks": [],
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "total_chunks": len(all_results["ids"]) if all_results["ids"] else 0,
                    "include_files": include_files
                }
            }
            
            if not all_results["ids"]:
                return export_data
            
            # Group chunks by document
            documents_dict = {}
            
            for i, chunk_id in enumerate(all_results["ids"]):
                metadata = all_results["metadatas"][i] if all_results["metadatas"] else {}
                content = all_results["documents"][i] if all_results["documents"] else ""
                
                doc_id = metadata.get("document_id")
                if not doc_id:
                    continue
                
                # Add to documents dict
                if doc_id not in documents_dict:
                    documents_dict[doc_id] = {
                        "id": doc_id,
                        "filename": metadata.get("custom_filename", f"document_{doc_id}"),
                        "file_type": metadata.get("custom_file_type", "unknown"),
                        "file_size": metadata.get("custom_file_size", 0),
                        "processing_status": metadata.get("custom_processing_status", "completed"),
                        "chunk_count": 0,
                        "chunks": []
                    }
                
                # Add chunk
                chunk_data = {
                    "id": chunk_id,
                    "content": content,
                    "metadata": metadata
                }
                
                documents_dict[doc_id]["chunks"].append(chunk_data)
                documents_dict[doc_id]["chunk_count"] += 1
            
            export_data["documents"] = list(documents_dict.values())
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export database: {e}")
            raise VectorDatabaseError(f"Database export failed: {str(e)}")
    
    async def clear_database(self) -> bool:
        """Clear all data from the database.
        
        Returns:
            True if successful
        """
        try:
            return await self.reset_collection()
            
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False


# Create alias for backward compatibility
VectorDatabase = VectorDatabaseService


# Factory function for dependency injection
def get_vector_database_service() -> VectorDatabaseService:
    """Get vector database service instance."""
    return VectorDatabaseService()