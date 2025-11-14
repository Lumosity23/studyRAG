"""
ChromaDB utilities pour StudyRAG
"""

import chromadb
from chromadb.config import Settings
import os
import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class StudyRAGDB:
    """Interface ChromaDB pour StudyRAG"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB client
        
        Args:
            persist_directory: Directory to persist the database
        """
        self.persist_directory = persist_directory
        
        # Create client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="study_documents",
            metadata={"description": "StudyRAG document collection"}
        )
        
        logger.info(f"ChromaDB initialized at {persist_directory}")
    
    async def add_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Add document chunks to the database
        
        Args:
            chunks: List of chunk dictionaries with content, embedding, metadata
            
        Returns:
            True if successful
        """
        try:
            # Prepare data for ChromaDB
            ids = []
            documents = []
            embeddings = []
            metadatas = []
            
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                ids.append(chunk_id)
                documents.append(chunk['content'])
                embeddings.append(chunk['embedding'])
                
                # Prepare metadata
                metadata = {
                    'document_id': chunk.get('document_id', ''),
                    'document_title': chunk.get('document_title', ''),
                    'document_source': chunk.get('document_source', ''),
                    'chunk_index': chunk.get('chunk_index', 0),
                    'token_count': chunk.get('token_count', 0),
                    'created_at': datetime.now().isoformat(),
                    **chunk.get('metadata', {})
                }
                
                # ChromaDB metadata values must be strings, numbers, or booleans
                clean_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        clean_metadata[key] = value
                    else:
                        clean_metadata[key] = str(value)
                
                metadatas.append(clean_metadata)
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(chunks)} chunks to ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"Error adding chunks to ChromaDB: {e}")
            return False
    
    async def search_chunks(
        self, 
        query_embedding: List[float], 
        limit: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of matching chunks with metadata
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            # Format results
            chunks = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    # ChromaDB returns cosine distance, convert to similarity
                    distance = results['distances'][0][i]
                    similarity = 1 - distance  # For cosine distance
                    
                    chunk = {
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'similarity': similarity,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                    }
                    
                    # Filter by similarity threshold
                    if similarity >= similarity_threshold:
                        chunks.append(chunk)
            
            logger.info(f"Found {len(chunks)} matching chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error searching ChromaDB: {e}")
            return []
    
    async def search_chunks_by_text(
        self, 
        query_text: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search using text query (let ChromaDB handle embeddings)
        
        Args:
            query_text: Text query
            limit: Maximum number of results
            
        Returns:
            List of matching chunks with metadata
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=limit
            )
            
            # Format results
            chunks = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    distance = results['distances'][0][i]
                    similarity = 1 - distance
                    
                    chunk = {
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'similarity': similarity,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                    }
                    chunks.append(chunk)
            
            logger.info(f"Found {len(chunks)} matching chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error searching ChromaDB by text: {e}")
            return []
    
    async def clear_collection(self) -> bool:
        """
        Clear all documents from the collection
        
        Returns:
            True if successful
        """
        try:
            # Delete the collection and recreate it
            self.client.delete_collection("study_documents")
            self.collection = self.client.get_or_create_collection(
                name="study_documents",
                metadata={"description": "StudyRAG document collection"}
            )
            
            logger.info("ChromaDB collection cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing ChromaDB: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Dictionary with stats
        """
        try:
            count = self.collection.count()
            
            return {
                "total_chunks": count,
                "collection_name": self.collection.name,
                "persist_directory": self.persist_directory
            }
            
        except Exception as e:
            logger.error(f"Error getting ChromaDB stats: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close database connection"""
        # ChromaDB doesn't need explicit closing
        logger.info("ChromaDB connection closed")


# Factory function
def create_chroma_db(persist_directory: str = "./chroma_db") -> StudyRAGDB:
    """
    Create ChromaDB instance
    
    Args:
        persist_directory: Directory to persist the database
        
    Returns:
        StudyRAGDB instance
    """
    return StudyRAGDB(persist_directory)


# Test function
async def test_chroma_db():
    """Test ChromaDB functionality"""
    from rich.console import Console
    
    console = Console()
    console.print("[blue]🧪 Test ChromaDB[/blue]")
    
    # Create DB
    db = create_chroma_db("./test_chroma")
    
    # Test data
    test_chunks = [
        {
            'content': 'Python est un langage de programmation',
            'embedding': [0.1, 0.2, 0.3] * 128,  # 384 dimensions
            'document_id': 'doc1',
            'document_title': 'Cours Python',
            'document_source': 'test.md',
            'chunk_index': 0,
            'token_count': 10
        },
        {
            'content': 'JavaScript est utilisé pour le web',
            'embedding': [0.2, 0.3, 0.4] * 128,  # 384 dimensions
            'document_id': 'doc2',
            'document_title': 'Cours JS',
            'document_source': 'test2.md',
            'chunk_index': 0,
            'token_count': 8
        }
    ]
    
    # Add chunks
    success = await db.add_chunks(test_chunks)
    console.print(f"Add chunks: {'✅' if success else '❌'}")
    
    # Search
    query_embedding = [0.15, 0.25, 0.35] * 128
    results = await db.search_chunks(query_embedding, limit=2)
    console.print(f"Search results: {len(results)} chunks found")
    
    for result in results:
        console.print(f"  • {result['content'][:50]}... (similarity: {result['similarity']:.3f})")
    
    # Stats
    stats = await db.get_stats()
    console.print(f"Stats: {stats}")
    
    # Cleanup
    await db.clear_collection()
    await db.close()
    
    console.print("✅ ChromaDB test completed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_chroma_db())