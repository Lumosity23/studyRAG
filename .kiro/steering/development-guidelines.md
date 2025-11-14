---
inclusion: always
---

# Guidelines de Développement StudyRAG

## 🛠️ Standards de Code

### Gestionnaire de Dépendances
- **TOUJOURS utiliser UV** : `uv add`, `uv sync`, `uv run`
- **JAMAIS pip** sauf cas exceptionnel documenté
- Dépendances dans `pyproject.toml` uniquement

### Structure des Imports
```python
# Ordre des imports
import os
import sys
from pathlib import Path

import asyncio
import asyncpg
from rich.console import Console

from utils.providers import get_ollama_client
from ingestion.embedder import create_embedder
```

### Gestion des Erreurs
```python
# Toujours gérer les erreurs Ollama/DB
try:
    result = await ollama_client.chat(...)
except Exception as e:
    console.print(f"[red]Erreur Ollama: {e}[/red]")
    # Fallback ou retry
```

## 🗄️ Base de Données

### PostgreSQL + PGVector
- **Connexions**: Utiliser `utils/db_utils.py` pour le pooling
- **Embeddings**: Dimension 1536 (OpenAI) ou selon modèle local
- **Schema**: Toujours utiliser `sql/schema.sql`

### ChromaDB (Alternative)
- **Collections**: Nommer clairement (`study_docs_v1`)
- **Métadonnées**: Inclure source, type, date
- **Persistence**: Configurer le chemin de stockage

## 🤖 Modèles et LLM

### Priorité Ollama (Local)
1. **Vérifier disponibilité Ollama** avant OpenAI
2. **Modèles recommandés** : `llama3.2`, `mistral`, `qwen2.5`
3. **Fallback OpenAI** seulement si Ollama indisponible

### Configuration Embeddings
```python
# Ordre de préférence
1. sentence-transformers (local)
2. Ollama embeddings
3. OpenAI embeddings (fallback)
```

## 📄 Traitement Documents

### Formats Supportés
- **PDF** : Priorité Docling > PyPDF2
- **Office** : Docling pour .docx, .pptx
- **Audio** : Whisper via Docling
- **Markdown/HTML** : Traitement direct

### Chunking Strategy
```python
# Paramètres recommandés
chunk_size = 1000  # tokens
overlap = 200      # tokens
method = "semantic"  # ou "fixed"
```

## 🧪 Tests et Validation

### Fichiers de Test
- **Utiliser `test_samples/`** pour tous les tests
- **Formats variés** : PDF, DOCX, HTML, MD
- **Tailles différentes** : petit, moyen, grand document

### Scripts de Test
```bash
# Lancer depuis la racine
python scripts/test_chunking.py
python scripts/test_embedding_models.py
python scripts/verify_implementation.py
```

## 🔧 Debugging et Logs

### Rich Console
```python
from rich.console import Console
console = Console()

# Messages colorés
console.print("[green]✅ Succès[/green]")
console.print("[red]❌ Erreur[/red]")
console.print("[yellow]⚠️ Attention[/yellow]")
```

### Logs Structurés
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

## 🚀 Déploiement

### Docker
- **Base image** : Python 3.11-slim
- **Multi-stage** : Build + Runtime
- **Health checks** : Inclure vérification DB/Ollama

### Variables d'Environnement
```bash
# Obligatoires
DATABASE_URL=postgresql://...
OLLAMA_BASE_URL=http://localhost:11434

# Optionnelles
OPENAI_API_KEY=sk-...
LLM_CHOICE=llama3.2
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```