#!/bin/bash

# StudyRAG - Script de Setup Automatique
# Configure tout l'environnement de développement en une commande

set -e  # Arrêter en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    StudyRAG - Setup Automatique              ║"
    echo "║              Configuration complète de l'environnement       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${YELLOW}🔧 $1...${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Vérification des prérequis
check_requirements() {
    print_step "Vérification des prérequis système"
    
    # Python 3.9+
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python: $PYTHON_VERSION"
    else
        print_error "Python 3.9+ requis"
        exit 1
    fi
    
    # Git
    if command -v git &> /dev/null; then
        print_success "Git: $(git --version | cut -d' ' -f3)"
    else
        print_error "Git requis"
        exit 1
    fi
    
    # Curl
    if command -v curl &> /dev/null; then
        print_success "Curl disponible"
    else
        print_error "Curl requis"
        exit 1
    fi
}

# Installation de UV
install_uv() {
    print_step "Installation de UV (gestionnaire de dépendances)"
    
    if command -v uv &> /dev/null; then
        print_success "UV déjà installé: $(uv --version)"
        return
    fi
    
    echo "Installation de UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Ajouter UV au PATH pour cette session
    export PATH="$HOME/.cargo/bin:$PATH"
    
    if command -v uv &> /dev/null; then
        print_success "UV installé avec succès"
    else
        print_error "Échec de l'installation de UV"
        exit 1
    fi
}

# Configuration de l'environnement Python
setup_python_env() {
    print_step "Configuration de l'environnement Python"
    
    echo "Installation des dépendances..."
    uv sync
    
    echo "Vérification de l'installation..."
    if uv run python -c "import fastapi, asyncpg, rich; print('OK')" &> /dev/null; then
        print_success "Environnement Python configuré"
    else
        print_error "Problème avec les dépendances Python"
        exit 1
    fi
}

# Configuration PostgreSQL
setup_database() {
    print_step "Configuration de la base de données"
    
    # Vérifier PostgreSQL
    if command -v psql &> /dev/null; then
        print_success "PostgreSQL détecté"
    else
        print_error "PostgreSQL non trouvé"
        echo "Installation requise:"
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  brew install postgresql@15"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "  sudo apt-get install postgresql postgresql-contrib"
        fi
        
        echo "Puis relancez ce script."
        exit 1
    fi
    
    # Configuration par défaut
    DEFAULT_DB_URL="postgresql://studyrag:password@localhost:5432/studyrag"
    
    echo "Configuration de la base de données:"
    echo "URL par défaut: $DEFAULT_DB_URL"
    read -p "Appuyez sur Entrée pour utiliser cette URL ou tapez la vôtre: " DB_URL
    
    if [ -z "$DB_URL" ]; then
        DB_URL=$DEFAULT_DB_URL
    fi
    
    # Test de connexion (simple)
    echo "Test de connexion à la base de données..."
    if psql "$DB_URL" -c "SELECT 1;" &> /dev/null; then
        print_success "Connexion à la base de données réussie"
        
        # Créer le schéma si disponible
        if [ -f "sql/schema.sql" ]; then
            echo "Création du schéma..."
            psql "$DB_URL" -f sql/schema.sql &> /dev/null || print_warning "Problème avec le schéma"
            print_success "Schéma de base de données configuré"
        fi
    else
        print_warning "Impossible de se connecter à la base"
        echo "Créez d'abord la base de données:"
        echo "  createdb studyrag"
        echo "Puis relancez ce script."
    fi
    
    # Sauvegarder l'URL pour le fichier .env
    echo "$DB_URL" > .db_url_temp
}

# Installation et configuration d'Ollama
setup_ollama() {
    print_step "Configuration d'Ollama (LLM local)"
    
    # Vérifier si Ollama est installé
    if command -v ollama &> /dev/null; then
        print_success "Ollama déjà installé"
    else
        echo "Installation d'Ollama..."
        
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            print_warning "Téléchargez Ollama depuis: https://ollama.ai/download"
            return
        else
            curl -fsSL https://ollama.ai/install.sh | sh
            print_success "Ollama installé"
        fi
    fi
    
    # Démarrer Ollama en arrière-plan
    echo "Démarrage du serveur Ollama..."
    ollama serve &> /dev/null &
    OLLAMA_PID=$!
    
    # Attendre que le serveur soit prêt
    sleep 3
    
    # Télécharger un modèle recommandé
    echo "Voulez-vous télécharger le modèle llama3.2 (recommandé) ? [Y/n]"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY]|"")$ ]]; then
        echo "Téléchargement du modèle llama3.2..."
        ollama pull llama3.2
        print_success "Modèle llama3.2 téléchargé"
    fi
}

