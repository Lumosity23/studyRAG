#!/bin/bash

# 🚀 Script de migration vers l'architecture monorepo StudyRAG
# Ce script automatise la création de la nouvelle structure

set -e  # Arrêter en cas d'erreur

echo "🎯 StudyRAG Migration vers Monorepo"
echo "===================================="

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages colorés
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Vérifications préliminaires
check_requirements() {
    log_info "Vérification des prérequis..."
    
    # Vérifier Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js n'est pas installé. Veuillez l'installer d'abord."
        exit 1
    fi
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_warning "Docker n'est pas installé. Il sera nécessaire pour le développement."
    fi
    
    # Vérifier que nous sommes dans le bon répertoire
    if [ ! -f "app/main.py" ]; then
        log_error "Ce script doit être exécuté depuis le répertoire racine de votre projet StudyRAG actuel."
        exit 1
    fi
    
    log_success "Prérequis vérifiés"
}

# Créer la structure du monorepo
create_monorepo_structure() {
    log_info "Création de la structure du monorepo..."
    
    # Aller au répertoire parent
    cd ..
    
    # Créer le répertoire du monorepo
    MONOREPO_DIR="studyrag-monorepo"
    if [ -d "$MONOREPO_DIR" ]; then
        log_warning "Le répertoire $MONOREPO_DIR existe déjà. Voulez-vous continuer? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "Migration annulée."
            exit 0
        fi
        rm -rf "$MONOREPO_DIR"
    fi
    
    mkdir -p "$MONOREPO_DIR"
    cd "$MONOREPO_DIR"
    
    # Créer la structure des dossiers
    mkdir -p {frontend,backend,shared/{docs,scripts,types},infrastructure/{docker,k8s,terraform}}
    
    log_success "Structure du monorepo créée"
}

