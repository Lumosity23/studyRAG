# Scripts et Utilitaires

Ce dossier contient tous les scripts de test, de développement et utilitaires du projet.

## Scripts de test

- `test_*.py` - Scripts de test pour différents composants :
  - `test_chunking.py` - Test du système de chunking
  - `test_embedding_models.py` - Test des modèles d'embedding
  - `test_evaluation.py` - Test d'évaluation du système
  - `test_ollama_setup.py` - Test de la configuration Ollama
  - `test_pdf_simple.py` - Test simple de traitement PDF
  - `test_simple_export.py` - Test d'export simple
  - `test_ui_manual.py` - Test manuel de l'interface

## Scripts utilitaires

- `run_test.py` - Script principal pour lancer les tests
- `verify_implementation.py` - Vérification de l'implémentation
- `upgrade_embeddings.py` - Mise à jour des embeddings
- `ingest_simple.py` - Ingestion simple de documents
- `hybrid_search.py` - Recherche hybride

## Usage

```bash
# Lancer les tests
python scripts/run_test.py

# Vérifier l'implémentation
python scripts/verify_implementation.py

# Tester un composant spécifique
python scripts/test_chunking.py
```