"""
Search API endpoints for StudyRAG application.

This module provides endpoints for semantic search, hybrid search,
search suggestions, and context retrieval for RAG applications.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ...models.search import (
    SearchQuery, SearchResponse, SearchSuggestion, SearchSuggestionsResponse,
    ContextRetrievalRequest, ContextRetrievalResponse, SearchType, SearchStats
)
from ...services.search_engine import SearchEngine
from ...core.dependencies import get_search_engine
from ...core.exceptions import SearchEngineError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=SearchResponse,
    summary="Perform semantic search",
    description="Execute semantic similarity search across indexed documents using embeddings"
)
async def semantic_search(
    query: SearchQuery,
    search_engine: SearchEngine = Depends(get_search_engine)
) -> SearchResponse:
    """
    Perform semantic search across indexed documents.
    
    This endpoint uses embedding-based similarity search to find relevant content
    even when exact keywords don't match. The search considers semantic meaning
    and context to return the most relevant results.
    
    Args:
        query: Search query parameters including text, filters, and options
        search_engine: Injected search engine service
        
    Returns:
        SearchResponse with ranked results and metadata
        
    Raises:
        HTTPException: If search fails or validation errors occur
    """
    try:
        logger.info(f"Performing semantic search for query: '{query.query[:100]}...'")
        
        # Force search type to semantic for this endpoint
        query.search_type = SearchType.SEMANTIC
        
        # Execute search
        response = await search_engine.semantic_search(query)
        
        logger.info(
            f"Semantic search completed: {len(response.results)} results "
            f"in {response.search_time:.3f}s"
        )
        
        return response
        
    except ValidationError as e:
        logger.warning(f"Search validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search parameters: {str(e)}"
        )
    except SearchEngineError as e:
        logger.error(f"Search engine error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in semantic search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search"
        )


@router.post(
    "/hybrid",
    response_model=SearchResponse,
    summary="Perform hybrid search",
    description="Execute hybrid search combining semantic similarity and lexical matching"
)
async def hybrid_search(
    query: SearchQuery,
    search_engine: SearchEngine = Depends(get_search_engine)
) -> SearchResponse:
    """
    Perform hybrid search combining semantic and lexical approaches.
    
    This endpoint combines embedding-based semantic search with traditional
    keyword-based lexical search to provide comprehensive results that
    capture both semantic meaning and exact term matches.
    
    Args:
        query: Search query parameters including text, filters, and options
        search_engine: Injected search engine service
        
    Returns:
        SearchResponse with hybrid-ranked results and metadata
        
    Raises:
        HTTPException: If search fails or validation errors occur
    """
    try:
        logger.info(f"Performing hybrid search for query: '{query.query[:100]}...'")
        
        # Force search type to hybrid for this endpoint
        query.search_type = SearchType.HYBRID
        
        # Execute hybrid search
        response = await search_engine.hybrid_search(query)
        
        logger.info(
            f"Hybrid search completed: {len(response.results)} results "
            f"in {response.search_time:.3f}s"
        )
        
        return response
        
    except ValidationError as e:
        logger.warning(f"Hybrid search validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search parameters: {str(e)}"
        )
    except SearchEngineError as e:
        logger.error(f"Hybrid search engine error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid search failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in hybrid search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during hybrid search"
        )


@router.get(
    "/suggestions",
    response_model=SearchSuggestionsResponse,
    summary="Get search suggestions",
    description="Get autocomplete suggestions based on partial query input"
)
async def get_search_suggestions(
    q: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Partial query text for suggestions"
    ),
    max_suggestions: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of suggestions to return"
    ),
    search_engine: SearchEngine = Depends(get_search_engine)
) -> SearchSuggestionsResponse:
    """
    Get search suggestions for autocomplete functionality.
    
    This endpoint provides intelligent search suggestions based on:
    - Common search patterns
    - Indexed document content
    - Query completion suggestions
    - Popular search terms
    
    Args:
        q: Partial query text (minimum 1 character)
        max_suggestions: Maximum number of suggestions to return (1-50)
        search_engine: Injected search engine service
        
    Returns:
        SearchSuggestionsResponse with list of suggestions
        
    Raises:
        HTTPException: If suggestion generation fails
    """
    try:
        logger.debug(f"Getting search suggestions for: '{q}'")
        
        # Validate query length
        if len(q.strip()) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query must be at least 1 character long"
            )
        
        # Get suggestions from search engine
        suggestions = await search_engine.get_search_suggestions(
            partial_query=q.strip(),
            max_suggestions=max_suggestions
        )
        
        response = SearchSuggestionsResponse(
            query=q,
            suggestions=suggestions,
            total_suggestions=len(suggestions)
        )
        
        logger.debug(f"Generated {len(suggestions)} suggestions for query: '{q}'")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating search suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate search suggestions"
        )


@router.post(
    "/context",
    response_model=ContextRetrievalResponse,
    summary="Retrieve context for RAG",
    description="Retrieve optimized context chunks for Retrieval-Augmented Generation"
)
async def retrieve_context_for_rag(
    request: ContextRetrievalRequest,
    search_engine: SearchEngine = Depends(get_search_engine)
) -> ContextRetrievalResponse:
    """
    Retrieve optimized context for RAG (Retrieval-Augmented Generation).
    
    This endpoint finds the most relevant document chunks for a given query
    and formats them as context for language model generation. The context
    is optimized for token limits and includes source metadata.
    
    Args:
        request: Context retrieval parameters including query and limits
        search_engine: Injected search engine service
        
    Returns:
        ContextRetrievalResponse with formatted context and metadata
        
    Raises:
        HTTPException: If context retrieval fails
    """
    try:
        logger.info(f"Retrieving RAG context for query: '{request.query[:100]}...'")
        
        # Execute context retrieval
        response = await search_engine.retrieve_context_for_rag(request)
        
        logger.info(
            f"Context retrieval completed: {len(response.chunks_used)} chunks, "
            f"{response.total_tokens} tokens in {response.retrieval_time:.3f}s"
        )
        
        return response
        
    except ValidationError as e:
        logger.warning(f"Context retrieval validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid context retrieval parameters: {str(e)}"
        )
    except SearchEngineError as e:
        logger.error(f"Context retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Context retrieval failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in context retrieval: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during context retrieval"
        )


@router.get(
    "/stats",
    response_model=Dict[str, Any],
    summary="Get search statistics",
    description="Get comprehensive search engine statistics and performance metrics"
)
async def get_search_statistics(
    search_engine: SearchEngine = Depends(get_search_engine)
) -> Dict[str, Any]:
    """
    Get search engine statistics and performance metrics.
    
    This endpoint provides insights into search usage patterns,
    performance metrics, and system health indicators.
    
    Args:
        search_engine: Injected search engine service
        
    Returns:
        Dictionary with comprehensive search statistics
        
    Raises:
        HTTPException: If statistics retrieval fails
    """
    try:
        logger.debug("Retrieving search engine statistics")
        
        # Get statistics from search engine
        stats = await search_engine.get_search_stats()
        
        logger.debug("Search statistics retrieved successfully")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving search statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve search statistics"
        )


# Additional utility endpoints

@router.get(
    "/health",
    summary="Search service health check",
    description="Check the health and availability of the search service"
)
async def search_health_check(
    search_engine: SearchEngine = Depends(get_search_engine)
) -> Dict[str, Any]:
    """
    Check search service health and availability.
    
    This endpoint verifies that the search engine and its dependencies
    (vector database, embedding service) are functioning correctly.
    
    Args:
        search_engine: Injected search engine service
        
    Returns:
        Dictionary with health status information
    """
    try:
        # Perform basic health checks
        stats = await search_engine.get_search_stats()
        
        # Check if we can perform a simple search
        test_query = SearchQuery(
            query="test",
            top_k=1,
            min_similarity=0.0
        )
        
        # This will test the full search pipeline
        test_response = await search_engine.semantic_search(test_query)
        
        return {
            "status": "healthy",
            "search_engine": "operational",
            "total_searches_performed": stats.get("total_searches", 0),
            "avg_search_time": stats.get("avg_search_time", 0.0),
            "vector_db_status": "connected",
            "embedding_service_status": "operational"
        }
        
    except Exception as e:
        logger.error(f"Search health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "search_engine": "error"
            }
        )


# Note: Exception handlers are defined at the application level in main.py
# These search-specific exceptions are handled by the global exception handlers