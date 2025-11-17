# StudyRAG - Démarrage Ultra-Rapide ⚡

## 🚀 En 30 secondes

```bash
# 1. Cloner et entrer dans le projet
git clone <votre-repo>
cd studyrag

# 2. Setup automatique complet
python dev-setup.py

# 3. Démarrage immédiat
python start.py
```

**C'est tout!** Votre StudyRAG est prêt à l'adresse http://localhost:3000

## 🎯 Démarrage Express (si vous êtes pressé)

```bash
# Installation minimale
uv sync
cp .env.example .env

# Démarrage backend seulement
uv run uvicorn app.main:app --reload --port 8000

# Dans un autre terminal - frontend
cd frontend && npm install && npm run dev
```

## 🔧 Configuration Manuelle Rapide

### 1. Prérequis (5 min)
```bash
# Installer UV (gestionnaire Python)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve  # Dans un terminal séparé
ollama pull llama3.2  # Modèle recommandé
```

### 2. Variables d'environnement (2 min)
```bash
cp .env.example .env
# Éditez .env si nécessaire (optionnel pour les tests)
```

### 3. Installation (3 min)
```bash
# Backend
uv sync

# Frontend (si vous voulez l'interface web)
cd frontend && npm install && cd ..
```

### 4. Test rapide (1 min)
```bash
# Ajouter un document test
echo "# Test\nCeci est un document de test pour StudyRAG." > documents/test.md

# Ingestion
uv run python -m ingestion.ingest --documents documents/

# Test CLI
uv run python cli.py
```

## 🎓 Premiers pas

### Ajouter vos documents
```bash
# Formats supportés: PDF, Word, PowerPoint, Excel, HTML, Markdown, Audio
cp vos-documents.pdf documents/
cp cours.docx documents/
cp presentation.pptx documents/

# Ingestion
uv run python -m ingestion.ingest --documents documents/
```

### Utilisation
```bash
# Interface web (recommandée)
python start.py
# Puis ouvrir http://localhost:3000

# CLI interactif
uv run python cli.py

# API seulement
uv run uvicorn app.main:app --reload
# Documentation: http://localhost:8000/docs
```

## 🐳 Avec Docker (Alternative)

```bash
# Tout en un
docker-compose up -d

# Ingestion
docker-compose --profile ingestion up ingestion
```

## 🆘 Dépannage Express

### Ollama ne démarre pas
```bash
# Vérifier l'installation
ollama --version

# Démarrer manuellement
ollama serve

# Tester
curl http://localhost:11434/api/tags
```

### Erreur de dépendances
```bash
# Réinstaller
uv sync --reinstall

# Ou avec pip en fallback
pip install -r requirements.txt  # Si vous avez ce fichier
```

### Base de données
```bash
# SQLite par défaut (aucune config requise)
# Pour PostgreSQL, voir la documentation complète
```

### Frontend ne démarre pas
```bash
cd frontend
npm install --force
npm run dev
```

## 📚 Ressources

- **Documentation complète**: `README.md`
- **Tutoriels Docling**: `docling_basics/`
- **Scripts de test**: `scripts/`
- **Exemples**: `test_samples/`

## 🎯 Commandes Essentielles

```bash
# Démarrage complet
python start.py

# Setup développement
python dev-setup.py

# CLI seulement
uv run python cli.py

# Ingestion documents
uv run python -m ingestion.ingest --documents documents/

# Tests
python scripts/verify_implementation.py

# Docker
docker-compose up -d
```

---

**Besoin d'aide?** Consultez le README.md complet ou ouvrez une issue! 🚀