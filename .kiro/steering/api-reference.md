---
inclusion: fileMatch
fileMatchPattern: "*.py"
---

# Référence API StudyRAG

## 🔧 Modules Principaux

### `utils/providers.py`
```python
# Configuration des modèles et clients
get_ollama_client() -> ollama.AsyncClient
get_llm_model() -> str  # Retourne le modèle LLM configuré
get_embedding_model() -> str  # Retourne le modèle d'embedding
validate_configuration() -> bool  # Valide la config complète
get_model_info(model_name: str) -> dict  # Info sur un modèle
```

### `utils/db_utils.py`
```python
# Gestion des connexions base de données
create_db_pool() -> asyncpg.Pool  # Pool de connexions PostgreSQL
get_db_connection() -> asyncpg.Connection  # Connexion unique
execute_query(query: str, *args) -> Any  # Exécution requête
```

### `ingestion/embedder.py`
```python
# Génération d'embeddings
create_embedder() -> Embedder  # Factory pour embedder
embed_text(text: str) -> List[float]  # Embedding d'un texte
embed_batch(texts: List[str]) -> List[List[float]]  # Batch embeddings
```

### `ingestion/chunker.py`
```python
# Découpage de documents
chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]
semantic_chunking(text: str) -> List[str]  # Chunking sémantique
get_chunk_metadata(chunk: str, doc_info: dict) -> dict
```

## 📊 Modèles de Données

### Document
```python
@dataclass
class Document:
    id: str
    title: str
    source: str
    content: str
    metadata: dict
    created_at: datetime
    updated_at: datetime
```

### Chunk
```python
@dataclass
class Chunk:
    id: str
    document_id: str
    content: str
    embedding: List[float]
    chunk_index: int
    metadata: dict
    token_count: int
```

### SearchResult
```python
@dataclass
class SearchResult:
    chunk_id: str
    content: str
    similarity: float
    document_title: str
    document_source: str
    metadata: dict
```

## 🔍 Fonctions de Recherche

### `search_knowledge_base()`
```python
async def search_knowledge_base(
    query: str,
    limit: int = 5,
    similarity_threshold: float = 0.7
) -> List[SearchResult]:
    """
    Recherche sémantique dans la base de connaissances
    
    Args:
        query: Requête de recherche
        limit: Nombre max de résultats
        similarity_threshold: Seuil de similarité (0-1)
    
    Returns:
        Liste des résultats triés par pertinence
    """
```

### Fonction SQL `match_chunks()`
```sql
-- Recherche vectorielle avec PGVector
SELECT * FROM match_chunks(
    query_embedding::vector(1536),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.7
);
```

## 🤖 Agent RAG

### Configuration PydanticAI
```python
from pydantic_ai import Agent

agent = Agent(
    model='ollama:llama3.2',  # Modèle local prioritaire
    deps_type=None,
    system_prompt="Tu es un assistant...",
    tools=[search_knowledge_base]  # Outil de recherche
)
```

### Utilisation
```python
# Conversation simple
response = await agent.run("Ma question")

# Avec streaming
async with agent.run_stream("Ma question") as result:
    async for text in result.stream_text():
        print(text, end="", flush=True)

# Avec historique
history = []
response = await agent.run("Question", message_history=history)
```

## 📄 Pipeline d'Ingestion

### Workflow Complet
```python
# 1. Conversion avec Docling
converter = DocumentConverter()
doc = converter.convert("document.pdf")

# 2. Extraction du contenu
content = doc.document.export_to_markdown()

# 3. Chunking
chunks = chunk_text(content, chunk_size=1000)

# 4. Génération embeddings
embedder = create_embedder()
embeddings = [embedder.embed(chunk) for chunk in chunks]

# 5. Stockage en base
await store_document_and_chunks(doc_info, chunks, embeddings)
```

## 🎯 Formats Supportés

### Docling Auto-Detection
```python
supported_formats = {
    '.pdf': 'PDF documents',
    '.docx': 'Word documents', 
    '.pptx': 'PowerPoint presentations',
    '.xlsx': 'Excel spreadsheets',
    '.html': 'HTML files',
    '.md': 'Markdown files',
    '.txt': 'Plain text',
    '.mp3': 'Audio files (via Whisper)'
}
```

## 🔧 Configuration

### Variables d'Environnement
```python
# Obligatoires
DATABASE_URL: str  # PostgreSQL avec PGVector
OLLAMA_BASE_URL: str = "http://localhost:11434"

# Optionnelles
OPENAI_API_KEY: str = None  # Fallback embeddings
LLM_CHOICE: str = "llama3.2"
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 200
```

## 🚀 Points d'Entrée

### CLI Principal
```bash
# Interface interactive
uv run python cli.py

# Agent de base
uv run python rag_agent.py

# Interface web
uv run python main.py
```

### Ingestion
```bash
# Ingestion complète
uv run python -m ingestion.ingest --documents documents/

# Avec paramètres
uv run python -m ingestion.ingest \
    --documents test_samples/ \
    --chunk-size 800 \
    --clear-existing
```