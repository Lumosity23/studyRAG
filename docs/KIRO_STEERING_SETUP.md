# 🤖 Configuration Kiro Steering - StudyRAG

## ✅ Fichiers de Steering Créés

J'ai créé une configuration complète de steering pour Kiro dans le dossier `.kiro/steering/` :

### 📋 Liste des Fichiers

1. **`project-overview.md`** (Inclusion: always)
   - Vue d'ensemble du projet StudyRAG
   - Architecture technique (Ollama, Docling, PostgreSQL/ChromaDB)
   - Contexte éducatif et objectifs
   - Points d'attention spécifiques pour Kiro

2. **`development-guidelines.md`** (Inclusion: always)
   - Standards de code et structure des imports
   - Gestion des dépendances avec UV (jamais pip)
   - Configuration modèles (priorité Ollama > OpenAI)
   - Guidelines de test et debugging avec Rich

3. **`troubleshooting.md`** (Inclusion: always)
   - Guide de dépannage complet
   - Solutions aux erreurs fréquentes (DB, Ollama, embeddings)
   - Commandes de diagnostic et health checks
   - Procédures de récupération (reset complet/partiel)

4. **`api-reference.md`** (Inclusion: fileMatch "*.py")
   - Référence complète des APIs du projet
   - Modèles de données (Document, Chunk, SearchResult)
   - Fonctions de recherche et pipeline d'ingestion
   - Points d'entrée et configuration

5. **`performance-optimization.md`** (Inclusion: always)
   - Optimisations base de données (index, pool de connexions)
   - Cache et batch processing pour embeddings
   - Optimisations LLM (streaming, context window)
   - Monitoring et métriques de performance

6. **`quick-commands.md`** (Inclusion: always)
   - Commandes rapides pour développement
   - Scripts de test et validation
   - Maintenance et nettoyage
   - Raccourcis Docker et monitoring

7. **`README.md`** (Inclusion: manual)
   - Documentation de la configuration steering
   - Guide d'utilisation des fichiers
   - Références et mise à jour

## 🎯 Bénéfices pour Kiro

Avec cette configuration, Kiro pourra :

### 🧠 Compréhension Contextuelle
- Connaître l'architecture StudyRAG (RAG local pour étudiants)
- Comprendre le stack technique (Ollama, Docling, PGVector)
- Respecter les priorités (local > cloud, UV > pip)

### 🛠️ Assistance Technique
- Proposer les bonnes commandes selon le contexte
- Diagnostiquer rapidement les problèmes courants
- Suggérer des optimisations appropriées
- Respecter la structure organisée du projet

### 🚀 Développement Efficace
- Utiliser les bons outils (UV, Rich, scripts dans `scripts/`)
- Tester avec les échantillons dans `test_samples/`
- Maintenir la compatibilité avec `docling_basics/`
- Suivre les conventions de code établies

### 🔧 Résolution de Problèmes
- Identifier les erreurs typiques (Ollama, DB, embeddings)
- Proposer des solutions étape par étape
- Fournir les commandes de diagnostic appropriées
- Guider vers les procédures de récupération

## 📖 Utilisation

### Inclusion Automatique
La plupart des fichiers sont inclus automatiquement dans toutes les conversations :
- Vue d'ensemble du projet
- Guidelines de développement  
- Guide de dépannage
- Optimisations de performance
- Commandes rapides

### Inclusion Conditionnelle
- `api-reference.md` s'active automatiquement pour les fichiers Python

### Inclusion Manuelle
- Utilise `#steering` pour référencer le README de configuration

## 🔄 Maintenance

Ces fichiers doivent être mis à jour quand :
- L'architecture du projet évolue
- De nouvelles conventions sont adoptées
- Des problèmes récurrents sont identifiés
- Des optimisations sont découvertes

## 🎉 Résultat

Kiro est maintenant parfaitement configuré pour t'assister sur StudyRAG ! Il comprend :
- Le contexte et les objectifs du projet
- Les technologies et outils utilisés
- Les bonnes pratiques à respecter
- Les commandes et procédures utiles
- Les solutions aux problèmes courants

Tu peux maintenant travailler avec Kiro en toute confiance, il aura toujours le bon contexte pour t'aider efficacement ! 🚀