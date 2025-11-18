# StudyRAG - Assistant d'Étude IA Local 🎓

StudyRAG est un assistant d'étude personnel utilisant l'intelligence artificielle **100% locale**. Il vous permet de poser des questions sur vos documents de cours (PDF, Word, PowerPoint, etc.) et obtenir des réponses précises avec citations, le tout sans jamais envoyer vos données vers des services externes.

> **Basé sur le travail de [Cole Medin](https://github.com/coleam00/ottomator-agents/tree/main/docling-rag-agent)** - Merci pour l'inspiration et le code de base ! 🙏

## 🎯 Pourquoi StudyRAG ?

- **🔒 Confidentialité totale** : Vos documents restent sur votre machine
- **🚀 IA locale** : Utilise Ollama (pas besoin de clé API)
- **📚 Multi-formats** : PDF, Word, PowerPoint, HTML, Audio
- **💬 Interface simple** : CLI interactif ou interface web
- **🎯 Citations précises** : Références exactes avec numéros de page

## 🚀 Installation Ultra-Rapide

### 🪟 Windows (Débutant complet)

**Vous n'avez RIEN d'installé ?** Pas de problème !

1. **Télécharger le projet** (ZIP depuis GitHub)
2. **Double-cliquer sur `setup.bat`**
3. **Attendre 30-45 minutes** ☕

Le script installe automatiquement :
- Python 3.11
- PostgreSQL 15  
- Git
- Ollama + modèle IA
- Toutes les dépendances

```cmd
# Ou en ligne de commande
setup.bat
```

**Plus de détails** : Voir `README_WINDOWS.md`

### 🐧 Linux/macOS (Développeur)

```bash
# Clone du projet
git clone https://github.com/Lumosity23/studyRAG.git
cd studyRAG

# Setup automatique (installe tout)
python3 setup.py

# Ou version bash
chmod +x setup.sh && ./setup.sh
```

**Plus de détails** : Voir `SETUP.md`

## 🎮 Première Utilisation

### 1. Ingérer vos documents
```bash
# Tester avec les exemples fournis
uv run python -m ingestion.ingest --documents test_samples/

# Ou avec vos propres documents
uv run python -m ingestion.ingest --documents documents/
```

### 2. Lancer l'assistant
```bash
# Interface CLI interactive (recommandé)
uv run python cli.py

# Ou interface web
uv run python main.py  # Puis aller sur http://localhost:8000
```

### 3. Poser votre première question
```
Vous: Qu'est-ce que StudyRAG ?
Assistant: StudyRAG est un assistant d'étude personnel utilisant l'IA locale...
[Source: welcome.md, page 1]
```

## 🛠️ Ce qui est installé

### 🤖 Intelligence Artificielle
- **Ollama** : Serveur IA local (pas de clé API nécessaire)
- **Modèle llama3.2** : IA conversationnelle (2GB)
- **Embeddings locaux** : Recherche sémantique dans vos documents

### 🗄️ Base de Données
- **PostgreSQL** : Stockage des documents et métadonnées
- **PGVector** : Recherche vectorielle haute performance
- **Configuration automatique** : Base `studyrag` prête à l'emploi

### 📄 Traitement Documents
- **Docling** : Extraction PDF, Word, PowerPoint avancée
- **Whisper** : Transcription audio automatique
- **Chunking intelligent** : Découpage optimal des documents

## 🎯 Formats Supportés

| Type | Formats | Traitement |
|------|---------|------------|
| **Documents** | PDF, DOCX, PPTX | Docling (OCR inclus) |
| **Web** | HTML, Markdown | Extraction directe |
| **Audio** | MP3, WAV | Whisper (transcription) |
| **Texte** | TXT, MD | Lecture directe |

## 💡 Exemples d'Usage

### 📚 Étudiant en Médecine
```
Vous: "Quels sont les symptômes de l'hypertension selon mes cours ?"
Assistant: D'après votre cours de cardiologie (cardio_chap3.pdf), 
les symptômes incluent... [Source: cardio_chap3.pdf, page 15]
```

### 🏛️ Étudiant en Droit
```
Vous: "Résume-moi l'article 1382 du Code Civil"
Assistant: L'article 1382 traite de la responsabilité civile...
[Source: code_civil.pdf, page 234]
```

### 💻 Étudiant en Informatique
```
Vous: "Comment fonctionne l'algorithme de tri rapide ?"
Assistant: Le tri rapide utilise la stratégie diviser-pour-régner...
[Source: algorithmes_cours.pdf, page 67]
```

## 🔧 Configuration Avancée

### Variables d'environnement (`.env`)
```bash
# Base de données
DATABASE_URL=postgresql://studyrag:password@localhost:5432/studyrag

# IA locale (recommandé)
OLLAMA_BASE_URL=http://localhost:11434
LLM_CHOICE=llama3.2

# Optionnel : OpenAI en fallback
# OPENAI_API_KEY=sk-your-key-here

# Paramètres de performance
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_SEARCH_RESULTS=5
```

### Modèles IA disponibles
```bash
# Modèles Ollama (locaux)
ollama pull llama3.2      # Équilibré (recommandé)
ollama pull mistral       # Rapide
ollama pull qwen2.5       # Multilingue

# Changer de modèle
export LLM_CHOICE=mistral
```

## 🧪 Tests et Vérification

### Vérifier l'installation
```bash
# Test complet de l'installation
python scripts/post_setup_check.py

# Tests individuels
python scripts/test_ollama_setup.py      # Test Ollama
python scripts/test_embedding_models.py  # Test embeddings
python scripts/verify_implementation.py  # Test complet
```

### Performance et métriques
```bash
# Évaluation de la qualité des réponses
python scripts/test_evaluation.py

# Statistiques de la base de données
psql $DATABASE_URL -c "
SELECT COUNT(*) as documents, 
       (SELECT COUNT(*) FROM chunks) as chunks;
"
```

## 🚨 Dépannage Rapide

### Problèmes courants

#### Ollama ne répond pas
```bash
# Redémarrer Ollama
pkill ollama
ollama serve &

# Tester la connexion
curl http://localhost:11434/api/tags
```

#### Base de données inaccessible
```bash
# Vérifier PostgreSQL
sudo systemctl status postgresql  # Linux
Get-Service postgresql*           # Windows

# Tester la connexion
psql $DATABASE_URL -c "SELECT 1;"
```

#### Python/UV non trouvé
```bash
# Ajouter au PATH (Linux/macOS)
export PATH="$HOME/.cargo/bin:$PATH"

# Redémarrer le terminal (Windows)
```

**Plus de solutions** : Voir `docs/troubleshooting.md`

## 📁 Structure du Projet

```
studyrag/
├── 🚀 setup.bat/setup.sh        # Scripts d'installation
├── 💬 cli.py                    # Interface principale
├── 🤖 rag_agent.py             # Agent IA
├── 📄 ingestion/               # Traitement documents
├── 🛠️ utils/                   # Utilitaires
├── 📚 docs/                    # Documentation complète
├── 🧪 scripts/                 # Tests et maintenance
├── 📖 test_samples/            # Documents d'exemple
└── ⚙️ .env                     # Configuration
```

## 🎓 Cas d'Usage Étudiants

### 📝 Révisions d'Examens
- Posez des questions sur vos cours
- Obtenez des résumés automatiques
- Vérifiez votre compréhension

### 📚 Recherche Documentaire
- Trouvez rapidement des informations
- Citations automatiques avec sources
- Croisement de plusieurs documents

### 🎯 Préparation de Présentations
- Extrayez les points clés
- Générez des plans détaillés
- Vérifiez la cohérence des arguments

## 🌟 Fonctionnalités Avancées

### 🔍 Recherche Hybride
- Recherche sémantique (sens des mots)
- Recherche textuelle (mots-clés exacts)
- Combinaison intelligente des résultats

### 📊 Citations Précises
- Numéro de page exact
- Nom du document source
- Contexte de la citation

### 🧠 Mémoire Conversationnelle
- L'assistant se souvient du contexte
- Questions de suivi naturelles
- Historique des conversations

## 🏗️ Architecture Technique

### Stack Principal
- **Backend** : Python 3.9+ avec FastAPI
- **Agent IA** : PydanticAI pour la logique conversationnelle
- **LLM Local** : Ollama (llama3.2, mistral, qwen2.5)
- **Embeddings** : Sentence Transformers (local) avec fallback OpenAI
- **Base de données** : PostgreSQL avec PGVector pour la recherche vectorielle
- **Traitement documents** : Docling (PDF, Word, PowerPoint, HTML, Audio via Whisper)
- **Interface** : CLI avec Rich + Interface web FastAPI optionnelle

### Composants Principaux
- **Agent RAG** (`rag_agent.py`) : Agent conversationnel principal avec PydanticAI
- **CLI Interactif** (`cli.py`) : Interface en ligne de commande avec Rich
- **Pipeline d'ingestion** (`ingestion/`) : Traitement et indexation des documents
- **Utilitaires** (`utils/`) : Modules pour DB, providers, embeddings

## 🤝 Contribution et Support

### 🐛 Signaler un Bug
1. Vérifier les [issues existantes](https://github.com/votre-repo/issues)
2. Créer une nouvelle issue avec :
   - Description du problème
   - Étapes pour reproduire
   - Logs d'erreur

### 💡 Proposer une Fonctionnalité
1. Ouvrir une issue "Feature Request"
2. Décrire le cas d'usage
3. Proposer une implémentation

### 📖 Documentation
- **Guide complet** : `SETUP.md`
- **Dépannage** : `docs/troubleshooting.md`
- **Développement** : `docs/development-guidelines.md`
- **Commandes rapides** : `docs/quick-commands.md`

## 📄 Licence et Crédits

### 📜 Licence
MIT License - Utilisez librement pour vos études !

### 🙏 Remerciements Spéciaux
- **[Cole Medin](https://github.com/coleam00)** - Créateur du [repo original](https://github.com/coleam00/ottomator-agents/tree/main/docling-rag-agent) qui a inspiré ce projet
- **Docling** - Traitement avancé de documents
- **Ollama** - IA locale accessible
- **PydanticAI** - Framework d'agents IA

---

## 🚀 Commencer Maintenant

### Windows (Débutant)
```cmd
# Télécharger le ZIP, puis :
setup.bat
```

### Linux/macOS (Développeur)
```bash
git clone https://github.com/votre-repo/studyrag
cd studyrag && python3 setup.py
```

### Première question
```bash
uv run python cli.py
# Puis tapez : "Explique-moi ce qu'est StudyRAG"
```

**StudyRAG - Votre assistant d'étude personnel, 100% local et privé** 🎓✨