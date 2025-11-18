# StudyRAG - Guide de Setup Automatique

Ce guide vous permet de configurer complètement StudyRAG en quelques minutes.

## 🚀 Setup Automatique (Recommandé)

### Windows (Installation complète depuis zéro)

#### Option 1: Script Batch (Le plus simple)
```cmd
# Clone du projet (si Git installé) ou télécharger le ZIP
git clone <votre-repo>
cd studyrag

# Double-clic sur setup.bat OU en ligne de commande:
setup.bat
```

#### Option 2: Script PowerShell (Plus de contrôle)
```powershell
# Ouvrir PowerShell en tant qu'administrateur
# Naviguer vers le dossier du projet
cd studyrag

# Exécuter le setup
.\setup.ps1

# Ou avec options
.\setup.ps1 -SkipPython  # Si Python déjà installé
```

### Linux/macOS

#### Option 1: Script Python (Recommandé)
```bash
# Clone du projet
git clone <votre-repo>
cd studyrag

# Lancement du setup automatique
python3 setup.py
```

#### Option 2: Script Bash (Alternative)
```bash
# Rendre le script exécutable
chmod +x setup.sh

# Lancement du setup
./setup.sh
```

## 📋 Ce que fait le setup automatique

### ✅ Windows (Installation complète)
- [x] Installation de Chocolatey (gestionnaire de paquets Windows)
- [x] Installation de Python 3.11 (si absent)
- [x] Installation de Git (si absent)
- [x] Installation de PostgreSQL 15 avec configuration automatique
- [x] Installation de UV (gestionnaire de dépendances Python)
- [x] Installation des dépendances Python via `uv sync`
- [x] Installation et configuration d'Ollama
- [x] Téléchargement du modèle LLM recommandé (llama3.2)

### ✅ Linux/macOS (Vérifications et installations)
- [x] Vérification des prérequis système (Python 3.9+, Git, Curl)
- [x] Installation automatique de UV (gestionnaire de dépendances)
- [x] Installation des dépendances Python via `uv sync`
- [x] Configuration PostgreSQL + PGVector
- [x] Installation et configuration d'Ollama
- [x] Téléchargement du modèle LLM recommandé (llama3.2)

### ⚙️ Configuration automatique
- [x] Création du fichier `.env` avec les bonnes variables
- [x] Création du schéma de base de données
- [x] Génération de documents d'exemple
- [x] Tests de vérification de l'installation

### 🎯 Résultat final
Après le setup, vous aurez un environnement StudyRAG complètement fonctionnel avec :
- Toutes les dépendances installées
- Base de données configurée
- Ollama opérationnel avec un modèle LLM
- Documents d'exemple prêts à tester

## 🔧 Setup Manuel (Si nécessaire)

Si le setup automatique échoue, voici les étapes manuelles :

### 1. Prérequis système
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip git curl postgresql postgresql-contrib

# macOS
brew install python git postgresql@15

# Vérifier les versions
python3 --version  # >= 3.9
git --version
psql --version
```

### 2. Installation UV
```bash
# Installation UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Ajouter au PATH (redémarrer le terminal ou)
export PATH="$HOME/.cargo/bin:$PATH"
```

### 3. Dépendances Python
```bash
# Dans le dossier du projet
uv sync

# Vérification
uv run python -c "import fastapi, asyncpg, rich; print('OK')"
```

### 4. Base de données PostgreSQL
```bash
# Créer la base de données
sudo -u postgres createdb studyrag
sudo -u postgres createuser studyrag

# Configurer le mot de passe
sudo -u postgres psql -c "ALTER USER studyrag PASSWORD 'password';"

# Créer le schéma
psql postgresql://studyrag:password@localhost:5432/studyrag -f sql/schema.sql
```

### 5. Installation Ollama
```bash
# Installation
curl -fsSL https://ollama.ai/install.sh | sh

# Démarrage du serveur
ollama serve &

# Téléchargement d'un modèle
ollama pull llama3.2
```

### 6. Configuration .env
```bash
# Copier et éditer
cp .env.example .env

# Éditer avec vos paramètres
nano .env
```

## 🧪 Vérification de l'installation

### Tests automatiques
```bash
# Test complet
python scripts/verify_implementation.py

# Tests individuels
python scripts/test_ollama_setup.py
python scripts/test_embedding_models.py
python scripts/test_chunking.py
```

### Test manuel rapide
```bash
# 1. Ingérer les documents d'exemple
uv run python -m ingestion.ingest --documents test_samples/

# 2. Lancer le CLI
uv run python cli.py

# 3. Poser une question test
# Dans le CLI: "Qu'est-ce que StudyRAG ?"
```

## 🐳 Alternative Docker

Si vous préférez Docker :

```bash
# Build et lancement
docker-compose up -d

# Ingestion via Docker
docker-compose --profile ingestion up ingestion

# Accès au CLI
docker-compose exec rag-agent python cli.py
```

## 🚨 Dépannage

### Problèmes courants

#### UV non trouvé après installation
```bash
# Ajouter au PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Ou redémarrer le terminal
```

#### PostgreSQL non accessible
```bash
# Vérifier le service
sudo systemctl status postgresql

# Démarrer si nécessaire
sudo systemctl start postgresql

# Créer la base manuellement
sudo -u postgres createdb studyrag
```

#### Ollama ne démarre pas
```bash
# Vérifier le processus
ps aux | grep ollama

# Redémarrer
pkill ollama
ollama serve &

# Tester la connexion
curl http://localhost:11434/api/tags
```

#### Erreurs de dépendances Python
```bash
# Nettoyer et réinstaller
uv sync --reinstall

# Vérifier l'environnement
uv run python -c "import sys; print(sys.path)"
```

### Logs et debug

#### Activer les logs détaillés
```bash
# Variables d'environnement pour debug
export PYTHONPATH=.
export LOG_LEVEL=DEBUG

# Lancer avec logs
uv run python cli.py
```

#### Fichiers de log utiles
- `~/.ollama/logs/server.log` - Logs Ollama
- Logs PostgreSQL dans `/var/log/postgresql/`
- Sortie console avec Rich pour les erreurs Python

## 📞 Support

### Informations à collecter en cas de problème
1. **Système** : `uname -a`
2. **Python** : `python3 --version`
3. **UV** : `uv --version`
4. **PostgreSQL** : `psql --version`
5. **Ollama** : `ollama --version`
6. **Variables d'env** : `env | grep -E "(DATABASE|OLLAMA|OPENAI)"`
7. **Logs d'erreur** : Stack trace complète

### Commandes de diagnostic
```bash
# Health check complet
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

# Test Ollama
curl -s http://localhost:11434/api/tags | jq '.models[].name'

# Stats base de données
psql $DATABASE_URL -c "
SELECT 
    COUNT(*) as total_documents,
    (SELECT COUNT(*) FROM chunks) as total_chunks,
    pg_size_pretty(pg_database_size(current_database())) as db_size;
"
```

## 🎉 Après le setup

Une fois le setup terminé avec succès :

1. **Première ingestion** : `uv run python -m ingestion.ingest --documents test_samples/`
2. **Lancer le CLI** : `uv run python cli.py`
3. **Tester une question** : "Qu'est-ce que StudyRAG ?"
4. **Explorer la documentation** : Dossier `docs/`

Bon apprentissage avec StudyRAG ! 🚀