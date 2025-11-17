# StudyRAG 🎓

**Agent RAG local intelligent pour étudiants** - Système de génération augmentée par récupération utilisant Docling pour le traitement de documents, embeddings locaux, base de données vectorielle et Ollama pour les conversations IA.

## ✨ Fonctionnalités

- 🤖 **Agent conversationnel local** avec Ollama (pas besoin d'OpenAI)
- 📄 **Traitement multi-format** avec Docling (PDF, Word, PowerPoint, Excel, HTML, Audio)
- 🔍 **Recherche sémantique** dans vos documents avec embeddings
- 💾 **Base vectorielle** (ChromaDB + PostgreSQL/PGVector)
- 🌐 **Interface web moderne** (React/Next.js) + CLI
- 🎙️ **Transcription audio** avec Whisper
- 📚 **Citations sources** pour toutes les réponses
- 🔄 **Streaming en temps réel** des réponses
- 🏠 **100% local** - vos données restent privées

## 🚀 Démarrage Ultra-Rapide

### Prérequis
- **Python 3.9+** avec [UV](https://docs.astral.sh/uv/) installé
- **Node.js 18+** et npm (pour l'interface web)
- **Ollama** installé et en cours d'exécution ([Installation Ollama](https://ollama.ai/))

### Installation en 30 secondes

```bash
# 1. Cloner le projet
git clone <votre-repo>
cd studyrag

# 2. Démarrage automatique (backend + frontend)
python start.py
# OU
./start.sh
```

**C'est tout!** 🎉 Le script fait automatiquement:
- ✅ Installation des dépendances Python et Node.js
- ✅ Configuration de l'environnement (.env)
- ✅ Démarrage du backend FastAPI
- ✅ Démarrage du frontend React
- ✅ Vérification des services

### Accès rapide
- 🌐 **Interface web**: http://localhost:3000
- 🔧 **API Backend**: http://localhost:8000
- 📚 **Documentation**: http://localhost:8000/docs
- ❤️ **Health Check**: http://localhost:8000/health

## 🛠️ Configuration Manuelle (Optionnelle)

Si vous préférez configurer manuellement:

### 1. Variables d'environnement
```bash
cp .env.example .env
# Éditez .env selon vos besoins
```

Variables principales:
- `OLLAMA_BASE_URL` - URL d'Ollama (défaut: http://localhost:11434)
- `LLM_CHOICE` - Modèle Ollama (défaut: llama3.2)
- `DATABASE_URL` - Base de données (SQLite par défaut pour les tests)
- `EMBEDDING_MODEL` - Modèle d'embeddings local

### 2. Installer Ollama et modèles
```bash
# Installer Ollama (si pas déjà fait)
curl -fsSL https://ollama.ai/install.sh | sh

# Démarrer Ollama
ollama serve

# Installer des modèles (dans un autre terminal)
ollama pull llama3.2        # Modèle principal recommandé
ollama pull mistral         # Alternative
ollama pull qwen2.5:7b      # Pour plus de performance
```

### 3. Ingestion de documents

Ajoutez vos documents dans le dossier `documents/` ou `test_samples/`:

**Formats supportés via Docling:**
- 📄 **PDF** (`.pdf`)
- 📝 **Word** (`.docx`, `.doc`) 
- 📊 **PowerPoint** (`.pptx`, `.ppt`)
- 📈 **Excel** (`.xlsx`, `.xls`)
- 🌐 **HTML** (`.html`, `.htm`)
- 📋 **Markdown** (`.md`)
- 📃 **Texte** (`.txt`)
- 🎵 **Audio** (`.mp3`) - transcription avec Whisper

```bash
# Ingestion automatique
uv run python -m ingestion.ingest --documents documents/

# Avec paramètres personnalisés
uv run python -m ingestion.ingest --documents test_samples/ --chunk-size 800
```

### 4. Utilisation

**Interface Web (Recommandée)**
- Ouvrez http://localhost:3000
- Interface moderne avec chat, upload de fichiers, gestion des documents

**CLI Interactif**
```bash
uv run python cli.py
```

**API REST**
- Documentation: http://localhost:8000/docs
- Endpoints: `/api/v1/chat`, `/api/v1/documents`, `/api/v1/search`

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  React Frontend │────▶│   FastAPI        │────▶│   ChromaDB      │
│  (Next.js)      │     │   Backend        │     │   + PostgreSQL  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                        ┌──────┴──────┐
                        │             │
                  ┌─────▼────┐  ┌────▼─────────┐
                  │  Ollama  │  │ Sentence     │
                  │   LLM    │  │ Transformers │
                  │ (Local)  │  │ (Embeddings) │
                  └──────────┘  └──────────────┘
                        │
                  ┌─────▼────┐
                  │ Docling  │
                  │Document  │
                  │Processing│
                  └──────────┘
```

### Stack Technique
- **Frontend**: React/Next.js avec Tailwind CSS
- **Backend**: FastAPI avec PydanticAI
- **LLM**: Ollama (modèles locaux)
- **Embeddings**: Sentence Transformers (local)
- **Base vectorielle**: ChromaDB + PostgreSQL/PGVector
- **Traitement docs**: Docling + Whisper
- **Déploiement**: Docker + Docker Compose

## 🎙️ Transcription Audio

Les fichiers audio sont automatiquement transcrits avec **Whisper** via Docling:

**Fonctionnement:**
1. Déposez des fichiers MP3 dans `documents/`
2. Docling utilise Whisper pour la transcription
3. Le texte est indexé et devient recherchable
4. Citations avec timestamps dans les réponses

**Avantages:**
- 🎙️ **Speech-to-text**: Podcasts, interviews, cours → texte recherchable
- ⏱️ **Timestamps**: Localisation précise du contenu
- 🔍 **Recherche sémantique**: Trouvez du contenu audio par sujet
- 🤖 **100% automatique**: Glissez-déposez et c'est parti

**Exemple de transcription:**
```markdown
[time: 0.0-4.0] Bienvenue dans ce podcast sur l'IA et l'apprentissage automatique.
[time: 5.28-9.96] Aujourd'hui nous discuterons des systèmes RAG.
```

## 🧩 Composants Clés

### Agent RAG Principal
- **`rag_agent.py`**: Agent conversationnel avec PydanticAI
- **`cli.py`**: Interface en ligne de commande interactive
- **`app/main.py`**: API FastAPI pour l'interface web

### Pipeline d'Ingestion
- **`ingestion/`**: Traitement automatique des documents
- **Docling**: Conversion multi-format (PDF, Office, HTML, Audio)
- **Chunking intelligent**: Découpage sémantique optimisé
- **Embeddings locaux**: Sentence Transformers

### Base de Données
- **ChromaDB**: Base vectorielle simple pour les tests
- **PostgreSQL + PGVector**: Base vectorielle scalable
- **SQLite**: Option légère pour le développement

### Interface Web
- **Frontend React**: Interface moderne et intuitive
- **Upload de fichiers**: Glisser-déposer direct
- **Chat en temps réel**: Streaming des réponses
- **Gestion des documents**: Visualisation et organisation

## ⚡ Optimisations

### Performance
- **Cache des embeddings**: Réduction des calculs répétitifs
- **Pool de connexions**: Gestion optimisée de la base de données
- **Streaming**: Réponses en temps réel token par token
- **Chunking adaptatif**: Taille optimisée selon le type de document

### Sécurité et Confidentialité
- **100% local**: Aucune donnée envoyée vers des services externes
- **Ollama local**: LLM qui tourne sur votre machine
- **Embeddings locaux**: Sentence Transformers sans API
- **Données privées**: Vos documents restent sur votre système

## 🐳 Déploiement Docker

### Démarrage avec Docker Compose

```bash
# Démarrer tous les services
docker-compose up -d

# Ingestion de documents
docker-compose --profile ingestion up ingestion

# Voir les logs
docker-compose logs -f rag-agent
```

### Déploiement Production
```bash
# Build optimisé
docker build -t studyrag:prod .

# Lancement avec variables d'environnement
docker run -d \
  -e OLLAMA_BASE_URL=http://ollama:11434 \
  -e DATABASE_URL=postgresql://... \
  -p 8000:8000 \
  studyrag:prod
```

## 📚 Tutoriels et Exemples

### 🎓 Nouveau avec Docling?

**Commencez par les tutoriels!** Consultez le dossier [`docling_basics/`](./docling_basics/) pour des exemples progressifs:

1. **Conversion PDF simple** - Traitement de base des documents
2. **Support multi-format** - PDF, Word, PowerPoint
3. **Transcription audio** - Speech-to-text avec Whisper
4. **Chunking hybride** - Découpage intelligent pour RAG

### API REST

**Endpoints principaux:**
- `POST /api/v1/chat` - Conversation avec l'agent
- `POST /api/v1/documents/upload` - Upload de documents
- `GET /api/v1/documents` - Liste des documents
- `POST /api/v1/search` - Recherche sémantique
- `GET /health` - Statut des services

**Documentation complète:** http://localhost:8000/docs

## 📁 Structure du Projet

```
studyrag/
├── start.py                 # 🚀 Script de démarrage automatique
├── start.sh                 # 🚀 Script bash alternatif
├── cli.py                   # 💬 Interface CLI interactive
├── rag_agent.py             # 🤖 Agent RAG principal
├── main.py                  # 📄 Point d'entrée legacy
├── app/                     # 🌐 Backend FastAPI
│   ├── main.py              # API principale
│   ├── api/                 # Endpoints REST
│   ├── core/                # Configuration et middleware
│   ├── models/              # Modèles de données
│   └── services/            # Services métier
├── frontend/                # ⚛️ Interface React/Next.js
│   ├── src/                 # Code source React
│   ├── components/          # Composants UI
│   ├── pages/               # Pages Next.js
│   └── package.json         # Dépendances Node.js
├── ingestion/               # 📥 Pipeline d'ingestion
│   ├── ingest.py            # Script principal
│   ├── embedder.py          # Génération d'embeddings
│   └── chunker.py           # Découpage de documents
├── utils/                   # 🔧 Modules utilitaires
│   ├── providers.py         # Configuration Ollama/modèles
│   ├── db_utils.py          # Gestion base de données
│   └── models.py            # Modèles Pydantic
├── documents/               # 📚 Vos documents à traiter
├── test_samples/            # 📋 Fichiers d'exemple
├── docling_basics/          # 🎓 Tutoriels Docling
├── scripts/                 # 🧪 Scripts de test et debug
├── docs/                    # 📖 Documentation
├── sql/                     # 🗄️ Schémas base de données
├── pyproject.toml           # 📦 Configuration Python/UV
├── docker-compose.yml       # 🐳 Déploiement Docker
└── README.md                # 📄 Ce fichier
```

## 🤝 Contribution

1. Fork le projet
2. Créez votre branche (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🆘 Support

- 📖 **Documentation**: Consultez le dossier `docs/`
- 🐛 **Issues**: Ouvrez une issue sur GitHub
- 💬 **Discussions**: Utilisez les GitHub Discussions
- 📧 **Contact**: [votre-email]

---

**StudyRAG** - Votre assistant IA local pour l'apprentissage et la recherche documentaire 🎓✨