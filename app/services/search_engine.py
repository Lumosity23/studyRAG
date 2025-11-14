"""
Search engine service for StudyRAG application.

This service provides semantic search, hybrid search, result ranking,
and context retrieval optimized for RAG applications.
"""

import asyncio
import logging
import time
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from collections import defaultdict, Counter
import math

from ..models.search import (
    SearchQuery, SearchResult, SearchResponse, SearchType,
    ContextRetrievalRequest, ContextRetrievalResponse, SearchSuggestion
)
from ..models.chunk import Chunk
from ..models.document import Document
from ..services.vector_database import VectorDatabaseService
from ..services.embedding_service import EmbeddingService
from ..core.exceptions import SearchEngineError, ValidationError

logger = logging.getLogger(__name__)


class SearchEngine:
    """
    Advanced search engine with semantic similarity search using ChromaDB.
    
    Provides semantic search, hybrid search, result ranking, filtering,
    and context retrieval optimized for RAG applications.
    """
    
    def __init__(
        self,
        vector_db: VectorDatabaseService,
        embedding_service: EmbeddingService,
        max_context_tokens: int = 4000,
        default_chunk_overlap: int = 50
    ):
        """
        Initialize search engine.
        
        Args:
            vector_db: Vector database service
            embedding_service: Embedding service
            max_context_tokens: Maximum tokens for RAG context
            default_chunk_overlap: Default overlap for context chunks
        """
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.max_context_tokens = max_context_tokens
        self.default_chunk_overlap = default_chunk_overlap
        
        # Search statistics
        self._search_stats = {
            "total_searches": 0,
            "total_search_time": 0.0,
            "search_types": defaultdict(int),
            "query_cache": {}
        }
        
        logger.info("Initialized SearchEngine")
    
    async def semantic_search(
        self,
        query: SearchQuery
    ) -> SearchResponse:
        """
        Perform semantic similarity search using embeddings.
        
        Args:
            query: Search query parameters
            
        Returns:
            Search response with ranked results
        """
        start_time = time.time()
        
        try:
            # Update statistics
            self._search_stats["total_searches"] += 1
            self._search_stats["search_types"][SearchType.SEMANTIC] += 1
            
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query.query)
            
            # Prepare filters for vector database
            filters = self._build_vector_filters(query)
            
            # Search in vector database
            vector_results = await self.vector_db.search_similar(
                query_embedding=query_embedding,
                top_k=min(query.top_k * 2, 100),  # Get more results for better ranking
                filters=filters,
                min_similarity=query.min_similarity
            )
            
            # Convert to SearchResult objects
            search_results = await self._convert_vector_results(vector_results, query)
            
            # Apply additional filtering
            filtered_results = self._apply_additional_filters(search_results, query)
            
            # Rank and score results
            ranked_results = self._rank_results(filtered_results, query)
            
            # Limit to requested number
            final_results = ranked_results[:query.top_k]
            
            # Add highlighting if requested
            if query.highlight:
                final_results = await self._add_highlighting(final_results, query.query)
            
            # Add rank information
            for i, result in enumerate(final_results):
                result.rank = i + 1
            
            search_time = time.time() - start_time
            self._search_stats["total_search_time"] += search_time
            
            logger.info(f"Semantic search completed: {len(final_results)} results in {search_time:.3f}s")
            
            return SearchResponse(
                query=query.query,
                search_type=SearchType.SEMANTIC,
                results=final_results,
                total_results=len(vector_results),
                search_time=search_time,
                filters_applied=self._get_applied_filters(query)
            )
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise SearchEngineError(f"Semantic search failed: {str(e)}")
    
    async def hybrid_search(
        self,
        query: SearchQuery
    ) -> SearchResponse:
        """
        Perform hybrid search combining semantic and lexical matching.
        
        Args:
            query: Search query parameters
            
        Returns:
            Search response with hybrid ranked results
        """
        start_time = time.time()
        
        try:
            # Update statistics
            self._search_stats["total_searches"] += 1
            self._search_stats["search_types"][SearchType.HYBRID] += 1
            
            # Perform semantic search
            semantic_query = SearchQuery(**query.model_dump())
            semantic_query.search_type = SearchType.SEMANTIC
            semantic_query.top_k = min(query.top_k * 3, 150)  # Get more for fusion
            
            semantic_response = await self.semantic_search(semantic_query)
            semantic_results = semantic_response.results
            
            # Perform lexical search
            lexical_results = await self._lexical_search(query)
            
            # Combine and rank using hybrid scoring
            hybrid_results = self._hybrid_rank_fusion(
                semantic_results, 
                lexical_results, 
                query
            )
            
            # Limit to requested number
            final_results = hybrid_results[:query.top_k]
            
            # Add highlighting if requested
            if query.highlight:
                final_results = await self._add_highlighting(final_results, query.query)
            
            # Add rank information
            for i, result in enumerate(final_results):
                result.rank = i + 1
            
            search_time = time.time() - start_time
            self._search_stats["total_search_time"] += search_time
            
            logger.info(f"Hybrid search completed: {len(final_results)} results in {search_time:.3f}s")
            
            return SearchResponse(
                query=query.query,
                search_type=SearchType.HYBRID,
                results=final_results,
                total_results=len(semantic_results) + len(lexical_results),
                search_time=search_time,
                filters_applied=self._get_applied_filters(query)
            )
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise SearchEngineError(f"Hybrid search failed: {str(e)}")
    
    async def retrieve_context_for_rag(
        self,
        request: ContextRetrievalRequest
    ) -> ContextRetrievalResponse:
        """
        Retrieve optimized context for RAG applications.
        
        Args:
            request: Context retrieval request
            
        Returns:
            Context response with optimized text and metadata
        """
        start_time = time.time()
        
        try:
            # Create search query for context retrieval
            search_query = SearchQuery(
                query=request.query,
                search_type=SearchType.SEMANTIC,
                top_k=request.max_chunks,
                min_similarity=request.min_similarity,
                document_ids=request.document_ids,
                include_metadata=True,
                highlight=False
            )
            
            # Perform semantic search
            search_response = await self.semantic_search(search_query)
            
            # Build context from results
            context_parts = []
            chunks_used = []
            total_tokens = 0
            truncated = False
            
            for result in search_response.results:
                # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
                chunk_tokens = len(result.chunk.content) // 4
                
                if total_tokens + chunk_tokens > request.max_tokens:
                    # Try to fit partial content
                    remaining_tokens = request.max_tokens - total_tokens
                    remaining_chars = remaining_tokens * 4
                    
                    if remaining_chars > 100:  # Only if we can fit meaningful content
                        partial_content = result.chunk.content[:remaining_chars]
                        # Try to break at sentence boundary
                        last_sentence = partial_content.rfind('.')
                        if last_sentence > remaining_chars * 0.7:  # If we can keep most content
                            partial_content = partial_content[:last_sentence + 1]
                        
                        context_parts.append(self._format_context_chunk(result, partial_content))
                        total_tokens += len(partial_content) // 4
                    
                    truncated = True
                    break
                
                # Add full chunk
                formatted_chunk = self._format_context_chunk(result)
                context_parts.append(formatted_chunk)
                chunks_used.append(result)
                total_tokens += chunk_tokens
            
            # Join context parts
            context = "\n\n".join(context_parts)
            
            retrieval_time = time.time() - start_time
            
            logger.info(f"Retrieved context: {len(chunks_used)} chunks, {total_tokens} tokens in {retrieval_time:.3f}s")
            
            return ContextRetrievalResponse(
                context=context,
                chunks_used=chunks_used,
                total_tokens=total_tokens,
                retrieval_time=retrieval_time,
                truncated=truncated
            )
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            raise SearchEngineError(f"Context retrieval failed: {str(e)}")
    
    async def get_search_suggestions(
        self,
        partial_query: str,
        max_suggestions: int = 10
    ) -> List[SearchSuggestion]:
        """
        Get search suggestions based on partial query.
        
        Args:
            partial_query: Partial search query
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of search suggestions
        """
        try:
            if len(partial_query.strip()) < 2:
                return []
            
            # Get collection stats to find common terms
            stats = await self.vector_db.get_collection_stats()
            
            # For now, return simple suggestions based on common patterns
            # This could be enhanced with a proper suggestion index
            suggestions = []
            
            # Add some common search patterns
            common_patterns = [
                f"What is {partial_query}?",
                f"How to {partial_query}",
                f"{partial_query} definition",
                f"{partial_query} examples",
                f"{partial_query} tutorial"
            ]
            
            for i, pattern in enumerate(common_patterns[:max_suggestions]):
                suggestions.append(SearchSuggestion(
                    suggestion=pattern,
                    frequency=max_suggestions - i,  # Mock frequency
                    category="pattern"
                ))
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []
    
    async def get_search_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        avg_search_time = (
            self._search_stats["total_search_time"] / 
            max(self._search_stats["total_searches"], 1)
        )
        
        return {
            "total_searches": self._search_stats["total_searches"],
            "avg_search_time": avg_search_time,
            "search_types_distribution": dict(self._search_stats["search_types"]),
            "vector_db_stats": await self.vector_db.get_collection_stats(),
            "embedding_service_stats": await self.embedding_service.get_service_stats()
        }
    
    # Private methods
    
    def _build_vector_filters(self, query: SearchQuery) -> Optional[Dict[str, Any]]:
        """Build filters for vector database query."""
        filters = {}
        
        if query.document_ids:
            if len(query.document_ids) == 1:
                filters["document_id"] = query.document_ids[0]
            else:
                # ChromaDB doesn't support IN operator directly, so we'll handle this differently
                # For now, we'll search without document filter and filter results later
                pass
        
        if query.document_types:
            # This would need to be handled at the application level
            # since document type is not stored in chunk metadata
            pass
        
        if query.languages:
            if len(query.languages) == 1:
                filters["language"] = query.languages[0]
        
        # Add custom filters
        if query.filters:
            for key, value in query.filters.items():
                if key in ["embedding_model", "section_title"]:
                    filters[key] = value
        
        return filters if filters else None
    
    async def _convert_vector_results(
        self, 
        vector_results: List[Dict[str, Any]], 
        query: SearchQuery
    ) -> List[SearchResult]:
        """Convert vector database results to SearchResult objects."""
        search_results = []
        
        for result in vector_results:
            try:
                # Extract metadata
                metadata = result.get("metadata", {})
                
                # Create Chunk object
                chunk = Chunk(
                    id=result["id"],
                    document_id=metadata.get("document_id", ""),
                    content=result["content"],
                    start_index=metadata.get("start_index", 0),
                    end_index=metadata.get("end_index", len(result["content"])),
                    chunk_index=metadata.get("chunk_index", 0),
                    embedding_model=metadata.get("embedding_model", ""),
                    created_at=datetime.fromisoformat(metadata.get("created_at", datetime.now().isoformat())),
                    section_title=metadata.get("section_title"),
                    page_number=metadata.get("page_number"),
                    language=metadata.get("language"),
                    token_count=metadata.get("token_count"),
                    metadata={k: v for k, v in metadata.items() if k.startswith("custom_")}
                )
                
                # Create mock Document object (in real implementation, this would be fetched)
                document = Document(
                    id=chunk.document_id,
                    filename=f"document_{chunk.document_id}",  # Mock filename
                    file_type="pdf",  # Mock type
                    file_size=0,  # Mock size
                    processing_status="completed"
                )
                
                # Create SearchResult
                search_result = SearchResult(
                    chunk=chunk,
                    document=document,
                    similarity_score=result["similarity_score"]
                )
                
                search_results.append(search_result)
                
            except Exception as e:
                logger.warning(f"Failed to convert vector result: {e}")
                continue
        
        return search_results
    
    def _apply_additional_filters(
        self, 
        results: List[SearchResult], 
        query: SearchQuery
    ) -> List[SearchResult]:
        """Apply additional filters that couldn't be handled by vector database."""
        filtered_results = results
        
        # Filter by document IDs if multiple specified
        if query.document_ids and len(query.document_ids) > 1:
            filtered_results = [
                r for r in filtered_results 
                if r.chunk.document_id in query.document_ids
            ]
        
        # Filter by date range
        if query.date_from or query.date_to:
            filtered_results = [
                r for r in filtered_results
                if self._is_in_date_range(r.chunk.created_at, query.date_from, query.date_to)
            ]
        
        return filtered_results
    
    def _is_in_date_range(
        self, 
        date: datetime, 
        date_from: Optional[datetime], 
        date_to: Optional[datetime]
    ) -> bool:
        """Check if date is within specified range."""
        if date_from and date < date_from:
            return False
        if date_to and date > date_to:
            return False
        return True
    
    def _rank_results(
        self, 
        results: List[SearchResult], 
        query: SearchQuery
    ) -> List[SearchResult]:
        """Rank search results using multiple factors."""
        if not results:
            return results
        
        # Calculate additional scoring factors
        for result in results:
            # Base score is similarity
            base_score = result.similarity_score
            
            # Boost score based on content quality indicators
            content_boost = self._calculate_content_boost(result.chunk, query.query)
            
            # Boost score based on metadata
            metadata_boost = self._calculate_metadata_boost(result.chunk)
            
            # Calculate final score
            final_score = base_score * (1 + content_boost + metadata_boost)
            result.similarity_score = min(final_score, 1.0)  # Cap at 1.0
        
        # Sort by final score
        return sorted(results, key=lambda r: r.similarity_score, reverse=True)
    
    def _calculate_content_boost(self, chunk: Chunk, query: str) -> float:
        """Calculate content quality boost factor."""
        boost = 0.0
        
        # Boost for exact matches
        query_lower = query.lower()
        content_lower = chunk.content.lower()
        
        if query_lower in content_lower:
            boost += 0.1
        
        # Boost for title/header content
        if chunk.section_title and any(
            word in chunk.section_title.lower() 
            for word in query_lower.split()
        ):
            boost += 0.05
        
        # Boost for appropriate chunk length (not too short, not too long)
        content_length = len(chunk.content)
        if 200 <= content_length <= 1000:
            boost += 0.02
        elif content_length < 50:
            boost -= 0.05  # Penalize very short chunks
        
        return boost
    
    def _calculate_metadata_boost(self, chunk: Chunk) -> float:
        """Calculate metadata-based boost factor."""
        boost = 0.0
        
        # Boost for chunks with section titles
        if chunk.section_title:
            boost += 0.02
        
        # Boost for recent content (if timestamp available)
        if chunk.created_at:
            days_old = (datetime.now() - chunk.created_at).days
            if days_old < 30:
                boost += 0.01
        
        return boost
    
    async def _lexical_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform lexical (keyword-based) search."""
        # This is a simplified implementation
        # In a full implementation, this would use a proper text search index
        
        try:
            # Get all chunks from vector database (this is inefficient but works for demo)
            # In production, you'd want a separate text search index
            all_results = await self.vector_db.search_similar(
                query_embedding=[0.0] * 384,  # Dummy embedding
                top_k=1000,  # Get many results
                min_similarity=0.0
            )
            
            # Convert to SearchResult objects
            search_results = await self._convert_vector_results(all_results, query)
            
            # Score based on lexical matching
            query_terms = self._extract_query_terms(query.query)
            
            lexical_results = []
            for result in search_results:
                lexical_score = self._calculate_lexical_score(result.chunk.content, query_terms)
                if lexical_score > 0.1:  # Only include results with meaningful lexical match
                    result.similarity_score = lexical_score
                    lexical_results.append(result)
            
            # Sort by lexical score
            lexical_results.sort(key=lambda r: r.similarity_score, reverse=True)
            
            return lexical_results[:query.top_k * 2]  # Return top lexical matches
            
        except Exception as e:
            logger.warning(f"Lexical search failed: {e}")
            return []
    
    def _extract_query_terms(self, query: str) -> List[str]:
        """Extract search terms from query."""
        # Simple tokenization - could be enhanced with proper NLP
        terms = re.findall(r'\b\w+\b', query.lower())
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'what', 'how', 'when', 'where', 'why', 'who'}
        return [term for term in terms if term not in stop_words and len(term) > 2]
    
    def _calculate_lexical_score(self, content: str, query_terms: List[str]) -> float:
        """Calculate lexical matching score."""
        if not query_terms:
            return 0.0
        
        content_lower = content.lower()
        content_terms = re.findall(r'\b\w+\b', content_lower)
        content_term_counts = Counter(content_terms)
        
        score = 0.0
        total_terms = len(query_terms)
        
        for term in query_terms:
            if term in content_term_counts:
                # TF-IDF like scoring
                tf = content_term_counts[term] / len(content_terms)
                # Simple boost for exact matches
                score += tf * (2.0 if term in content_lower else 1.0)
        
        # Normalize by query length
        return min(score / total_terms, 1.0)
    
    def _hybrid_rank_fusion(
        self,
        semantic_results: List[SearchResult],
        lexical_results: List[SearchResult],
        query: SearchQuery
    ) -> List[SearchResult]:
        """Combine semantic and lexical results using rank fusion."""
        # Create maps for efficient lookup
        semantic_map = {r.chunk.id: (i, r) for i, r in enumerate(semantic_results)}
        lexical_map = {r.chunk.id: (i, r) for i, r in enumerate(lexical_results)}
        
        # Get all unique chunk IDs
        all_chunk_ids = set(semantic_map.keys()) | set(lexical_map.keys())
        
        hybrid_results = []
        
        for chunk_id in all_chunk_ids:
            # Get ranks and scores from both searches
            semantic_rank, semantic_result = semantic_map.get(chunk_id, (len(semantic_results), None))
            lexical_rank, lexical_result = lexical_map.get(chunk_id, (len(lexical_results), None))
            
            # Use the result object from whichever search found it (prefer semantic)
            result = semantic_result or lexical_result
            
            # Calculate hybrid score using reciprocal rank fusion
            semantic_score = 1.0 / (semantic_rank + 1) if semantic_result else 0.0
            lexical_score = 1.0 / (lexical_rank + 1) if lexical_result else 0.0
            
            # Weight semantic vs lexical (favor semantic slightly)
            hybrid_score = (0.6 * semantic_score) + (0.4 * lexical_score)
            
            # Also consider original similarity scores
            if semantic_result:
                hybrid_score += 0.2 * semantic_result.similarity_score
            if lexical_result:
                hybrid_score += 0.1 * lexical_result.similarity_score
            
            result.similarity_score = min(hybrid_score, 1.0)
            hybrid_results.append(result)
        
        # Sort by hybrid score
        return sorted(hybrid_results, key=lambda r: r.similarity_score, reverse=True)
    
    async def _add_highlighting(
        self, 
        results: List[SearchResult], 
        query: str
    ) -> List[SearchResult]:
        """Add highlighting to search results."""
        query_terms = self._extract_query_terms(query)
        
        for result in results:
            highlighted_content = result.chunk.content
            
            # Simple highlighting - could be enhanced
            for term in query_terms:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                highlighted_content = pattern.sub(
                    f"<mark>{term}</mark>", 
                    highlighted_content
                )
            
            result.highlighted_content = highlighted_content
        
        return results
    
    def _format_context_chunk(
        self, 
        result: SearchResult, 
        content: Optional[str] = None
    ) -> str:
        """Format a chunk for RAG context."""
        chunk_content = content or result.chunk.content
        
        # Add metadata context
        context_parts = []
        
        # Add source information
        if result.chunk.section_title:
            context_parts.append(f"Section: {result.chunk.section_title}")
        
        if result.chunk.page_number:
            context_parts.append(f"Page: {result.chunk.page_number}")
        
        # Add document reference
        context_parts.append(f"Source: {result.document.filename}")
        
        # Format the chunk
        header = " | ".join(context_parts) if context_parts else "Content"
        return f"[{header}]\n{chunk_content}"
    
    def _get_applied_filters(self, query: SearchQuery) -> Optional[Dict[str, Any]]:
        """Get summary of applied filters."""
        filters = {}
        
        if query.document_ids:
            filters["document_ids"] = query.document_ids
        if query.document_types:
            filters["document_types"] = query.document_types
        if query.languages:
            filters["languages"] = query.languages
        if query.date_from:
            filters["date_from"] = query.date_from.isoformat()
        if query.date_to:
            filters["date_to"] = query.date_to.isoformat()
        if query.min_similarity != 0.5:  # Default value
            filters["min_similarity"] = query.min_similarity
        
        return filters if filters else None


# Factory function for dependency injection
def get_search_engine(
    vector_db: VectorDatabaseService,
    embedding_service: EmbeddingService
) -> SearchEngine:
    """Get search engine instance."""
    return SearchEngine(vector_db, embedding_service)