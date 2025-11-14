# Organisation du Projet

Ce document décrit l'organisation du projet après le nettoyage et la restructuration.

## 🎯 Objectif

Créer une structure claire et logique pour faciliter la navigation et la maintenance du projet.

## 📁 Structure Organisée

### Fichiers Principaux (Racine)
- `cli.py` - Interface en ligne de commande principale
- `rag_agent.py` - Agent RAG de base
- `main.py` - Point d'entrée principal
- `chat_rag.py` - Implémentation du chat RAG
- `pyproject.toml` - Configuration et dépendances du projet
- `README.md` - Documentation principale

### Dossiers Organisés

#### 📚 `docs/` - Documentation
- `architecture/` - Documentation technique et guides d'architecture
- `tasks/` - Résumés d'implémentation des tâches (TASK_4 à TASK_14)
- `ui/` - Documentation interface utilisateur et configuration Kiro

#### 🔧 `scripts/` - Scripts et Utilitaires
- Scripts de test (`test_*.py`)
- Scripts utilitaires (`run_test.py`, `verify_implementation.py`, etc.)
- Scripts d'ingestion et de recherche

#### 🧪 `test_samples/` - Échantillons de Test
- Fichiers d'exemple pour tester différents formats
- Documents de test (PDF, Word, HTML, Markdown)

#### 📦 `archive/` - Fichiers Archivés
- `requirements.txt` (remplacé par pyproject.toml)
- `migrate_to_monorepo.sh`
- `api_openapi_spec.json`

#### 🗂️ `temp_files/` - Fichiers Temporaires
- `processed_docs/` - Documents traités
- `test_chroma/` - Base de données ChromaDB de test

### Dossiers Fonctionnels (Inchangés)
- `ingestion/` - Pipeline d'ingestion de documents
- `utils/` - Modules utilitaires
- `sql/` - Schémas de base de données
- `app/` - Application web
- `static/` - Fichiers statiques
- `documents/` - Documents pour ingestion
- `docling_basics/` - Exemples tutoriels Docling
- `examples/` - Exemples d'utilisation
- `tests/` - Tests unitaires et d'intégration

## 🧹 Nettoyage Effectué

### Fichiers Déplacés
- ✅ Documentation éparpillée → `docs/`
- ✅ Scripts de test → `scripts/`
- ✅ Fichiers d'exemple → `test_samples/`
- ✅ Fichiers obsolètes → `archive/`
- ✅ Fichiers temporaires → `temp_files/`

### Fichiers Supprimés/Consolidés
- ✅ Dossiers vides supprimés (`uploads/`)
- ✅ `requirements.txt` archivé (remplacé par `pyproject.toml`)
- ✅ Dossiers de test consolidés

### Améliorations
- ✅ `.gitignore` créé pour éviter les fichiers temporaires
- ✅ README.md mis à jour avec la nouvelle structure
- ✅ Documentation ajoutée dans chaque dossier organisé

## 🚀 Avantages de la Nouvelle Organisation

1. **Clarté** - Structure logique et intuitive
2. **Maintenance** - Fichiers groupés par fonction
3. **Navigation** - Plus facile de trouver ce qu'on cherche
4. **Développement** - Séparation claire entre code, tests, et documentation
5. **Collaboration** - Structure standardisée pour l'équipe

## 📖 Prochaines Étapes

1. Vérifier que tous les imports fonctionnent encore
2. Mettre à jour les chemins dans les scripts si nécessaire
3. Tester l'application pour s'assurer que tout fonctionne
4. Documenter les nouvelles conventions dans l'équipe