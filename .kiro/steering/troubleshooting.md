---
inclusion: always
---

# Guide de Dépannage StudyRAG

## 🚨 Problèmes Fréquents et Solutions

### 1. Erreurs de Connexion Base de Données

#### Symptômes
```
asyncpg.exceptions.ConnectionDoesNotExistError
Could not connect to PostgreSQL
```

#### Solutions
```bash
# Vérifier la variable DATABASE_URL
echo $DATABASE_URL

# Tester la connexion
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('$DATABASE_URL'))"

# Vérifier PGVector
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 2. Ollama Non Disponible

#### Symptômes
```
ConnectionError: Ollama server not reachable
Model not found
```

#### Solutions
```bash
# Vérifier le service Ollama
curl http://localhost:11434/api/tags

# Démarrer Ollama
ollama serve

# Installer un modèle
ollama pull llama3.2
ollama pull mistral
```

### 3. Erreurs d'Ingestion Documents

#### Symptômes
```
UnsupportedFileTypeException
Docling conversion failed
```

#### Solutions
```python
# Vérifier les formats supportés
supported_formats = ['.pdf', '.docx', '.pptx', '.html', '.md', '.txt', '.mp3']

# Test avec fichier simple
python scripts/test_pdf_simple.py

# Utiliser les échantillons
python -m ingestion.ingest --documents test_samples/
```

### 4. Problèmes d'Embeddings

#### Symptômes
```
OpenAI API key not found
Embedding dimension mismatch
```

#### Solutions
```python
# Ordre de fallback
1. sentence-transformers (local) ✅
2. Ollama embeddings
3. OpenAI (avec clé API)

# Test embeddings
python scripts/test_embedding_models.py
```

### 5. Erreurs de Chunking

#### Symptômes
```
Chunk too large
Token count exceeded
```

#### Solutions
```python
# Ajuster les paramètres
chunk_size = 800  # Réduire si trop grand
overlap = 100     # Réduire l'overlap
max_tokens = 1000 # Limite stricte
```

## 🔧 Commandes de Diagnostic

### Vérification Complète
```bash
# Test de l'implémentation
python scripts/verify_implementation.py

# Test des composants
python scripts/test_ollama_setup.py
python scripts/test_chunking.py
```

### Logs de Debug
```python
# Activer les logs détaillés
import logging
logging.basicConfig(level=logging.DEBUG)

# Rich console pour debug
from rich.console import Console
console = Console()
console.print_exception()  # Affiche la stack trace colorée
```

### Nettoyage des Données
```bash
# Nettoyer ChromaDB
rm -rf chroma_db/

# Nettoyer les fichiers temporaires
rm -rf temp_files/processed_docs/
rm -rf temp_files/test_chroma/
```

## 🩺 Health Checks

### Base de Données
```python
async def check_db_health():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        return result == 1
    except Exception:
        return False
```

### Ollama
```python
async def check_ollama_health():
    try:
        client = get_ollama_client()
        models = await client.list()
        return len(models.get('models', [])) > 0
    except Exception:
        return False
```

### Embeddings
```python
def check_embeddings_health():
    try:
        embedder = create_embedder()
        test_embedding = embedder.embed("test")
        return len(test_embedding) > 0
    except Exception:
        return False
```

## 🔄 Procédures de Récupération

### Reset Complet
```bash
# 1. Nettoyer les données
rm -rf chroma_db/ temp_files/

# 2. Réinstaller les dépendances
uv sync --reinstall

# 3. Recréer le schéma DB
psql $DATABASE_URL < sql/schema.sql

# 4. Re-ingérer les documents
uv run python -m ingestion.ingest --documents test_samples/
```

### Reset Partiel (Données seulement)
```bash
# Nettoyer seulement les données
python -c "
import asyncio
import asyncpg
async def reset():
    conn = await asyncpg.connect('$DATABASE_URL')
    await conn.execute('TRUNCATE documents, chunks CASCADE')
    await conn.close()
asyncio.run(reset())
"
```

## 📞 Escalade des Problèmes

### Informations à Collecter
1. **Version Python** : `python --version`
2. **Dépendances** : `uv tree`
3. **Variables d'env** : `env | grep -E "(DATABASE|OLLAMA|OPENAI)"`
4. **Logs d'erreur** : Stack trace complète
5. **Fichier testé** : Type, taille, source

### Fichiers de Log Utiles
- `~/.ollama/logs/server.log`
- Logs PostgreSQL
- Sortie console avec Rich
- Fichiers dans `temp_files/`