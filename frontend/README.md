# StudyRAG - Interface React

Interface utilisateur moderne et dynamique pour StudyRAG, construite avec Next.js, React, et ShadCN UI.

## 🎨 Caractéristiques

### Design Moderne
- **Thème sombre par défaut** avec système de thèmes personnalisables
- **Couleurs pastel** avec 5 palettes de couleurs différentes
- **Composants ShadCN UI** pour une expérience utilisateur cohérente
- **Animations Framer Motion** pour des transitions fluides
- **Design responsive** qui s'adapte à tous les écrans

### Fonctionnalités

#### 🎨 **Système de Thèmes**
- **5 palettes de couleurs** : Default, Rose, Ocean, Forest, Lavender, Sunset
- **Mode sombre/clair** avec détection automatique du système
- **Couleurs pastel** harmonieuses pour chaque thème
- **Changement de thème en temps réel**

#### 📱 **Interface Modulaire**
- **Sidebar rétractable** avec navigation fluide
- **Top bar épurée** avec actions rapides
- **Zone de chat centrée** et minimaliste
- **Zone de prompt agrandie** pour une meilleure expérience

#### 💬 **Chat Dynamique**
- **Messages en temps réel** avec animations
- **Bulles de chat** stylisées selon le rôle
- **Indicateur de frappe** animé
- **Citations des sources** avec scores de similarité
- **Formatage Markdown** pour les messages

#### 🗂️ **Gestion des Conversations**
- **Historique des conversations** avec recherche
- **Création/suppression** de conversations
- **Titre automatique** basé sur le contenu
- **Persistance locale** avec Zustand

## 🚀 Installation et Démarrage

### Prérequis
- Node.js 18+ 
- npm ou yarn
- Backend StudyRAG en cours d'exécution sur le port 8000

### Installation Rapide

1. **Installer les dépendances** :
```bash
cd frontend
npm install
```

2. **Démarrer le serveur de développement** :
```bash
npm run dev
```

3. **Ou utiliser le script Python** :
```bash
python start_frontend.py
```

4. **Ouvrir dans le navigateur** :
   - Interface React : http://localhost:3000
   - Le backend doit tourner sur : http://localhost:8000

## 🎨 Système de Thèmes

### Palettes Disponibles

#### 🌸 **Rose** (`theme-rose`)
- Rose pastel, bleu ciel, vert menthe, violet lavande
- Parfait pour une ambiance douce et féminine

#### 🌊 **Ocean** (`theme-ocean`)
- Bleu océan, vert aqua, rose corail, violet profond
- Idéal pour une atmosphère marine et apaisante

#### 🌲 **Forest** (`theme-forest`)
- Vert forêt, bleu ciel, rose poudré, orange automne
- Excellent pour une ambiance naturelle et zen

#### 💜 **Lavender** (`theme-lavender`)
- Violet lavande, rose pâle, bleu pervenche, vert sauge
- Parfait pour une atmosphère relaxante et créative

#### 🌅 **Sunset** (`theme-sunset`)
- Orange coucher de soleil, rose corail, jaune doré, violet crépuscule
- Idéal pour une ambiance chaleureuse et énergisante

### Utilisation des Thèmes

```typescript
import { useAppStore } from '@/lib/store'

function ThemeSelector() {
  const { colorTheme, setColorTheme } = useAppStore()
  
  return (
    <select 
      value={colorTheme} 
      onChange={(e) => setColorTheme(e.target.value)}
    >
      <option value="default">Défaut</option>
      <option value="rose">Rose</option>
      <option value="ocean">Océan</option>
      <option value="forest">Forêt</option>
      <option value="lavender">Lavande</option>
      <option value="sunset">Coucher de soleil</option>
    </select>
  )
}
```

## 🏗️ Architecture

### Structure des Dossiers
```
frontend/
├── app/                    # App Router Next.js
│   ├── globals.css        # Styles globaux et thèmes
│   ├── layout.tsx         # Layout principal
│   └── page.tsx           # Page d'accueil
├── components/
│   ├── ui/                # Composants ShadCN UI
│   ├── layout/            # Composants de layout
│   ├── chat/              # Composants de chat
│   └── providers/         # Providers React
├── lib/
│   ├── store.ts           # Store Zustand
│   └── utils.ts           # Utilitaires
└── ...
```

### Technologies Utilisées
- **Next.js 14** - Framework React avec App Router
- **React 18** - Bibliothèque UI avec hooks modernes
- **TypeScript** - Typage statique pour plus de robustesse
- **Tailwind CSS** - Framework CSS utilitaire
- **ShadCN UI** - Composants UI modernes et accessibles
- **Framer Motion** - Animations et transitions fluides
- **Zustand** - Gestion d'état simple et performante
- **Lucide React** - Icônes modernes et cohérentes

## 🔧 Développement

### Scripts Disponibles
```bash
npm run dev      # Serveur de développement
npm run build    # Build de production
npm run start    # Serveur de production
npm run lint     # Linting du code
```

### Ajout de Nouveaux Composants

1. **Créer le composant** :
```bash
# Exemple pour un nouveau composant UI
touch components/ui/new-component.tsx
```

2. **Utiliser les conventions ShadCN** :
```typescript
import * as React from "react"
import { cn } from "@/lib/utils"

interface NewComponentProps {
  className?: string
  children: React.ReactNode
}

const NewComponent = React.forwardRef<
  HTMLDivElement,
  NewComponentProps
>(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("base-styles", className)}
    {...props}
  >
    {children}
  </div>
))

NewComponent.displayName = "NewComponent"

export { NewComponent }
```

### Ajout de Nouveaux Thèmes

1. **Définir les couleurs dans `globals.css`** :
```css
.theme-custom {
  --primary: 280 81% 60%;
  --primary-foreground: 280 100% 98%;
  --pastel-pink: 320 100% 95%;
  --pastel-blue: 200 100% 95%;
  /* ... autres couleurs */
}
```

2. **Ajouter au store** :
```typescript
export type ColorTheme = 'default' | 'rose' | 'ocean' | 'forest' | 'lavender' | 'sunset' | 'custom'
```

## 🔗 Intégration Backend

L'interface communique avec le backend FastAPI via :

### Proxy Next.js
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

### API Calls
```typescript
// Exemple d'appel API
const sendMessage = async (message: string) => {
  const response = await fetch('/api/v1/chat/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: currentId })
  })
  return response.json()
}
```

## 🎯 Fonctionnalités Futures

- [ ] **Gestionnaire de fichiers** intégré
- [ ] **Calendrier** avec planification
- [ ] **Mode collaboratif** multi-utilisateurs
- [ ] **Thèmes personnalisés** créés par l'utilisateur
- [ ] **Raccourcis clavier** avancés
- [ ] **Mode hors ligne** avec synchronisation
- [ ] **Plugins** et extensions

## 🤝 Contribution

1. Respectez les conventions de nommage ShadCN UI
2. Utilisez TypeScript pour tous les nouveaux composants
3. Testez sur différentes tailles d'écran
4. Documentez les nouveaux composants
5. Suivez les patterns Zustand pour la gestion d'état

## 📄 Licence

Ce projet utilise la même licence que StudyRAG principal.