# 🔧 Guide de Résolution des Problèmes StudyRAG

## 🚨 Problèmes Identifiés

1. **Fonction `loadConversation` manquante** dans la sidebar
2. **Backend non accessible** (Connection Refused)
3. **Erreur 400 Bad Request** sur `/api/v1/chat/message`
4. **Attributs serveur supplémentaires** (warnings React)

## ⚡ Solution Rapide (Recommandée)

### Étape 1: Diagnostic Automatique
```bash
python diagnose_and_fix.py
```

### Étape 2: Démarrage Complet
```bash
python start_studyrag_complete.py
```

## 🔧 Solution Manuelle Détaillée

### 1. Corriger l'Erreur TypeScript (Déjà fait)
La fonction `loadConversation` manquante a été corrigée dans `sidebar.tsx`.

### 2. Configurer l'Environnement
```bash
# Copier la configuration
cp .env.example .env

# Éditer si nécessaire
nano .env
```

### 3. Démarrer le Backend
```bash
# Option A: Script automatique
python start_backend_only.py

# Option B: Manuel
python -m app.main
```

### 4. Démarrer le Frontend
```bash
# Option A: Script automatique
python start_frontend_dev.py

# Option B: Manuel
cd frontend
npm install  # si nécessaire
npm run dev
```

### 5. Vérifier les Connexions
```bash
python verify_api_routes.py
```

## 🔍 Diagnostic des Erreurs Spécifiques

### Erreur: "Connection Refused"
**Cause**: Backend non démarré
**Solution**:
```bash
# Vérifier si le backend tourne
curl http://localhost:8000/health

# Si non, démarrer
python -m app.main
```

### Erreur: "400 Bad Request" sur chat
**Cause**: Format de requête incorrect ou backend non configuré
**Solution**:
1. Vérifier que le backend est démarré
2. Vérifier les logs backend pour voir l'erreur exacte
3. Tester avec une requête simple :
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```

### Erreur: "loadConversation is not defined"
**Cause**: Fonction manquante dans sidebar.tsx
**Solution**: Déjà corrigée automatiquement

### Warnings React "Extra attributes"
**Cause**: Hydratation SSR/CSR
**Solution**: Ces warnings sont généralement bénins en développement

## 🎯 Vérifications Post-Correction

### 1. Services Accessibles
- ✅ Backend: http://localhost:8000/health
- ✅ Frontend: http://localhost:3000
- ✅ API Docs: http://localhost:8000/docs

### 2. Fonctionnalités UI
- ✅ Prompt centré s'affiche
- ✅ Suggestions apparaissent
- ✅ Transition fluide vers conversation
- ✅ Sidebar avec conversations
- ✅ Upload de documents

### 3. API Endpoints
```bash
# Test rapide des routes principales
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/database/stats
curl -X POST http://localhost:8000/api/v1/chat/message -H "Content-Type: application/json" -d '{"message":"test"}'
```

## 🚀 Démarrage Recommandé

Pour éviter tous ces problèmes à l'avenir :

```bash
# 1. Diagnostic initial (une fois)
python diagnose_and_fix.py

# 2. Démarrage quotidien
python start_studyrag_complete.py
```

## 📞 Si les Problèmes Persistent

### Logs à Vérifier
1. **Console backend** : Erreurs Python/FastAPI
2. **Console frontend** : Erreurs React/Next.js
3. **DevTools navigateur** : Erreurs réseau/JavaScript

### Commandes de Debug
```bash
# Backend verbose
DEBUG=true python -m app.main

# Frontend verbose
cd frontend && npm run dev

# Test des routes
python verify_api_routes.py

# Test complet
python test_ui_complete.py
```

### Reset Complet (Dernier Recours)
```bash
# Nettoyer les caches
rm -rf frontend/.next
rm -rf frontend/node_modules
rm -rf __pycache__

# Réinstaller
cd frontend && npm install
uv sync

# Redémarrer
python start_studyrag_complete.py
```

---

**Note**: La plupart de ces problèmes viennent du fait que les services ne sont pas démarrés dans le bon ordre. Le script `start_studyrag_complete.py` résout cela automatiquement.