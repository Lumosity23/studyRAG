# 🤖 Prompt Optimisé pour Kiro - Interface StudyRAG Moderne

## 🎯 Contexte du projet

Tu vas créer l'interface utilisateur moderne pour **StudyRAG**, un système RAG (Retrieval-Augmented Generation) d'analyse de documents académiques. L'interface doit ressembler aux chatbots modernes comme ChatGPT ou Claude, avec une expérience utilisateur fluide et professionnelle.

## 📁 Structure du projet

Tu travailles dans le dossier `frontend/` d'un monorepo Next.js 14 déjà initialisé avec :
- ✅ TypeScript configuré
- ✅ Tailwind CSS installé  
- ✅ ShadCN/UI prêt à utiliser
- ✅ Backend FastAPI fonctionnel sur http://localhost:8000

## 🎨 Design requis - Interface ChatBot moderne

### 🏗️ Layout principal
```
┌─────────────────────────────────────────────────────────┐
│ [StudyRAG Logo] [Chat] [Files]              [Settings] │ Header
├─────────────┬───────────────────────────────────────────┤
│             │                                           │
│  Sidebar    │           Zone Chat Centrale              │
│  (300px)    │                                           │
│             │                                           │
│ • New Chat  │  "Que veux-tu étudier aujourd'hui ?"     │
│ • Conv 1    │                                           │
│ • Conv 2    │  [Suggestions de prompts]                │
│ • Conv 3    │                                           │
│             │                                           │
│ [Settings]  │                                           │
├─────────────┴───────────────────────────────────────────┤
│           [📎] [Input de chat...] [➤]                   │ Input fixe
└─────────────────────────────────────────────────────────┘
```

### 📱 Composants requis

#### 1. **Sidebar gauche (rétractable)**
- **Header** : Logo StudyRAG + bouton collapse
- **New Chat** : Bouton proéminent pour nouvelle conversation
- **Liste conversations** : 
  - Titre auto-généré ou "New Chat"
  - Date/heure dernière activité
  - Bouton delete au hover
  - Conversation active mise en évidence
- **Footer** : Settings et profil utilisateur

#### 2. **Zone chat centrale**
- **État vide** (première visite) :
  - Message d'accueil centré : "Que veux-tu étudier aujourd'hui ?"
  - Suggestions cliquables :
    * "Analyse ce document PDF"
    * "Résume mes notes de cours" 
    * "Trouve des informations sur..."
    * "Compare ces deux documents"
- **État conversation active** :
  - Messages utilisateur : bulles bleues alignées à droite
  - Réponses IA : bulles grises alignées à gauche avec avatar StudyRAG
  - Sources citées sous chaque réponse IA
  - Boutons d'action (copy, regenerate, like/dislike)

#### 3. **Onglet File Manager**
- **Vue grille/liste** des documents uploadés
- **Informations par fichier** : nom, type, taille, date, statut processing
- **Actions** : view, download, delete, reindex
- **Zone drag & drop** proéminente en haut
- **Filtres** par type de fichier et statut
- **Barre de recherche** dans les fichiers

#### 4. **Barre de saisie (fixe en bas)**
- **Input large** et moderne (style ChatGPT)
- **Bouton attach** (📎) pour joindre des fichiers
- **Bouton send** (➤) avec états disabled/enabled
- **Auto-resize** selon le contenu
- **Support markdown** et raccourcis clavier
- **Indicateur de frappe** quand l'IA répond

## 🎨 Style et Design System

### Palette de couleurs
```css
/* Couleurs principales */
--primary: #3b82f6;      /* Bleu principal */
--primary-dark: #1d4ed8; /* Bleu foncé */
--gray-50: #f9fafb;      /* Arrière-plan clair */
--gray-100: #f3f4f6;     /* Bordures légères */
--gray-900: #111827;     /* Texte principal */
--sidebar-bg: #1f2937;   /* Arrière-plan sidebar */
```

### Typographie
- **Font principale** : Inter ou system font
- **Tailles** : 16px base, 14px secondaire, 12px captions
- **Poids** : 400 normal, 500 medium, 600 semibold

### Animations
- **Transitions fluides** : 200ms ease-in-out
- **Micro-interactions** : hover, focus, click feedback
- **Scroll smooth** dans les conversations
- **Fade in/out** pour les nouveaux messages

## 🔧 Spécifications techniques

### API Backend (http://localhost:8000)
```typescript
// Endpoints principaux
POST /api/v1/chat/message          // Envoyer message
GET  /api/v1/chat/conversations    // Liste conversations
POST /api/v1/documents/upload      // Upload fichiers
GET  /api/v1/database/documents    // Liste documents
WS   /ws/processing                // Mises à jour temps réel
```

### Types TypeScript
Utilise les types fournis dans `shared/types/TYPESCRIPT_TYPES.ts` :
- `ChatMessage`, `ConversationHistory`
- `Document`, `UploadResponse`
- `SearchRequest`, `SearchResponse`
- `WebSocketMessage`, `ProcessingUpdate`