# Création du fichier .env
create_env_file() {
    print_step "Création du fichier de configuration"
    
    # Lire l'URL de la base de données
    if [ -f ".db_url_temp" ]; then
        DB_URL=$(cat .db_url_temp)
        rm .db_url_temp
    else
        DB_URL="postgresql://studyrag:password@localhost:5432/studyrag"
    fi
    
    # Créer le fichier .env
    cat > .env << EOF
# Configuration StudyRAG

# Base de données
DATABASE_URL=$DB_URL

# Ollama (LLM local)
OLLAMA_BASE_URL=http://localhost:11434
LLM_CHOICE=llama3.2

# Embeddings (local par défaut)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# OpenAI (optionnel)
# OPENAI_API_KEY=sk-your-key-here

# Configuration avancée
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_SEARCH_RESULTS=5
EOF
    
    print_success "Fichier .env configuré"
}

# Création de documents d'exemple
create_sample_docs() {
    print_step "Création de documents d'exemple"
    
    mkdir -p test_samples
    
    # Document d'accueil
    cat > test_samples/welcome.md << 'EOF'
# Bienvenue dans StudyRAG

StudyRAG est votre assistant d'étude personnel utilisant l'IA locale.

## Fonctionnalités

- Traitement de documents PDF, Word, PowerPoint
- Recherche sémantique dans vos documents  
- Réponses avec citations sources
- Modèles IA locaux (confidentialité garantie)

## Premiers pas

1. Placez vos documents dans le dossier `documents/`
2. Lancez l'ingestion: `uv run python -m ingestion.ingest --documents documents/`
3. Utilisez le CLI: `uv run python cli.py`

## Commandes utiles

- Interface CLI interactive: `uv run python cli.py`
- Interface web: `uv run python main.py`
- Tests: `python scripts/verify_implementation.py`

Bon apprentissage !
EOF

    # Guide de démarrage rapide
    cat > test_samples/guide_demarrage.md << 'EOF'
# Guide de Démarrage Rapide

## Installation terminée ✅

Votre environnement StudyRAG est maintenant configuré !

## Prochaines étapes

### 1. Ingérer vos premiers documents
```bash
# Utiliser les exemples
uv run python -m ingestion.ingest --documents test_samples/

# Ou vos propres documents
uv run python -m ingestion.ingest --documents documents/
```

### 2. Lancer l'interface
```bash
# CLI interactif (recommandé)
uv run python cli.py

# Interface web
uv run python main.py
```

### 3. Tester le système
```bash
python scripts/verify_implementation.py
```

## Dépannage

Si vous rencontrez des problèmes, consultez:
- `docs/troubleshooting.md`
- `docs/quick-commands.md`

Ou lancez les tests individuels:
- `python scripts/test_ollama_setup.py`
- `python scripts/test_embedding_models.py`
EOF

    print_success "Documents d'exemple créés"
}

# Tests de vérification
run_tests() {
    print_step "Tests de vérification"
    
    # Tests disponibles
    tests=(
        "scripts/test_ollama_setup.py:Test Ollama"
        "scripts/test_embedding_models.py:Test Embeddings"
        "scripts/verify_implementation.py:Vérification complète"
    )
    
    for test_info in "${tests[@]}"; do
        IFS=':' read -r script_path description <<< "$test_info"
        
        if [ -f "$script_path" ]; then
            echo "Exécution: $description..."
            if uv run python "$script_path" &> /dev/null; then
                print_success "$description: OK"
            else
                print_warning "$description: Problème détecté"
            fi
        else
            print_warning "Script $script_path non trouvé"
        fi
    done
}

# Affichage des prochaines étapes
print_next_steps() {
    echo -e "\n${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    🎉 Setup terminé avec succès !            ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${BLUE}Prochaines étapes:${NC}"
    echo "1. uv run python -m ingestion.ingest --documents test_samples/"
    echo "2. uv run python cli.py"
    echo ""
    echo -e "${BLUE}Commandes utiles:${NC}"
    echo "• Interface CLI: uv run python cli.py"
    echo "• Interface web: uv run python main.py"
    echo "• Tests: python scripts/verify_implementation.py"
    echo ""
    echo -e "${BLUE}Documentation:${NC} Consultez le dossier docs/"
}

# Fonction principale
main() {
    print_header
    
    # Vérifier les arguments
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        echo "StudyRAG Setup Script"
        echo ""
        echo "Usage: ./setup.sh"
        echo ""
        echo "Ce script configure automatiquement l'environnement StudyRAG:"
        echo "• Installe UV et les dépendances Python"
        echo "• Configure PostgreSQL et PGVector"
        echo "• Installe et configure Ollama"
        echo "• Crée les fichiers de configuration"
        echo "• Lance les tests de vérification"
        echo ""
        echo "Prérequis:"
        echo "• Python 3.9+"
        echo "• Git"
        echo "• PostgreSQL (sera configuré)"
        echo "• Connexion Internet"
        exit 0
    fi
    
    # Exécution des étapes
    check_requirements
    install_uv
    setup_python_env
    setup_database
    setup_ollama
    create_env_file
    create_sample_docs
    run_tests
    
    print_next_steps
}

# Gestion des erreurs
trap 'echo -e "\n${RED}❌ Setup interrompu${NC}"; exit 1' INT TERM

# Lancement du script
main "$@"