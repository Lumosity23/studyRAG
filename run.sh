#!/bin/bash

# StudyRAG Quick Start Script
# Simple script to start StudyRAG with all checks

echo "🚀 StudyRAG - Démarrage rapide"
echo "================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

# Check if we're in a virtual environment or if uv is available
if [[ -z "$VIRTUAL_ENV" ]] && ! command -v uv &> /dev/null; then
    echo "⚠️  Aucun environnement virtuel détecté et uv non disponible"
    echo "💡 Activez votre environnement virtuel ou installez uv"
    echo "   source .venv/bin/activate  # ou"
    echo "   pip install uv"
    exit 1
fi

# Use uv if available, otherwise use python directly
if command -v uv &> /dev/null; then
    echo "📦 Utilisation de uv pour la gestion des dépendances"
    uv run python start_studyrag.py
else
    echo "🐍 Utilisation de Python direct"
    python3 start_studyrag.py
fi