### Structure des composants
```
src/
├── app/
│   ├── layout.tsx              # Layout principal
│   ├── page.tsx                # Page chat (défaut)
│   └── files/page.tsx          # Page file manager
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx         # Sidebar avec conversations
│   │   ├── Header.tsx          # Header avec onglets
│   │   └── MainLayout.tsx      # Layout wrapper
│   ├── chat/
│   │   ├── ChatInterface.tsx   # Interface chat principale
│   │   ├── MessageBubble.tsx   # Bulles de messages
│   │   ├── ChatInput.tsx       # Barre de saisie
│   │   ├── WelcomeScreen.tsx   # Écran d'accueil
│   │   ├── ConversationList.tsx # Liste conversations
│   │   └── SourceCitation.tsx  # Citations de sources
│   ├── files/
│   │   ├── FileManager.tsx     # Gestionnaire fichiers
│   │   ├── FileCard.tsx        # Carte de fichier
│   │   ├── DropZone.tsx        # Zone drag & drop
│   │   └── FileActions.tsx     # Actions sur fichiers
│   └── ui/                     # Composants ShadCN
└── lib/
    ├── api.ts                  # Client API
    ├── websocket.ts            # WebSocket client
    └── utils.ts                # Utilitaires
```

## 🚀 Fonctionnalités prioritaires

### Phase 1 : Interface de base
1. **Layout principal** avec sidebar rétractable
2. **Page chat** avec état vide élégant
3. **Barre de saisie** fonctionnelle
4. **Navigation** entre Chat et Files

### Phase 2 : Fonctionnalités chat
1. **Envoi/réception** de messages
2. **Historique** des conversations
3. **Gestion** des conversations (new, delete)
4. **Citations** de sources dans les réponses

### Phase 3 : File Manager
1. **Upload** avec drag & drop
2. **Liste** des documents avec actions
3. **Filtres** et recherche
4. **Statuts** de processing en temps réel

### Phase 4 : Temps réel
1. **WebSocket** pour mises à jour live
2. **Indicateurs** de traitement
3. **Notifications** toast
4. **États de chargement** fluides

## 📱 Responsive Design

### Breakpoints
- **Mobile** : < 768px (sidebar en drawer overlay)
- **Tablet** : 768-1024px (sidebar collapsible)
- **Desktop** : > 1024px (sidebar fixe)

### Adaptations mobiles
- **Bottom navigation** pour mobile
- **Swipe gestures** pour ouvrir sidebar
- **Touch targets** 44px minimum
- **Keyboard handling** pour input

## 🎯 Exemples d'interactions

### Nouveau chat
1. Utilisateur clique "New Chat"
2. Interface passe en mode vide avec suggestions
3. Utilisateur tape ou clique une suggestion
4. Message envoyé, réponse IA affichée avec sources

### Upload de fichier
1. Utilisateur va sur onglet "Files"
2. Drag & drop un PDF dans la zone
3. Progress bar s'affiche
4. WebSocket notifie du processing
5. Fichier apparaît dans la liste avec statut "Ready"

### Recherche dans documents
1. Utilisateur tape une question dans le chat
2. IA cherche dans les documents uploadés
3. Réponse avec citations des sources pertinentes
4. Liens cliquables vers les documents sources

## 🔍 Points d'attention

### Performance
- **Lazy loading** des conversations
- **Virtualisation** pour longues listes
- **Debounce** sur les inputs de recherche
- **Optimistic updates** pour l'UX

### Accessibilité
- **Navigation clavier** complète
- **Screen readers** support
- **Focus management** dans les modals
- **Contraste** WCAG AA compliant

### Sécurité
- **Validation** côté client et serveur
- **Sanitization** des messages
- **File type** validation
- **Size limits** respectés

## 🎨 Inspiration visuelle

Inspire-toi de ces interfaces modernes :
- **ChatGPT** : Layout général, barre de saisie
- **Claude** : Style des messages, sidebar
- **Notion** : File manager, organisation
- **Discord** : Navigation, états en ligne
- **Linear** : Design system, micro-interactions

## ✅ Critères de réussite

L'interface sera réussie si :
1. **Ressemble** aux chatbots modernes (ChatGPT/Claude)
2. **Fonctionne** parfaitement sur mobile et desktop
3. **Intègre** seamlessly avec l'API backend
4. **Offre** une expérience utilisateur fluide et intuitive
5. **Gère** les états de chargement et erreurs élégamment

## 🚀 Commencer maintenant

1. **Commence** par le layout principal et la sidebar
2. **Implémente** l'interface de chat avec état vide
3. **Ajoute** la barre de saisie et l'envoi de messages
4. **Intègre** le file manager avec drag & drop
5. **Connecte** le WebSocket pour le temps réel

**Crée une interface moderne, professionnelle et intuitive qui rivalise avec les meilleurs chatbots actuels !** 🎨✨