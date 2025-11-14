---
inclusion: manual
---

# Configuration Kiro pour StudyRAG

Ce dossier contient tous les fichiers de steering pour optimiser l'assistance de Kiro sur le projet StudyRAG.

## 📁 Fichiers de Steering

### `project-overview.md` (Toujours inclus)
- Vue d'ensemble du projet StudyRAG
- Architecture technique et composants clés
- Contexte éducatif et objectifs
- Points d'attention spécifiques pour Kiro

### `development-guidelines.md` (Toujours inclus)
- Standards de code et bonnes pratiques
- Gestion des dépendances avec UV
- Configuration des modèles et LLM
- Guidelines de test et debugging

### `troubleshooting.md` (Toujours inclus)
- Guide de dépannage complet
- Solutions aux problèmes fréquents
- Commandes de diagnostic
- Procédures de récupération

### `api-reference.md` (Inclus pour fichiers .py)
- Référence complète des APIs
- Modèles de données
- Fonctions de recherche
- Pipeline d'ingestion

### `performance-optimization.md` (Toujours inclus)
- Optimisations base de données
- Cache et batch processing
- Optimisations LLM et recherche
- Monitoring des performances

### `quick-commands.md` (Toujours inclus)
- Commandes rapides pour développement
- Scripts de test et validation
- Maintenance et nettoyage
- Raccourcis utiles

## 🎯 Utilisation

Ces fichiers permettent à Kiro de :

1. **Comprendre le contexte** du projet StudyRAG
2. **Respecter les conventions** de développement
3. **Proposer des solutions** adaptées au stack technique
4. **Diagnostiquer rapidement** les problèmes
5. **Optimiser les performances** selon les bonnes pratiques
6. **Fournir les bonnes commandes** pour chaque situation

## 🔧 Configuration

- **Inclusion automatique** : La plupart des fichiers sont inclus automatiquement
- **Inclusion conditionnelle** : `api-reference.md` s'active pour les fichiers Python
- **Inclusion manuelle** : Ce README peut être référencé avec `#steering`

## 📚 Références Externes

Les fichiers de steering peuvent référencer d'autres documents du projet :
- `#[[file:README.md]]` - Documentation principale
- `#[[file:pyproject.toml]]` - Configuration des dépendances
- `#[[file:sql/schema.sql]]` - Schéma de base de données

## 🚀 Mise à Jour

Ces fichiers doivent être mis à jour quand :
- L'architecture du projet évolue
- De nouvelles conventions sont adoptées
- Des problèmes récurrents sont identifiés
- Des optimisations sont découvertes

---

**💡 Conseil** : Utilise `#steering` dans tes conversations avec Kiro pour référencer manuellement ce guide !