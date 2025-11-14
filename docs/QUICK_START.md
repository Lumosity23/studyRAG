# 🚀 Guide de Démarrage Rapide StudyRAG

## 📋 Prérequis

### Backend
- Python 3.9+
- PostgreSQL avec extension PGVector
- Ollama (optionnel, pour LLM local)

### Frontend
- Node.js 18+
- npm ou yarn

## ⚡ Démarrage Ultra-Rapide

### Option 1: Démarrage Automatique Complet
```bash
# Démarre backend + frontend automatiquement
python start_studyrag_complete.py
```

### Option 2: Démarrage Manuel

#### 1. Configuration
```bash
# Copier le fichier d'environnement
cp .env.example .env

# Éditer les variables (DATABASE_URL obligatoire)
nano .env
```

#### 2. Backend
```bash
# Installer les dépendances
uv sync

# Démarrer le serveur API
python -m app.main
```

#### 3. Frontend (nouveau terminal)
```bash
# Démarrer le frontend
python start_frontend_dev.py
```

## 🌐 Accès aux Services

- **Frontend**: http://localhost:3000
- **API Backend**: http://localhost:8000
- **Documentation API**: http://localhost:8000/docs

## 🔧 Configuration Minimale

### Variables d'Environnement (.env)
```bash
# Obligatoire
DATABASE_URL=postgresql://user:password@localhost:5432/studyrag

# Optionnel
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=sk-your-key-here
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000
```

## 📄 Premier Test

1. **Accéder au frontend**: http://localhost:3000
2. **Uploader un document** via le bouton "Uploader"
3. **Poser une question** dans le prompt central
4. **Voir la réponse** avec citations sources

## 🛠️ Scripts Utiles

```bash
# Vérifier les routes API
python verify_api_routes.py

# Démarrer seulement le frontend
python start_frontend_dev.py

# Démarrer seulement le backend
python -m app.main

# Tests rapides
python scripts/verify_implementation.py
```

## 🎨 Interface Utilisateur

### Fonctionnalités Principales
- ✅ **Prompt centré** comme ChatGPT
- ✅ **Transition fluide** vers mode conversation
- ✅ **Upload de documents** par drag & drop
- ✅ **Citations sources** dans les réponses
- ✅ **Thèmes** clair/sombre avec couleurs pastel
- ✅ **Sidebar** avec historique des conversations

### Navigation
- **Nouvelle conversation**: Clic sur le logo ou bouton "+"
- **Historique**: Sidebar gauche (toggle avec hamburger)
- **Upload**: Bouton "Uploader" ou drag & drop
- **Paramètres**: Icône engrenage (top-right)

## 🔍 Dépannage Rapide

### Backend ne démarre pas
```bash
# Vérifier la base de données
psql $DATABASE_URL -c "SELECT 1"

# Vérifier Ollama (optionnel)
curl http://localhost:11434/api/tags
```

### Frontend ne démarre pas
```bash
# Réinstaller les dépendances
cd frontend && npm install

# Vérifier Node.js
node --version  # Doit être 18+
```

### Routes API ne fonctionnent pas
```bash
# Tester les routes
python verify_api_routes.py

# Vérifier les CORS
curl -H "Origin: http://localhost:3000" http://localhost:8000/health
```

## 📚 Documentation Complète

- **API**: http://localhost:8000/docs (quand le backend tourne)
- **Architecture**: Voir `docs/`
- **Troubleshooting**: Voir `VERIFICATION_GUIDE.md`
- **Commandes**: Voir les steering rules dans `.kiro/steering/`

## 🎯 Prochaines Étapes

1. **Configurer Ollama** pour LLM local
2. **Ajouter des documents** de test
3. **Explorer l'interface** et les fonctionnalités
4. **Personnaliser** les thèmes et paramètres
5. **Intégrer** avec vos documents d'étude

---

**Besoin d'aide ?** Consultez les guides détaillés dans le dossier `docs/` ou les steering rules dans `.kiro/steering/`.