---
inclusion: always
---

# StudyRAG - Vue d'ensemble du projet

## 🎯 Objectif Principal
StudyRAG est un agent RAG (Retrieval Augmented Generation) local conçu pour les étudiants, utilisant Docling pour le traitement de documents et Ollama pour l'inférence locale.

## 🏗️ Architecture Technique

### Stack Principal
- **Backend**: Python 3.9+ avec FastAPI
- **LLM Local**: Ollama (modèles locaux)
- **Embeddings**: Sentence Transformers / OpenAI
- **Base de données vectorielle**: ChromaDB + PostgreSQL avec PGVector
- **Traitement documents**: Docling (PDF, Word, PowerPoint, HTML, Audio)
- **Interface**: CLI avec Rich + Interface web optionnelle

### Composants Clés
- **Agent RAG**: `rag_agent.py` - Agent principal avec PydanticAI
- **CLI**: `cli.py` - Interface en ligne de commande améliorée
- **Ingestion**: `ingestion/` - Pipeline de traitement des documents
- **Utils**: `utils/` - Modules utilitaires (DB, providers, modèles)

## 📁 Structure du Projet
```
├── cli.py, rag_agent.py, main.py     # Code principal
├── ingestion/                        # Pipeline d'ingestion
├── utils/                           # Modules utilitaires
├── docs/                            # Documentation organisée
├── scripts/                         # Tests et utilitaires
├── test_samples/                    # Fichiers d'exemple
└── app/                            # Interface web (optionnelle)
```

## 🔧 Configuration Importante
- **Variables d'environnement**: `.env` (DATABASE_URL, OPENAI_API_KEY optionnelle)
- **Dépendances**: `pyproject.toml` avec UV comme gestionnaire
- **Base de données**: PostgreSQL avec extension PGVector
- **Modèles**: Configuration dans `utils/providers.py`

## 🎓 Contexte Éducatif
Ce projet est conçu pour aider les étudiants à :
- Traiter et indexer leurs documents de cours
- Poser des questions sur leur contenu
- Obtenir des réponses avec citations sources
- Utiliser des modèles locaux (confidentialité)

## 🚨 Points d'Attention pour Kiro
- Toujours privilégier les solutions locales (Ollama vs OpenAI)
- Respecter la structure organisée récemment mise en place
- Tester avec les fichiers dans `test_samples/`
- Utiliser UV pour la gestion des dépendances
- Maintenir la compatibilité avec les tutoriels `docling_basics/`