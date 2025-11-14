---
inclusion: always
---

# Commandes Rapides StudyRAG

## 🚀 Démarrage Rapide

### Installation et Setup
```bash
# Clone et setup
git clone <repo>
cd studyrag
uv sync

# Configuration
cp .env.example .env
# Éditer .env avec tes paramètres

# Test rapide
python scripts/test_ollama_setup.py
```

### Première Ingestion
```bash
# Utiliser les échantillons
uv run python -m ingestion.ingest --documents test_samples/

# Ou tes propres documents
uv run python -m ingestion.ingest --documents documents/
```

### Lancement
```bash
# CLI interactif (recommandé)
uv run python cli.py

# Agent de base
uv run python rag_agent.py

# Interface web
uv run python main.py
```

## 🔧 Commandes de Développement

### Tests et Validation
```bash
# Test complet de l'implémentation
python scripts/verify_implementation.py

# Test des composants individuels
python scripts/test_ollama_setup.py      # Ollama
python scripts/test_embedding_models.py  # Embeddings
python scripts/test_chunking.py          # Chunking
python scripts/test_pdf_simple.py        # PDF processing

# Test d'évaluation
python scripts/test_evaluation.py
```

### Gestion des Dépendances
```bash
# Synchroniser les dépendances
uv sync

# Ajouter une nouvelle dépendance
uv add package-name

# Mettre à jour
uv sync --upgrade

# Voir l'arbre des dépendances
uv tree
```

### Base de Données
```bash
# Créer le schéma
psql $DATABASE_URL < sql/schema.sql

# Reset complet des données
python -c "
import asyncio, asyncpg
async def reset():
    conn = await asyncpg.connect('$DATABASE_URL')
    await conn.execute('TRUNCATE documents, chunks CASCADE')
    await conn.close()
asyncio.run(reset())
"

# Vérifier la connexion
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('$DATABASE_URL'))"
```

## 🧪 Tests et Debug

### Tests Rapides
```bash
# Test avec un document spécifique
python -c "
from ingestion.ingest import process_single_document
result = process_single_document('test_samples/test_document.pdf')
print(f'Processed: {result}')
"

# Test de recherche
python -c "
import asyncio
from rag_agent import search_knowledge_base
async def test():
    results = await search_knowledge_base('test query')
    print(f'Found {len(results)} results')
asyncio.run(test())
"
```

### Debug et Logs
```bash
# Logs détaillés
PYTHONPATH=. python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Ton code ici
"

# Avec Rich pour debug
python -c "
from rich.console import Console
console = Console()
try:
    # Ton code ici
    pass
except Exception:
    console.print_exception()
"
```

## 🔄 Maintenance

### Nettoyage
```bash
# Nettoyer les fichiers temporaires
rm -rf temp_files/processed_docs/
rm -rf temp_files/test_chroma/
rm -rf chroma_db/

# Nettoyer les caches Python
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### Mise à Jour des Embeddings
```bash
# Script de mise à jour
python scripts/upgrade_embeddings.py

# Re-ingestion complète
uv run python -m ingestion.ingest --documents documents/ --clear-existing
```

### Backup et Restore
```bash
# Backup PostgreSQL
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore
psql $DATABASE_URL < backup_20241112.sql

# Backup ChromaDB
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_db/
```

## 🐳 Docker

### Développement
```bash
# Build et run
docker-compose up -d

# Logs
docker-compose logs -f rag-agent

# Ingestion via Docker
docker-compose --profile ingestion up ingestion

# Shell dans le container
docker-compose exec rag-agent bash
```

### Production
```bash
# Build optimisé
docker build -t studyrag:prod .

# Run avec variables d'env
docker run -d \
  -e DATABASE_URL=$DATABASE_URL \
  -e OLLAMA_BASE_URL=$OLLAMA_BASE_URL \
  -p 8000:8000 \
  studyrag:prod
```

## 📊 Monitoring

### Health Checks
```bash
# Vérifier tous les services
python -c "
import asyncio
from utils.providers import validate_configuration
from utils.db_utils import check_db_health

async def health_check():
    db_ok = await check_db_health()
    config_ok = validate_configuration()
    print(f'DB: {\"✅\" if db_ok else \"❌\"}')
    print(f'Config: {\"✅\" if config_ok else \"❌\"}')

asyncio.run(health_check())
"

# Vérifier Ollama
curl -s http://localhost:11434/api/tags | jq '.models[].name'

# Stats base de données
psql $DATABASE_URL -c "
SELECT 
    COUNT(*) as total_documents,
    (SELECT COUNT(*) FROM chunks) as total_chunks,
    pg_size_pretty(pg_database_size(current_database())) as db_size;
"
```

### Performance
```bash
# Mesurer les temps de réponse
time python -c "
import asyncio
from rag_agent import search_knowledge_base
asyncio.run(search_knowledge_base('test query'))
"

# Profiling avec cProfile
python -m cProfile -o profile.stats scripts/test_chunking.py
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(10)
"
```

## 🎯 Raccourcis Utiles

### Variables d'Environnement Rapides
```bash
# Setup rapide pour développement local
export DATABASE_URL="postgresql://user:pass@localhost:5432/studyrag"
export OLLAMA_BASE_URL="http://localhost:11434"
export LLM_CHOICE="llama3.2"
```

### Aliases Bash Utiles
```bash
# Ajouter à ~/.bashrc
alias srag-cli="cd /path/to/studyrag && uv run python cli.py"
alias srag-ingest="cd /path/to/studyrag && uv run python -m ingestion.ingest"
alias srag-test="cd /path/to/studyrag && python scripts/verify_implementation.py"
```

### Scripts One-Liner
```bash
# Reset et re-ingestion complète
rm -rf chroma_db/ temp_files/ && uv run python -m ingestion.ingest --documents test_samples/

# Test rapide de bout en bout
python -c "
import asyncio
from cli import main
# Test automatisé
"
```