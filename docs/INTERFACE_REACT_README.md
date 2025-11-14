# 🎨 StudyRAG - Interface React Moderne

Interface utilisateur complète et moderne pour StudyRAG, construite avec **Next.js**, **React**, **ShadCN UI** et **Tailwind CSS**.

## ✨ Fonctionnalités

### 🎨 **Design Moderne**
- **Thème sombre par défaut** avec système de thèmes personnalisables
- **5 palettes de couleurs pastel** harmonieuses
- **Composants ShadCN UI** pour une expérience utilisateur cohérente
- **Animations Framer Motion** pour des transitions fluides
- **Design responsive** qui s'adapte à tous les écrans

### 🏗️ **Architecture Modulaire**
- **Sidebar rétractable** avec navigation fluide
- **Top bar épurée** avec actions rapides
- **Zone de chat centrée** et minimaliste
- **Zone de prompt agrandie** pour une meilleure expérience

### 🎨 **Système de Thèmes Pastel**

#### 🌸 **Rose** - Douceur et féminité
- Rose pastel, bleu ciel, vert menthe, violet lavande

#### 🌊 **Ocean** - Atmosphère marine
- Bleu océan, vert aqua, rose corail, violet profond

#### 🌲 **Forest** - Ambiance naturelle
- Vert forêt, bleu ciel, rose poudré, orange automne

#### 💜 **Lavender** - Relaxation et créativité
- Violet lavande, rose pâle, bleu pervenche, vert sauge

#### 🌅 **Sunset** - Chaleur et énergie
- Orange coucher de soleil, rose corail, jaune doré, violet crépuscule

## 🚀 Installation et Démarrage

### **Option 1 : Installation Automatique (Recommandée)**

```bash
# Installation complète
python install_frontend.py

# Démarrage complet (Backend + Frontend)
python start_studyrag_full.py
```

### **Option 2 : Installation Manuelle**

```bash
# 1. Installer les dépendances
cd frontend
npm install

# 2. Démarrer le backend (terminal 1)
python start_studyrag.py

# 3. Démarrer l'interface (terminal 2)
cd frontend
npm run dev
```

### **Accès**
- 📱 **Interface React** : http://localhost:3000
- 🔧 **API Backend** : http://localhost:8000
- 📚 **Documentation** : http://localhost:8000/docs

## 🎯 Fonctionnalités de l'Interface

### 💬 **Chat Dynamique**
- **Messages en temps réel** avec animations
- **Bulles de chat** stylisées selon le rôle (utilisateur/assistant)
- **Indicateur de frappe** animé pendant les réponses
- **Citations des sources** avec scores de similarité
- **Formatage Markdown** pour les messages enrichis

### 🗂️ **Gestion des Conversations**
- **Historique complet** des conversations
- **Création/suppression** facile de conversations
- **Titre automatique** basé sur le premier message
- **Persistance locale** avec Zustand
- **Navigation fluide** entre les conversations

### 📁 **Sidebar Moderne**
- **Navigation avec icônes** Lucide React
- **Actions rapides** : Documents, Recherche, Calendrier, Gestionnaire
- **Animation de glissement** fluide
- **Mode rétractable** pour plus d'espace

### 🔝 **Top Bar Épurée**
- **Titre dynamique** de la conversation active
- **Actions rapides centrées** pour un accès facile
- **Indicateur de connexion** en temps réel
- **Sélecteur de thème** intégré

## 🛠️ Technologies Utilisées

### **Frontend**
- **Next.js 14** - Framework React avec App Router
- **React 18** - Bibliothèque UI avec hooks modernes
- **TypeScript** - Typage statique pour plus de robustesse
- **Tailwind CSS** - Framework CSS utilitaire
- **ShadCN UI** - Composants UI modernes et accessibles

### **Animations & UX**
- **Framer Motion** - Animations et transitions fluides
- **Lucide React** - Icônes modernes et cohérentes
- **React Hot Toast** - Notifications élégantes

### **État & Données**
- **Zustand** - Gestion d'état simple et performante
- **Persistance locale** - Sauvegarde automatique des préférences

## 📁 Structure du Projet

```
frontend/
├── app/                    # App Router Next.js
│   ├── globals.css        # Styles globaux et thèmes
│   ├── layout.tsx         # Layout principal avec providers
│   └── page.tsx           # Page d'accueil
├── components/
│   ├── ui/                # Composants ShadCN UI
│   │   ├── button.tsx     # Boutons avec variantes
│   │   ├── input.tsx      # Champs de saisie
│   │   ├── textarea.tsx   # Zone de texte
│   │   ├── dialog.tsx     # Modales
│   │   └── ...
│   ├── layout/            # Composants de layout
│   │   ├── main-layout.tsx # Layout principal
│   │   ├── sidebar.tsx    # Barre latérale
│   │   └── top-bar.tsx    # Barre supérieure
│   ├── chat/              # Composants de chat
│   │   ├── chat-area.tsx  # Zone de chat principale
│   │   └── welcome-screen.tsx # Écran d'accueil
│   └── providers/         # Providers React
│       └── theme-provider.tsx # Gestion des thèmes
├── lib/
│   ├── store.ts           # Store Zustand global
│   └── utils.ts           # Utilitaires et helpers
├── package.json           # Dépendances et scripts
├── tailwind.config.js     # Configuration Tailwind
├── next.config.js         # Configuration Next.js
└── tsconfig.json          # Configuration TypeScript
```

