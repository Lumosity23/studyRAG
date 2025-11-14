# 🏗️ Guide d'Architecture StudyRAG - Séparation Frontend/Backend

## 🎯 Vision d'ensemble

Nous allons créer une architecture moderne avec :
- **Frontend** : Next.js + ShadCN/UI (nouveau dossier)
- **Backend** : FastAPI + Services (projet actuel refactorisé)
- **Intégration** : Docker Compose pour le développement, déploiement séparé en production

## 📁 Structure finale recommandée

```
studyrag-monorepo/
├── frontend/                    # Nouveau projet Next.js
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── hooks/
│   ├── package.json
│   ├── next.config.js
│   └── tailwind.config.js
│
├── backend/                     # Votre projet actuel refactorisé
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── services/
│   │   └── models/
│   ├── tests/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
│
├── shared/                      # Ressources partagées
│   ├── docs/
│   ├── scripts/
│   └── types/
│
├── infrastructure/              # Configuration déploiement
│   ├── docker/
│   ├── k8s/
│   └── terraform/
│
├── docker-compose.yml           # Développement local
├── docker-compose.prod.yml      # Production
├── README.md
└── .env.example
```

## 🚀 Plan de migration étape par étape

### Étape 1 : Préparation du monorepo

1. **Créer la structure du monorepo :**
```bash
# Dans le répertoire parent de votre projet actuel
mkdir studyrag-monorepo
cd studyrag-monorepo

# Déplacer votre projet actuel
mv ../Docling_RAG_app backend

# Créer les autres dossiers
mkdir frontend shared infrastructure
mkdir shared/{docs,scripts,types}
mkdir infrastructure/{docker,k8s,terraform}
```

2. **Créer le frontend Next.js :**
```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir
```

### Étape 2 : Refactorisation du backend

**Ce qu'il faut garder de votre projet actuel :**

```python
# À conserver et organiser
backend/
├── app/
│   ├── api/                 # ✅ Vos endpoints actuels
│   ├── core/                # ✅ Configuration, middleware
│   ├── services/            # ✅ Tous vos services
│   │   ├── vector_database.py
│   │   ├── document_processor.py
│   │   ├── embedding_service.py
│   │   ├── chat_engine.py
│   │   ├── search_engine.py
│   │   └── ollama_client.py
│   └── models/              # ✅ Modèles de données
├── tests/                   # ✅ Tous vos tests
├── requirements.txt         # ✅ Dépendances Python
├── .env                     # ✅ Configuration
└── main.py                  # ✅ Point d'entrée FastAPI
```

**Ce qu'il faut supprimer/déplacer :**
```bash
# À supprimer du backend (maintenant dans le frontend)
rm -rf backend/static/
rm -rf backend/templates/

# À déplacer vers shared/docs/
mv backend/API_DOCUMENTATION_FOR_UI.md shared/docs/
mv backend/TYPESCRIPT_TYPES.ts shared/types/
mv backend/UI_*.md shared/docs/
```

### Étape 3 : Configuration Docker

**`docker-compose.yml` (développement) :**
```yaml
version: '3.8'

services:
  # Backend FastAPI
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/studyrag
      - CHROMA_HOST=chroma
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - ./backend:/app
      - ./shared:/shared
    depends_on:
      - postgres
      - chroma
      - ollama
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # Frontend Next.js
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend
    command: npm run dev

  # Base de données PostgreSQL
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: studyrag
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infrastructure/docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  # ChromaDB (base vectorielle)
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - CHROMA_SERVER_HOST=0.0.0.0
      - CHROMA_SERVER_HTTP_PORT=8000

  # Ollama (modèles LLM)
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0

  # Redis (cache et sessions)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  chroma_data:
  ollama_data:
  redis_data:
```

### Étape 4 : Configuration du backend

**`backend/Dockerfile` :**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# Exposer le port
EXPOSE 8000

# Commande par défaut
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`backend/app/core/config.py` (mise à jour) :**
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "StudyRAG API"
    
    # Base de données
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/studyrag"
    
    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    
    # Ollama
    OLLAMA_URL: str = "http://localhost:11434"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8080"]
    
    # Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Étape 5 : Configuration du frontend

**`frontend/Dockerfile.dev` :**
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copier package.json
COPY package*.json ./
RUN npm install

# Copier le code
COPY . .

# Exposer le port
EXPOSE 3000

