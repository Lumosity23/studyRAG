---
inclusion: always
---

# Optimisation des Performances StudyRAG

## 🚀 Optimisations Base de Données

### PostgreSQL + PGVector
```sql
-- Index pour recherche vectorielle
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Index sur métadonnées fréquemment utilisées
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_documents_source ON documents(source);
CREATE INDEX idx_chunks_token_count ON chunks(token_count);
```

### Pool de Connexions
```python
# Configuration optimale
db_pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=2,        # Minimum de connexions
    max_size=10,       # Maximum selon charge
    command_timeout=60, # Timeout requêtes
    max_queries=50000,  # Limite par connexion
    max_inactive_connection_lifetime=300  # 5min
)
```

### Requêtes Optimisées
```python
# Batch insert pour chunks
async def batch_insert_chunks(chunks_data: List[dict]):
    query = """
    INSERT INTO chunks (document_id, content, embedding, chunk_index, metadata, token_count)
    VALUES ($1, $2, $3, $4, $5, $6)
    """
    await conn.executemany(query, chunks_data)
```

## 🧠 Optimisations Embeddings

### Cache Local
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_embed(text: str) -> List[float]:
    """Cache des embeddings fréquemment utilisés"""
    return embedder.embed(text)

# Cache persistant avec diskcache
import diskcache as dc
cache = dc.Cache('embeddings_cache')

def persistent_embed(text: str) -> List[float]:
    text_hash = hashlib.md5(text.encode()).hexdigest()
    if text_hash in cache:
        return cache[text_hash]
    
    embedding = embedder.embed(text)
    cache[text_hash] = embedding
    return embedding
```

### Batch Processing
```python
# Traiter les embeddings par batch
def batch_embed_chunks(chunks: List[str], batch_size: int = 32) -> List[List[float]]:
    embeddings = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_embeddings = embedder.embed_batch(batch)
        embeddings.extend(batch_embeddings)
    return embeddings
```

## 📄 Optimisations Traitement Documents

### Chunking Intelligent
```python
# Chunking adaptatif selon le type de document
def adaptive_chunking(content: str, doc_type: str) -> List[str]:
    if doc_type == 'pdf':
        # PDFs : chunks plus grands, overlap réduit
        return chunk_text(content, chunk_size=1200, overlap=150)
    elif doc_type == 'html':
        # HTML : chunking par sections
        return semantic_chunking(content)
    else:
        # Défaut
        return chunk_text(content, chunk_size=1000, overlap=200)
```

### Traitement Asynchrone
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_documents_parallel(doc_paths: List[str]) -> List[dict]:
    """Traitement parallèle des documents"""
    with ThreadPoolExecutor(max_workers=4) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, process_single_document, path)
            for path in doc_paths
        ]
        return await asyncio.gather(*tasks)
```

## 🔍 Optimisations Recherche

### Recherche Hybride
```python
async def hybrid_search(query: str, limit: int = 5) -> List[SearchResult]:
    """Combine recherche vectorielle + texte"""
    
    # 1. Recherche vectorielle (sémantique)
    vector_results = await vector_search(query, limit * 2)
    
    # 2. Recherche textuelle (mots-clés)
    text_results = await text_search(query, limit * 2)
    
    # 3. Fusion et re-ranking
    combined = merge_and_rerank(vector_results, text_results)
    return combined[:limit]
```

### Pre-filtering
```python
async def filtered_search(
    query: str, 
    doc_types: List[str] = None,
    date_range: tuple = None
) -> List[SearchResult]:
    """Recherche avec filtres pour réduire l'espace de recherche"""
    
    filters = []
    if doc_types:
        filters.append(f"metadata->>'type' = ANY($1)")
    if date_range:
        filters.append(f"created_at BETWEEN $2 AND $3")
    
    where_clause = " AND ".join(filters) if filters else "TRUE"
    
    # Recherche seulement dans les chunks filtrés
    query = f"""
    SELECT * FROM match_chunks($1, $2, $3)
    WHERE {where_clause}
    """
```

## 🤖 Optimisations LLM

### Streaming Optimisé
```python
async def optimized_streaming_response(query: str) -> AsyncIterator[str]:
    """Streaming avec buffer pour réduire la latence"""
    
    buffer = ""
    buffer_size = 50  # Caractères
    
    async with agent.run_stream(query) as result:
        async for token in result.stream_text(delta=True):
            buffer += token
            
            # Flush buffer quand plein ou fin de phrase
            if len(buffer) >= buffer_size or token in '.!?':
                yield buffer
                buffer = ""
        
        # Flush buffer final
        if buffer:
            yield buffer
```

### Context Window Management
```python
def manage_context_window(
    query: str, 
    search_results: List[SearchResult],
    max_tokens: int = 4000
) -> str:
    """Gestion intelligente de la fenêtre de contexte"""
    
    context_parts = []
    token_count = len(query.split())  # Approximation
    
    for result in search_results:
        result_tokens = len(result.content.split())
        
        if token_count + result_tokens > max_tokens:
            # Tronquer le résultat si nécessaire
            available_tokens = max_tokens - token_count - 100  # Marge
            truncated = ' '.join(result.content.split()[:available_tokens])
            context_parts.append(f"Source: {result.document_title}\n{truncated}...")
            break
        
        context_parts.append(f"Source: {result.document_title}\n{result.content}")
        token_count += result_tokens
    
    return "\n\n".join(context_parts)
```

## 📊 Monitoring des Performances

### Métriques Clés
```python
import time
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    search_time: float
    embedding_time: float
    llm_response_time: float
    total_time: float
    results_count: int
    cache_hit_rate: float

async def measure_performance(query: str) -> PerformanceMetrics:
    start_time = time.time()
    
    # Mesurer chaque étape
    embed_start = time.time()
    query_embedding = await embed_query(query)
    embed_time = time.time() - embed_start
    
    search_start = time.time()
    results = await search_knowledge_base(query)
    search_time = time.time() - search_start
    
    llm_start = time.time()
    response = await generate_response(query, results)
    llm_time = time.time() - llm_start
    
    total_time = time.time() - start_time
    
    return PerformanceMetrics(
        search_time=search_time,
        embedding_time=embed_time,
        llm_response_time=llm_time,
        total_time=total_time,
        results_count=len(results),
        cache_hit_rate=get_cache_hit_rate()
    )
```

## 🎯 Recommandations par Charge

### Développement Local
- ChromaDB pour simplicité
- Modèles Ollama légers (llama3.2:1b)
- Cache en mémoire seulement

### Production Légère
- PostgreSQL + PGVector
- Pool de connexions (2-5)
- Cache disque persistant
- Modèles Ollama optimisés

### Production Intensive
- PostgreSQL avec réplication
- Pool de connexions (10-20)
- Cache Redis distribué
- GPU pour embeddings locaux
- Load balancer pour Ollama