## 🎨 Personnalisation des Thèmes

### **Utilisation dans les Composants**

```typescript
import { useAppStore } from '@/lib/store'

function MonComposant() {
  const { colorTheme, setColorTheme } = useAppStore()
  
  return (
    <div className="bg-pastel-pink p-4 rounded-lg">
      <button 
        onClick={() => setColorTheme('ocean')}
        className="bg-gradient-to-r from-pastel-blue to-pastel-green"
      >
        Changer de thème
      </button>
    </div>
  )
}
```

### **Classes CSS Disponibles**

```css
/* Couleurs pastel pour chaque thème */
.bg-pastel-pink     /* Rose pastel */
.bg-pastel-blue     /* Bleu pastel */
.bg-pastel-green    /* Vert pastel */
.bg-pastel-purple   /* Violet pastel */
.bg-pastel-orange   /* Orange pastel */
.bg-pastel-yellow   /* Jaune pastel */

/* Gradients prédéfinis */
.gradient-bg        /* Gradient multicolore */
.chat-bubble-user   /* Style bulle utilisateur */
.chat-bubble-assistant /* Style bulle assistant */
```

## 🔧 Scripts Disponibles

```bash
# Développement
npm run dev         # Serveur de développement avec hot reload
npm run build       # Build de production optimisé
npm run start       # Serveur de production
npm run lint        # Vérification du code avec ESLint

# Scripts Python
python install_frontend.py      # Installation automatique
python start_frontend.py        # Démarrage frontend seul
python start_studyrag_full.py   # Démarrage complet (backend + frontend)
```

## 🔗 Intégration Backend

### **Proxy Automatique**
L'interface utilise un proxy Next.js pour rediriger les appels API :

```javascript
// next.config.js
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:8000/api/:path*',
    },
  ]
}
```

### **Appels API**
```typescript
// Exemple d'appel API
const sendMessage = async (message: string) => {
  const response = await fetch('/api/v1/chat/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      message, 
      conversation_id: currentConversationId 
    })
  })
  return response.json()
}
```

## 🎯 Fonctionnalités Futures

- [ ] **Gestionnaire de fichiers** intégré avec drag & drop
- [ ] **Calendrier** avec planification et rappels
- [ ] **Mode collaboratif** multi-utilisateurs
- [ ] **Thèmes personnalisés** créés par l'utilisateur
- [ ] **Raccourcis clavier** avancés (Ctrl+K, etc.)
- [ ] **Mode hors ligne** avec synchronisation
- [ ] **Plugins** et système d'extensions
- [ ] **Export** des conversations en PDF/Markdown

## 🐛 Dépannage

### **Problèmes Courants**

#### **Port 3000 déjà utilisé**
```bash
# Trouver le processus
lsof -ti:3000
# Tuer le processus
kill -9 $(lsof -ti:3000)
```

#### **Erreurs de dépendances**
```bash
# Nettoyer et réinstaller
rm -rf frontend/node_modules frontend/package-lock.json
cd frontend && npm install --legacy-peer-deps
```

#### **Problèmes de proxy API**
- Vérifiez que le backend tourne sur le port 8000
- Vérifiez la configuration dans `next.config.js`
- Consultez les logs du navigateur (F12)

### **Logs de Développement**
- **Frontend** : Console du navigateur (F12)
- **Backend** : Terminal du serveur FastAPI
- **Network** : Onglet Network des DevTools

## 🤝 Contribution

### **Ajout de Nouveaux Composants**

1. **Créer le composant** dans le bon dossier
2. **Suivre les conventions ShadCN UI**
3. **Utiliser TypeScript** pour le typage
4. **Ajouter les animations** Framer Motion si nécessaire
5. **Tester** sur différentes tailles d'écran

### **Ajout de Nouveaux Thèmes**

1. **Définir les couleurs** dans `globals.css`
2. **Ajouter au type** `ColorTheme` dans le store
3. **Tester** l'harmonie des couleurs
4. **Documenter** le nouveau thème

## 📄 Licence

Ce projet utilise la même licence que StudyRAG principal.

---

## 🎉 Résultat Final

Vous avez maintenant une **interface React moderne et complète** pour StudyRAG avec :

✅ **Design moderne** avec thèmes pastel  
✅ **Architecture modulaire** et extensible  
✅ **Animations fluides** et transitions naturelles  
✅ **Gestion d'état** réactive avec Zustand  
✅ **Intégration backend** transparente  
✅ **Expérience utilisateur** optimisée  

**Démarrez avec** : `python start_studyrag_full.py` et ouvrez http://localhost:3000 ! 🚀