# Commande de développement
CMD ["npm", "run", "dev"]
```

**`frontend/next.config.js` :**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,POST,PUT,DELETE,OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

## 🔧 Scripts de développement

**`shared/scripts/dev-setup.sh` :**
```bash
#!/bin/bash

echo "🚀 Setting up StudyRAG development environment..."

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed."
    exit 1
fi

# Créer les fichiers d'environnement
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env file from template"
fi

# Construire et démarrer les services
echo "🏗️ Building and starting services..."
docker-compose up --build -d

# Attendre que les services soient prêts
echo "⏳ Waiting for services to be ready..."
sleep 10

# Vérifier la santé des services
echo "🔍 Checking service health..."
curl -f http://localhost:8000/health || echo "❌ Backend not ready"
curl -f http://localhost:3000 || echo "❌ Frontend not ready"

echo "✅ Development environment is ready!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
```

**`package.json` (racine du monorepo) :**
```json
{
  "name": "studyrag-monorepo",
  "private": true,
  "scripts": {
    "dev": "docker-compose up",
    "dev:build": "docker-compose up --build",
    "dev:down": "docker-compose down",
    "dev:clean": "docker-compose down -v --remove-orphans",
    "setup": "chmod +x shared/scripts/dev-setup.sh && ./shared/scripts/dev-setup.sh",
    "frontend": "cd frontend && npm run dev",
    "backend": "cd backend && uvicorn app.main:app --reload",
    "test:frontend": "cd frontend && npm test",
    "test:backend": "cd backend && pytest",
    "test": "npm run test:backend && npm run test:frontend",
    "build:frontend": "cd frontend && npm run build",
    "build:backend": "cd backend && docker build -t studyrag-backend .",
    "build": "npm run build:backend && npm run build:frontend"
  },
  "workspaces": [
    "frontend",
    "backend"
  ]
}
```

## 🚀 Déploiement en production

### Option 1 : Déploiement séparé (recommandé)

**Frontend (Vercel/Netlify) :**
```bash
# Dans le dossier frontend
npm run build
# Déployer sur Vercel avec NEXT_PUBLIC_API_URL=https://api.studyrag.com
```

**Backend (Railway/Render/AWS) :**
```bash
# Dans le dossier backend
docker build -t studyrag-backend .
# Déployer avec les variables d'environnement appropriées
```

### Option 2 : Déploiement unifié (Docker)

**`docker-compose.prod.yml` :**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - CHROMA_HOST=chroma
      - OLLAMA_URL=http://ollama:11434
    depends_on:
      - postgres
      - chroma

  frontend:
    build: 
      context: ./frontend
      dockerfile: Dockerfile.prod
    environment:
      - NEXT_PUBLIC_API_URL=https://api.studyrag.com
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infrastructure/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./infrastructure/ssl:/etc/ssl
    depends_on:
      - frontend
      - backend

  # Autres services (postgres, chroma, etc.)
```

## 📋 Checklist de migration

### Phase 1 : Préparation
- [ ] Créer la structure du monorepo
- [ ] Déplacer le backend actuel
- [ ] Créer le projet frontend Next.js
- [ ] Configurer Docker Compose

### Phase 2 : Backend
- [ ] Nettoyer le backend (supprimer static/, templates/)
- [ ] Mettre à jour la configuration CORS
- [ ] Tester que l'API fonctionne toujours
- [ ] Ajouter les variables d'environnement Docker

### Phase 3 : Frontend
- [ ] Installer ShadCN/UI
- [ ] Configurer le client API
- [ ] Implémenter les pages principales
- [ ] Tester l'intégration avec le backend

### Phase 4 : Intégration
- [ ] Configurer les WebSockets
- [ ] Tester l'upload de fichiers
- [ ] Vérifier les mises à jour temps réel
- [ ] Tests end-to-end

### Phase 5 : Production
- [ ] Configurer les environnements
- [ ] Mettre en place le CI/CD
- [ ] Déployer et tester

## 🎯 Avantages de cette architecture

✅ **Séparation claire** : Frontend et backend indépendants
✅ **Scalabilité** : Chaque partie peut être déployée séparément
✅ **Développement** : Équipes peuvent travailler en parallèle
✅ **Maintenance** : Code organisé et modulaire
✅ **Performance** : Frontend optimisé, backend dédié à l'API
✅ **Flexibilité** : Possibilité de changer de technologie par partie

Cette architecture vous permettra d'avoir une base solide pour faire évoluer StudyRAG ! 🚀