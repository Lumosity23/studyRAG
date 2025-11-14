#!/bin/bash

# Script de nettoyage avant push GitHub
# Évite les problèmes de fichiers volumineux

echo "🧹 Nettoyage avant push GitHub..."

# Supprimer les caches et builds
echo "Suppression des caches..."
rm -rf frontend/.next/
rm -rf frontend/node_modules/
rm -rf chroma_db/
rm -rf temp_files/
rm -rf documents/
rm -rf .pytest_cache/
rm -rf __pycache__/
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*.tsbuildinfo" -delete

# Vérifier la taille des fichiers suivis
echo "📊 Taille des fichiers suivis par Git:"
git ls-files | xargs du -ch | tail -1

# Vérifier s'il y a des gros fichiers
echo "🔍 Recherche de gros fichiers (>10MB):"
git ls-files | xargs ls -lh | awk '$5 ~ /^[0-9]+M$/ && $5+0 > 10 {print $5, $9}'

echo "✅ Nettoyage terminé. Vous pouvez maintenant faire git push."