#!/bin/bash
# Script de démarrage StudyRAG (version bash alternative)

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
OLLAMA_PORT=11434

# Fonction d'affichage
print_status() {
    echo -e "${BLUE}[StudyRAG]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Fonction de nettoyage
cleanup() {
    print_status "Arrêt des services..."
    
    # Arrêter les processus en arrière-plan
    if [[ ! -z "$BACKEND_PID" ]]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [[ ! -z "$FRONTEND_PID" ]]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Attendre un peu puis forcer l'arrêt
    sleep 2
    pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
    pkill -f "next.*dev" 2>/dev/null || true
    
    print_success "Services arrêtés"
    exit 0
}

# Capturer Ctrl+C
trap cleanup SIGINT SIGTERM

# Vérification des dépendances
check_dependencies() {
    print_status "Vérification des dépendances..."
    
    # Vérifier UV
    if ! command -v uv &> /dev/null; then
        print_error "UV non trouvé. Installez UV: https://docs.astral.sh/uv/"
        exit 1
    fi
    print_success "UV installé"
    
    # Vérifier Node.js
    if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
        print_error "Node.js/npm non trouvé. Installez Node.js: https://nodejs.org/"
        exit 1
    fi
    print_success "Node.js et npm installés"
}

# Vérification d'Ollama
check_ollama() {
    if curl -s "http://localhost:$OLLAMA_PORT/api/tags" > /dev/null 2>&1; then
        local models=$(curl -s "http://localhost:$OLLAMA_PORT/api/tags" | jq -r '.models | length' 2>/dev/null || echo "0")
        print_success "Ollama disponible avec $models modèles"
    else
        print_warning "Ollama non disponible. Démarrez Ollama avec: ollama serve"
    fi
}

# Configuration de l'environnement
setup_environment() {
    print_status "Configuration de l'environnement..."
    
    # Créer .env si nécessaire
    if [[ ! -f .env && -f .env.example ]]; then
        print_status "Création du fichier .env depuis .env.example"
        cp .env.example .env
        
        # Ajuster pour SQLite en développement
        sed -i 's|DATABASE_URL=postgresql://studyrag:studyrag@localhost:5432/studyrag|DATABASE_URL=sqlite:///./study_rag.db|g' .env
        
        print_success "Fichier .env créé"
    fi
    
    # Synchroniser les dépendances Python
    print_status "Installation des dépendances Python..."
    if uv sync; then
        print_success "Dépendances Python installées"
    else
        print_error "Erreur lors de l'installation des dépendances Python"
        exit 1
    fi
    
    # Installer les dépendances frontend si le dossier existe
    if [[ -d "frontend" ]]; then
        print_status "Installation des dépendances frontend..."
        cd frontend
        if npm install; then
            print_success "Dépendances frontend installées"
        else
            print_error "Erreur lors de l'installation des dépendances frontend"
            exit 1
        fi
        cd ..
    fi
}

# Attendre qu'un service soit disponible
wait_for_service() {
    local name=$1
    local url=$2
    local timeout=${3:-30}
    
    print_status "Attente du démarrage de $name..."
    
    local count=0
    while [[ $count -lt $timeout ]]; do
        if curl -s "$url" > /dev/null 2>&1; then
            print_success "$name démarré sur $url"
            return 0
        fi
        sleep 1
        ((count++))
    done
    
    print_warning "$name met du temps à démarrer..."
    return 1
}

# Démarrage du backend
start_backend() {
    print_status "Démarrage du backend..."
    
    # Démarrer le backend en arrière-plan
    uv run uvicorn app.main:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --reload \
        --log-level info > backend.log 2>&1 &
    
    BACKEND_PID=$!
    
    # Attendre que le backend soit prêt
    wait_for_service "Backend" "http://localhost:$BACKEND_PORT/health"
}

# Démarrage du frontend
start_frontend() {
    if [[ ! -d "frontend" ]]; then
        print_warning "Dossier frontend non trouvé, backend seulement"
        return 0
    fi
    
    print_status "Démarrage du frontend..."
    
    # Démarrer le frontend en arrière-plan
    cd frontend
    npm run dev > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    
    # Attendre que le frontend soit prêt
    wait_for_service "Frontend" "http://localhost:$FRONTEND_PORT"
}

# Affichage du statut
show_status() {
    echo ""
    echo "============================================================"
    echo -e "${GREEN}🎓 StudyRAG démarré avec succès!${NC}"
    echo "============================================================"
    echo ""
    echo -e "🌐 Frontend:      http://localhost:$FRONTEND_PORT"
    echo -e "🔧 Backend API:   http://localhost:$BACKEND_PORT"
    echo -e "📚 Documentation: http://localhost:$BACKEND_PORT/docs"
    echo -e "❤️ Health Check:  http://localhost:$BACKEND_PORT/health"
    echo ""
    echo -e "${YELLOW}Appuyez sur Ctrl+C pour arrêter tous les services${NC}"
    echo "============================================================"
    echo ""
}

# Surveillance des logs
monitor_logs() {
    # Afficher les logs en temps réel (optionnel)
    if [[ "$1" == "--logs" ]]; then
        tail -f backend.log frontend.log 2>/dev/null &
        TAIL_PID=$!
    fi
}

# Fonction principale
main() {
    echo "============================================================"
    echo -e "${BLUE}🎓 StudyRAG - Script de Démarrage${NC}"
    echo "Démarre automatiquement le backend et frontend pour les tests"
    echo "============================================================"
    echo ""
    
    # Vérifications et setup
    check_dependencies
    check_ollama
    setup_environment
    
    # Démarrage des services
    start_backend
    start_frontend
    
    # Surveillance des logs si demandé
    monitor_logs "$1"
    
    # Affichage du statut
    show_status
    
    # Attendre l'interruption
    print_status "Services en cours d'exécution... (Ctrl+C pour arrêter)"
    
    # Boucle d'attente
    while true; do
        # Vérifier que les processus sont toujours en vie
        if [[ ! -z "$BACKEND_PID" ]] && ! kill -0 $BACKEND_PID 2>/dev/null; then
            print_error "Le backend s'est arrêté inopinément"
            exit 1
        fi
        
        if [[ ! -z "$FRONTEND_PID" ]] && ! kill -0 $FRONTEND_PID 2>/dev/null; then
            print_error "Le frontend s'est arrêté inopinément"
            exit 1
        fi
        
        sleep 1
    done
}

# Lancer le script principal
main "$@"