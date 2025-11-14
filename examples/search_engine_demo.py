#!/usr/bin/env python3
"""
SearchEngine demonstration script.

This script demonstrates the key features of the SearchEngine service:
- Semantic search with similarity scoring
- Hybrid search combining semantic and lexical matching
- Context retrieval optimized for RAG
- Result ranking and filtering
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

from app.services.search_engine import SearchEngine
from app.services.vector_database import VectorDatabaseService
from app.services.embedding_service import EmbeddingService
from app.models.search import SearchQuery, SearchType, ContextRetrievalRequest
from app.models.chunk import Chunk
from app.models.document import Document, DocumentType, ProcessingStatus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockVectorDatabase:
    """Mock vector database for demonstration."""
    
    def __init__(self):
        self.sample_data = [
            {
                "id": "chunk_ml_intro",
                "content": "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed.",
                "similarity_score": 0.95,
                "metadata": {
                    "document_id": "ml_guide_2024",
                    "chunk_index": 0,
                    "start_index": 0,
                    "end_index": 140,
                    "embedding_model": "all-minilm-l6-v2",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Introduction to Machine Learning",
                    "page_number": 1,
                    "language": "en",
                    "token_count": 28
                }
            },
            {
                "id": "chunk_algorithms",
                "content": "Popular machine learning algorithms include linear regression, decision trees, random forests, support vector machines, and neural networks. Each algorithm has specific use cases and performance characteristics.",
                "similarity_score": 0.88,
                "metadata": {
                    "document_id": "ml_guide_2024",
                    "chunk_index": 5,
                    "start_index": 500,
                    "end_index": 680,
                    "embedding_model": "all-minilm-l6-v2",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Machine Learning Algorithms",
                    "page_number": 3,
                    "language": "en",
                    "token_count": 35
                }
            },
            {
                "id": "chunk_deep_learning",
                "content": "Deep learning is a specialized branch of machine learning that uses neural networks with multiple layers to model and understand complex patterns in data.",
                "similarity_score": 0.82,
                "metadata": {
                    "document_id": "deep_learning_handbook",
                    "chunk_index": 0,
                    "start_index": 0,
                    "end_index": 145,
                    "embedding_model": "all-minilm-l6-v2",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "What is Deep Learning?",
                    "page_number": 1,
                    "language": "en",
                    "token_count": 30
                }
            },
            {
                "id": "chunk_python_ml",
                "content": "Python is the most popular programming language for machine learning due to its extensive libraries like scikit-learn, TensorFlow, and PyTorch.",
                "similarity_score": 0.75,
                "metadata": {
                    "document_id": "python_ml_tutorial",
                    "chunk_index": 2,
                    "start_index": 200,
                    "end_index": 340,
                    "embedding_model": "all-minilm-l6-v2",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Python for Machine Learning",
                    "page_number": 2,
                    "language": "en",
                    "token_count": 25
                }
            },
            {
                "id": "chunk_data_preprocessing",
                "content": "Data preprocessing is a crucial step in machine learning that involves cleaning, transforming, and preparing raw data for analysis and model training.",
                "similarity_score": 0.70,
                "metadata": {
                    "document_id": "data_science_basics",
                    "chunk_index": 1,
                    "start_index": 100,
                    "end_index": 240,
                    "embedding_model": "all-minilm-l6-v2",
                    "created_at": datetime.now().isoformat(),
                    "section_title": "Data Preprocessing",
                    "page_number": 1,
                    "language": "en",
                    "token_count": 22
                }
            }
        ]
    
    async def search_similar(self, query_embedding, top_k=10, filters=None, min_similarity=0.0):
        """Mock semantic search."""
        # Filter by similarity threshold
        results = [
            result for result in self.sample_data 
            if result["similarity_score"] >= min_similarity
        ]
        
        # Apply document filters if specified
        if filters and "document_id" in filters:
            results = [
                result for result in results 
                if result["metadata"]["document_id"] == filters["document_id"]
            ]
        
        # Sort by similarity and limit results
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]
    
    async def get_collection_stats(self):
        """Mock collection statistics."""
        return {
            "total_chunks": len(self.sample_data),
            "documents_count": len(set(r["metadata"]["document_id"] for r in self.sample_data)),
            "embedding_models": ["all-minilm-l6-v2"],
            "languages": ["en"]
        }


class MockEmbeddingService:
    """Mock embedding service for demonstration."""
    
    async def generate_embedding(self, text):
        """Mock embedding generation."""
        # Return a mock embedding vector
        return [0.1] * 384
    
    async def get_service_stats(self):
        """Mock service statistics."""
        return {
            "active_model": "all-minilm-l6-v2",
            "loaded_models": ["all-minilm-l6-v2"],
            "cache_stats": {"size": 50, "hit_rate": 0.85}
        }


async def demonstrate_semantic_search(search_engine: SearchEngine):
    """Demonstrate semantic search functionality."""
    print("\n" + "="*60)
    print("SEMANTIC SEARCH DEMONSTRATION")
    print("="*60)
    
    # Test query about machine learning
    query = SearchQuery(
        query="What are machine learning algorithms and their applications?",
        search_type=SearchType.SEMANTIC,
        top_k=3,
        min_similarity=0.7,
        highlight=True
    )
    
    print(f"Query: {query.query}")
    print(f"Search Type: {query.search_type}")
    print(f"Min Similarity: {query.min_similarity}")
    
    response = await search_engine.semantic_search(query)
    
    print(f"\nResults: {len(response.results)} found in {response.search_time:.3f}s")
    print(f"Total Results: {response.total_results}")
    
    for i, result in enumerate(response.results, 1):
        print(f"\n--- Result {i} (Rank: {result.rank}) ---")
        print(f"Similarity Score: {result.similarity_score:.3f}")
        print(f"Document: {result.document.filename}")
        print(f"Section: {result.chunk.section_title}")
        print(f"Content: {result.chunk.content[:100]}...")
        if result.highlighted_content:
            print(f"Highlighted: {result.highlighted_content[:100]}...")


async def demonstrate_hybrid_search(search_engine: SearchEngine):
    """Demonstrate hybrid search functionality."""
    print("\n" + "="*60)
    print("HYBRID SEARCH DEMONSTRATION")
    print("="*60)
    
    query = SearchQuery(
        query="Python machine learning libraries",
        search_type=SearchType.HYBRID,
        top_k=3,
        min_similarity=0.6,
        highlight=True
    )
    
    print(f"Query: {query.query}")
    print(f"Search Type: {query.search_type}")
    
    response = await search_engine.hybrid_search(query)
    
    print(f"\nResults: {len(response.results)} found in {response.search_time:.3f}s")
    
    for i, result in enumerate(response.results, 1):
        print(f"\n--- Hybrid Result {i} ---")
        print(f"Combined Score: {result.similarity_score:.3f}")
        print(f"Section: {result.chunk.section_title}")
        print(f"Content: {result.chunk.content[:120]}...")


async def demonstrate_context_retrieval(search_engine: SearchEngine):
    """Demonstrate context retrieval for RAG."""
    print("\n" + "="*60)
    print("CONTEXT RETRIEVAL FOR RAG DEMONSTRATION")
    print("="*60)
    
    request = ContextRetrievalRequest(
        query="machine learning algorithms and deep learning",
        max_tokens=1000,
        max_chunks=3,
        min_similarity=0.7
    )
    
    print(f"Query: {request.query}")
    print(f"Max Tokens: {request.max_tokens}")
    print(f"Max Chunks: {request.max_chunks}")
    
    response = await search_engine.retrieve_context_for_rag(request)
    
    print(f"\nContext Retrieved in {response.retrieval_time:.3f}s")
    print(f"Chunks Used: {len(response.chunks_used)}")
    print(f"Total Tokens: {response.total_tokens}")
    print(f"Truncated: {response.truncated}")
    
    print(f"\n--- RAG Context ---")
    print(response.context[:500] + "..." if len(response.context) > 500 else response.context)


async def demonstrate_filtering(search_engine: SearchEngine):
    """Demonstrate search filtering capabilities."""
    print("\n" + "="*60)
    print("SEARCH FILTERING DEMONSTRATION")
    print("="*60)
    
    # Search with document filter
    query = SearchQuery(
        query="machine learning",
        document_ids=["ml_guide_2024"],
        top_k=5,
        min_similarity=0.5
    )
    
    print(f"Query: {query.query}")
    print(f"Document Filter: {query.document_ids}")
    
    response = await search_engine.semantic_search(query)
    
    print(f"\nFiltered Results: {len(response.results)}")
    print(f"Filters Applied: {response.filters_applied}")
    
    for result in response.results:
        print(f"- Document: {result.chunk.document_id}, Score: {result.similarity_score:.3f}")


async def demonstrate_search_stats(search_engine: SearchEngine):
    """Demonstrate search statistics."""
    print("\n" + "="*60)
    print("SEARCH STATISTICS DEMONSTRATION")
    print("="*60)
    
    stats = await search_engine.get_search_stats()
    
    print("Search Engine Statistics:")
    print(f"- Total Searches: {stats['total_searches']}")
    print(f"- Average Search Time: {stats['avg_search_time']:.3f}s")
    print(f"- Search Types: {stats['search_types_distribution']}")
    print(f"- Vector DB Stats: {stats['vector_db_stats']}")
    print(f"- Embedding Service Stats: {stats['embedding_service_stats']}")


async def main():
    """Main demonstration function."""
    print("SearchEngine Service Demonstration")
    print("This demo shows the key features of the StudyRAG search engine")
    
    # Initialize mock services
    mock_vector_db = MockVectorDatabase()
    mock_embedding_service = MockEmbeddingService()
    
    # Create search engine
    search_engine = SearchEngine(
        vector_db=mock_vector_db,
        embedding_service=mock_embedding_service,
        max_context_tokens=4000
    )
    
    try:
        # Run demonstrations
        await demonstrate_semantic_search(search_engine)
        await demonstrate_hybrid_search(search_engine)
        await demonstrate_context_retrieval(search_engine)
        await demonstrate_filtering(search_engine)
        await demonstrate_search_stats(search_engine)
        
        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())