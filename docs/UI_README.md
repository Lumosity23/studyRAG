# StudyRAG - Interface Utilisateur Moderne

Une interface web moderne et élégante pour StudyRAG, inspirée de ShadCN UI avec un thème sombre professionnel.

## 🎨 Caractéristiques de l'Interface

### Design Moderne
- **Thème sombre** élégant et professionnel
- **Composants ShadCN UI** adaptés pour une expérience utilisateur optimale
- **Animations fluides** et transitions naturelles
- **Interface responsive** qui s'adapte à tous les écrans
- **Icônes Lucide** pour une cohérence visuelle

### Fonctionnalités Principales

#### 💬 Chat en Temps Réel
- Interface de chat moderne avec bulles de messages
- Support WebSocket pour les réponses en temps réel
- Indicateur de frappe animé
- Historique des conversations avec navigation facile
- Citations des sources avec scores de similarité

#### 📄 Gestion des Documents
- Upload par glisser-déposer avec aperçu en temps réel
- Barre de progression pour le traitement des documents
- Support multi-formats (PDF, DOCX, TXT, MD, HTML)
- Validation des fichiers et gestion des erreurs

#### 🔍 Recherche Sémantique
- Interface de recherche avec suggestions en temps réel
- Résultats avec scores de pertinence
- Intégration directe avec le chat
- Mise en évidence des passages pertinents

#### 🎯 Actions Rapides
- Boutons d'action rapide pour les tâches courantes
- Raccourcis clavier intuitifs
- Navigation fluide entre les fonctionnalités

## 🚀 Installation et Configuration

### Prérequis
- Python 3.9+
- FastAPI application configurée
- Ollama installé et configuré
- Base de données PostgreSQL avec PGVector

### Démarrage Rapide

1. **Tester l'interface** :
```bash
python test_ui.py
```

2. **Démarrer le serveur de développement** :
```bash
uv run python app/main.py
```

3. **Accéder à l'interface** :
- Interface web : http://localhost:8000
- Documentation API : http://localhost:8000/docs
- Health check : http://localhost:8000/health

## 📁 Structure des Fichiers

```
static/
├── index.html          # Interface principale
├── app.js             # Logique JavaScript
├── styles.css         # Styles personnalisés
└── demo-data.js       # Données de démonstration

app/
├── main.py            # Application FastAPI
├── api/               # Endpoints API
│   ├── endpoints/
│   │   ├── chat.py    # WebSocket et chat
│   │   ├── documents.py # Upload et traitement
│   │   └── search.py  # Recherche sémantique
│   └── routes.py      # Configuration des routes
└── ...
```

## 🔧 Configuration

### Variables d'Environnement
```bash
# Base de données
DATABASE_URL=postgresql://user:pass@localhost:5432/studyrag

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_CHOICE=llama3.2

# Optionnel - OpenAI fallback
OPENAI_API_KEY=sk-...

# Configuration serveur
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### Personnalisation du Thème

Le thème peut être personnalisé en modifiant les variables CSS dans `styles.css` :

```css
:root {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  --primary: 210 40% 98%;
  --secondary: 217.2 32.6% 17.5%;
  /* ... autres variables */
}
```

## 🎮 Utilisation

### Chat avec l'Assistant
1. Cliquez sur "Nouvelle conversation" ou utilisez une conversation existante
2. Tapez votre question dans la zone de texte
3. Utilisez Shift + Entrée pour les nouvelles lignes
4. L'assistant répond en temps réel avec des sources citées

### Upload de Documents
1. Cliquez sur le bouton "Upload" ou utilisez l'action rapide
2. Glissez-déposez vos fichiers ou cliquez pour sélectionner
3. Suivez le progrès du traitement en temps réel
4. Les documents sont automatiquement indexés et disponibles pour le chat

### Recherche dans les Documents
1. Cliquez sur "Recherche" ou utilisez Ctrl+K
2. Tapez votre requête de recherche
3. Parcourez les résultats avec scores de similarité
4. Cliquez sur un résultat pour l'utiliser dans le chat

## 🔌 Intégration API

### Endpoints Principaux

#### Chat
```javascript
// Envoi de message
POST /api/v1/chat/message
{
  "message": "Votre question",
  "conversation_id": "conv_123",
  "include_sources": true
}

// WebSocket temps réel
WS /api/v1/chat/ws/{conversation_id}
```

#### Documents
```javascript
// Upload de document
POST /api/v1/documents/upload
FormData: { file: File }

// Statut du traitement
GET /api/v1/documents/status/{task_id}
```

#### Recherche
```javascript
// Recherche sémantique
POST /api/v1/search/
{
  "query": "votre recherche",
  "top_k": 10,
  "min_similarity": 0.3
}
```

## 🎨 Personnalisation

### Ajouter de Nouveaux Composants

1. **Créer le HTML** dans `index.html`
2. **Ajouter les styles** dans `styles.css`
3. **Implémenter la logique** dans `app.js`
4. **Connecter à l'API** si nécessaire

### Exemple - Nouveau Modal
```html
<!-- HTML -->
<div id="custom-modal" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 hidden">
  <div class="bg-card border border-border rounded-lg">
    <!-- Contenu du modal -->
  </div>
</div>
```

```css
/* CSS */
.custom-modal {
  animation: fadeIn 0.3s ease-out;
}
```

```javascript
// JavaScript
openCustomModal() {
  document.getElementById('custom-modal').classList.remove('hidden');
}
```

## 🐛 Débogage

### Logs de Développement
- Ouvrez les DevTools (F12)
- Consultez la console pour les logs JavaScript
- Vérifiez l'onglet Network pour les requêtes API
- Utilisez l'onglet WebSocket pour les connexions temps réel

### Problèmes Courants

#### WebSocket ne se connecte pas
```javascript
// Vérifiez la configuration dans app.js
this.wsUrl = `${this.wsBase}//${window.location.host}/api/v1/chat/ws`;
```

#### Upload de fichiers échoue
- Vérifiez la taille du fichier (max 50MB)
- Vérifiez le format supporté
- Consultez les logs serveur

#### Recherche ne fonctionne pas
- Vérifiez que des documents sont indexés
- Vérifiez la connexion à la base de données vectorielle
- Testez avec l'endpoint API directement

## 🚀 Déploiement

### Production
1. **Construire les assets** (si nécessaire)
2. **Configurer les variables d'environnement**
3. **Démarrer avec Gunicorn** :
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker
```dockerfile
# Utiliser l'image de base existante
FROM python:3.11-slim

# Copier les fichiers statiques
COPY static/ /app/static/

# Le reste de la configuration...
```

## 📚 Ressources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Lucide Icons](https://lucide.dev/)
- [ShadCN UI](https://ui.shadcn.com/)

## 🤝 Contribution

1. Testez vos modifications avec `python test_ui.py`
2. Respectez le style de code existant
3. Documentez les nouvelles fonctionnalités
4. Testez sur différents navigateurs et tailles d'écran

## 📄 Licence

Ce projet utilise la même licence que StudyRAG principal.