# Migrer le backend
migrate_backend() {
    log_info "Migration du backend..."
    
    # Copier tout le projet actuel vers backend
    cp -r ../Docling_RAG_app/* backend/
    
    # Nettoyer les fichiers frontend du backend
    rm -rf backend/static/
    rm -rf backend/templates/ 2>/dev/null || true
    
    # Déplacer les fichiers de documentation
    mv backend/API_DOCUMENTATION_FOR_UI.md shared/docs/ 2>/dev/null || true
    mv backend/TYPESCRIPT_TYPES.ts shared/types/ 2>/dev/null || true
    mv backend/UI_*.md shared/docs/ 2>/dev/null || true
    mv backend/ARCHITECTURE_GUIDE.md shared/docs/ 2>/dev/null || true
    
    # Créer le Dockerfile pour le backend
    cat > backend/Dockerfile << 'EOF'
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

# Créer le répertoire uploads
RUN mkdir -p uploads

# Exposer le port
EXPOSE 8000

# Commande par défaut
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
    
    log_success "Backend migré"
}

# Créer le frontend Next.js
create_frontend() {
    log_info "Création du frontend Next.js..."
    
    cd frontend
    
    # Créer le projet Next.js
    npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --yes
    
    # Installer ShadCN/UI
    npx shadcn-ui@latest init --yes --defaults
    
    # Installer les composants ShadCN nécessaires
    npx shadcn-ui@latest add button card input label textarea table badge toast dialog dropdown-menu tabs separator progress avatar sheet
    
    # Installer les dépendances supplémentaires
    npm install @tanstack/react-query react-dropzone lucide-react @hookform/resolvers zod react-hook-form date-fns clsx tailwind-merge
    
    # Créer le Dockerfile de développement
    cat > Dockerfile.dev << 'EOF'
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
EOF
    
    # Créer le Dockerfile de production
    cat > Dockerfile.prod << 'EOF'
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
EOF
    
    # Mettre à jour next.config.js
    cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/:path*`,
      },
      {
        source: '/health',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/health`,
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
EOF
    
    cd ..
    log_success "Frontend Next.js créé"
}

# Créer les fichiers Docker Compose
create_docker_compose() {
    log_info "Création des fichiers Docker Compose..."
    
    # Docker Compose pour le développement
    cat > docker-compose.yml << 'EOF'
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
      - CHROMA_PORT=8000
      - OLLAMA_URL=http://ollama:11434
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./backend:/app
      - ./shared:/shared
      - backend_uploads:/app/uploads
    depends_on:
      - postgres
      - chroma
      - ollama
      - redis
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
      - /app/.next
    depends_on:
      - backend

  # Base de données PostgreSQL
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: studyrag
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
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
  backend_uploads:
EOF
    
    # Fichier d'environnement exemple
    cat > .env.example << 'EOF'
# Backend Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/studyrag
CHROMA_HOST=localhost
CHROMA_PORT=8001
OLLAMA_URL=http://localhost:11434
REDIS_URL=redis://localhost:6379

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Security
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=["http://localhost:3000"]

# Upload Configuration
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=52428800
EOF
    
    # Copier vers .env si il n'existe pas
    if [ ! -f .env ]; then
        cp .env.example .env
    fi
    
    log_success "Fichiers Docker Compose créés"
}

# Créer les scripts utilitaires
create_scripts() {
    log_info "Création des scripts utilitaires..."
    
    # Package.json racine
    cat > package.json << 'EOF'
{
  "name": "studyrag-monorepo",
  "version": "1.0.0",
  "description": "StudyRAG - AI-powered document analysis system",
  "private": true,
  "scripts": {
    "dev": "docker-compose up",
    "dev:build": "docker-compose up --build",
    "dev:down": "docker-compose down",
    "dev:clean": "docker-compose down -v --remove-orphans",
    "setup": "chmod +x shared/scripts/dev-setup.sh && ./shared/scripts/dev-setup.sh",
    "frontend": "cd frontend && npm run dev",
    "backend": "cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000",
    "test:frontend": "cd frontend && npm test",
    "test:backend": "cd backend && python -m pytest",
    "test": "npm run test:backend && npm run test:frontend",
    "build:frontend": "cd frontend && npm run build",
    "build:backend": "cd backend && docker build -t studyrag-backend .",
    "build": "npm run build:backend && npm run build:frontend",
    "install:all": "cd frontend && npm install && cd ../backend && pip install -r requirements.txt"
  },
  "workspaces": [
    "frontend"
  ],
  "keywords": ["rag", "ai", "document-analysis", "fastapi", "nextjs"],
  "author": "StudyRAG Team",
  "license": "MIT"
}
EOF
    
    # Script de setup
    cat > shared/scripts/dev-setup.sh << 'EOF'
#!/bin/bash

echo "🚀 Setting up StudyRAG development environment..."

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed."
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Vérifier Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is required but not installed."
    exit 1
fi

# Créer le fichier .env s'il n'existe pas
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env file from template"
    echo "⚠️  Please review and update the .env file with your configuration"
fi

# Construire et démarrer les services
echo "🏗️ Building and starting services..."
docker-compose up --build -d

# Attendre que les services soient prêts
echo "⏳ Waiting for services to be ready..."
sleep 30

# Vérifier la santé des services
echo "🔍 Checking service health..."

# Backend
if curl -f http://localhost:8000/health &>/dev/null; then
    echo "✅ Backend is ready"
else
    echo "❌ Backend not ready - check logs with: docker-compose logs backend"
fi

# Frontend
if curl -f http://localhost:3000 &>/dev/null; then
    echo "✅ Frontend is ready"
else
    echo "❌ Frontend not ready - check logs with: docker-compose logs frontend"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📱 Access your application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo "   ChromaDB: http://localhost:8001"
echo ""
echo "🔧 Useful commands:"
echo "   npm run dev          - Start all services"
echo "   npm run dev:down     - Stop all services"
echo "   npm run dev:clean    - Stop and remove all data"
echo "   docker-compose logs  - View all logs"
echo ""
EOF
    
    chmod +x shared/scripts/dev-setup.sh
    
    # README principal
    cat > README.md << 'EOF'
# 🚀 StudyRAG - AI-Powered Document Analysis System

StudyRAG is a modern Retrieval-Augmented Generation (RAG) system designed for academic research and document analysis. It combines the power of AI with intelligent document processing to help you find, understand, and interact with your research materials.

## 🏗️ Architecture

This project uses a modern monorepo architecture with:

- **Frontend**: Next.js 14 + TypeScript + ShadCN/UI + Tailwind CSS
- **Backend**: FastAPI + Python with async support
- **Database**: PostgreSQL for metadata + ChromaDB for vector storage
- **AI**: Ollama for local LLM inference + SentenceTransformers for embeddings
- **Infrastructure**: Docker Compose for development, containerized deployment

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Development Setup

1. **Clone and setup:**
   ```bash
   git clone <your-repo>
   cd studyrag-monorepo
   npm run setup
   ```

2. **Start development environment:**
   ```bash
   npm run dev
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Local Development (without Docker)

1. **Backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## 📁 Project Structure

```
studyrag-monorepo/
├── frontend/           # Next.js application
├── backend/            # FastAPI application
├── shared/             # Shared resources and documentation
├── infrastructure/     # Deployment configurations
├── docker-compose.yml  # Development environment
└── package.json        # Monorepo scripts
```

## 🎯 Features

- **📄 Document Upload**: Drag & drop interface with support for PDF, DOCX, HTML, TXT, MD
- **🔍 Semantic Search**: Natural language search across all documents
- **💬 AI Chat**: Ask questions about your documents with contextual responses
- **📊 Real-time Updates**: WebSocket integration for live processing status
- **🎨 Modern UI**: Beautiful, responsive interface built with ShadCN/UI
- **🔒 Type Safety**: Full TypeScript integration across frontend and backend

## 🛠️ Development

### Available Scripts

- `npm run dev` - Start all services with Docker Compose
- `npm run frontend` - Start only frontend (requires backend running)
- `npm run backend` - Start only backend
- `npm run test` - Run all tests
- `npm run build` - Build all applications

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Backend
DATABASE_URL=postgresql://user:password@localhost:5432/studyrag
OLLAMA_URL=http://localhost:11434

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🚀 Deployment

### Production with Docker

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Separate Deployment

- **Frontend**: Deploy to Vercel/Netlify
- **Backend**: Deploy to Railway/Render/AWS

## 📚 Documentation

- [API Documentation](./shared/docs/API_DOCUMENTATION_FOR_UI.md)
- [Architecture Guide](./shared/docs/ARCHITECTURE_GUIDE.md)
- [TypeScript Types](./shared/types/TYPESCRIPT_TYPES.ts)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.
EOF
    
    log_success "Scripts et documentation créés"
}

# Finaliser la migration
finalize_migration() {
    log_info "Finalisation de la migration..."
    
    # Installer les dépendances du frontend
    cd frontend
    npm install
    cd ..
    
    # Créer un commit initial si git est initialisé
    if command -v git &> /dev/null; then
        git init
        git add .
        git commit -m "Initial commit: StudyRAG monorepo migration"
    fi
    
    log_success "Migration terminée!"
}

# Afficher les instructions finales
show_final_instructions() {
    echo ""
    echo "🎉 Migration vers le monorepo terminée avec succès!"
    echo "=================================================="
    echo ""
    echo "📁 Votre nouveau projet se trouve dans: $(pwd)"
    echo ""
    echo "🚀 Prochaines étapes:"
    echo "   1. cd studyrag-monorepo"
    echo "   2. Vérifiez le fichier .env"
    echo "   3. npm run setup (pour démarrer avec Docker)"
    echo "   ou"
    echo "   3. npm run frontend & npm run backend (développement local)"
    echo ""
    echo "🌐 Une fois démarré, accédez à:"
    echo "   - Frontend: http://localhost:3000"
    echo "   - Backend: http://localhost:8000"
    echo "   - API Docs: http://localhost:8000/docs"
    echo ""
    echo "📚 Documentation disponible dans shared/docs/"
    echo ""
    log_success "Bonne continuation avec votre nouveau StudyRAG! 🚀"
}

# Fonction principale
main() {
    echo "Démarrage de la migration..."
    
    check_requirements
    create_monorepo_structure
    migrate_backend
    create_frontend
    create_docker_compose
    create_scripts
    finalize_migration
    show_final_instructions
}

# Exécuter le script principal
main "$@"