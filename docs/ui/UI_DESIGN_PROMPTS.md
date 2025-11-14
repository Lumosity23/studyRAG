# 🎨 Prompts UI Design pour StudyRAG - Interface ChatBot Moderne

## 🎯 Vision générale
Interface inspirée de ChatGPT/Claude avec une grande barre de chat centrale, sidebar pour l'historique des conversations, et onglet file manager intégré.

---

## 🤖 PROMPT POUR CLAUDE/GPT-4 (Développement complet)

```
Crée une interface moderne pour StudyRAG, un système RAG d'analyse de documents académiques, en utilisant Next.js 14, TypeScript, Tailwind CSS et ShadCN/UI.

DESIGN REQUIS - Interface type ChatGPT/Claude :

🎨 LAYOUT PRINCIPAL :
- Interface full-screen avec sidebar gauche rétractable
- Zone de chat centrale occupant tout l'espace disponible
- Barre de saisie fixe en bas, centrée et élégante
- Onglets en haut pour basculer entre "Chat" et "File Manager"

📱 SIDEBAR GAUCHE (300px, rétractable) :
- Header avec logo "StudyRAG" et bouton collapse
- Bouton "New Chat" proéminent en haut
- Liste des conversations avec :
  - Titre auto-généré ou "New Chat"
  - Date/heure de dernière activité
  - Bouton delete au hover
  - Conversation active mise en évidence
- Footer avec settings et user profile

💬 ZONE CHAT CENTRALE :
- État initial : Grande barre de chat centrée verticalement avec :
  - Message d'accueil : "Que veux-tu étudier aujourd'hui ?"
  - Suggestions de prompts (bulles cliquables) :
    * "Analyse ce document PDF"
    * "Résume mes notes de cours"
    * "Trouve des informations sur..."
    * "Compare ces deux documents"
- État conversation : Messages en scroll avec :
  - Messages utilisateur alignés à droite (style bubble)
  - Réponses IA alignées à gauche avec avatar StudyRAG
  - Sources citées sous chaque réponse IA
  - Boutons d'action (copy, regenerate, etc.)

🗂️ ONGLET FILE MANAGER :
- Vue en grille/liste des documents uploadés
- Informations par fichier : nom, type, taille, date, statut processing
- Actions : view, download, delete, reindex
- Zone drag & drop proéminente en haut
- Filtres par type de fichier et statut
- Barre de recherche dans les fichiers

⌨️ BARRE DE SAISIE (fixe en bas) :
- Input large et moderne (comme ChatGPT)
- Bouton attach file (📎)
- Bouton send (➤) 
- Indicateur de frappe
- Support markdown et raccourcis clavier
- Auto-resize selon le contenu

🎨 STYLE MODERNE :
- Palette : Blanc/gris clair avec accents bleus
- Typographie : Inter ou similaire
- Animations fluides (framer-motion)
- Mode sombre optionnel
- Responsive mobile-first
- Micro-interactions élégantes

SPÉCIFICATIONS TECHNIQUES :
- Backend API : http://localhost:8000
- WebSocket pour temps réel : ws://localhost:8000/ws/processing
- Types TypeScript fournis dans shared/types/
- Documentation API complète dans shared/docs/

FONCTIONNALITÉS PRIORITAIRES :
1. Interface chat avec historique
2. Upload de documents avec drag & drop
3. File manager avec actions CRUD
4. Mises à jour temps réel via WebSocket
5. Recherche sémantique intégrée au chat

Utilise les spécifications fournies dans :
- shared/docs/API_DOCUMENTATION_FOR_UI.md
- shared/docs/UI_QUICK_START_GUIDE.md  
- shared/types/TYPESCRIPT_TYPES.ts

Crée une interface professionnelle, intuitive et moderne qui rivalise avec les meilleurs chatbots actuels.
```

---

## 🎨 PROMPT POUR MIDJOURNEY/DALL-E (Design visuel)

```
Modern chat interface design for StudyRAG academic document analysis app, inspired by ChatGPT and Claude UI:

Main layout: Clean white interface with collapsible left sidebar (300px), large central chat area, fixed bottom input bar. Top tabs for "Chat" and "File Manager" modes.

Left sidebar: Dark gray (#1f2937) with "StudyRAG" logo, "New Chat" button, conversation history list with timestamps, settings at bottom.

Central chat area: When empty - large centered input with "Que veux-tu étudier aujourd'hui?" placeholder and suggestion bubbles below. When active - chat messages with user messages right-aligned (blue bubbles), AI responses left-aligned with avatar, source citations below AI responses.

File manager tab: Grid view of uploaded documents with thumbnails, drag-and-drop zone at top, file actions (view/delete/reindex), search bar, filter buttons.

Bottom input bar: Wide rounded input field (like ChatGPT), attach button (📎), send button (➤), typing indicator.

Style: Modern, clean, professional. Color palette: whites, light grays (#f9fafb), blue accents (#3b82f6), dark sidebar. Typography: Inter font. Subtle shadows and rounded corners. Mobile responsive.

UI inspiration: ChatGPT, Claude, Notion, Linear. Academic/professional feel with modern chat UX.

--ar 16:10 --style modern --v 6
```

---

## 🖼️ PROMPT POUR FIGMA/DESIGN TOOLS

```
Crée un design system et maquettes pour StudyRAG - Interface de chat académique moderne

COMPOSANTS À DESIGNER :

1. LAYOUT PRINCIPAL
- Sidebar 300px (collapsible)
- Zone centrale responsive
- Barre de saisie fixe 60px hauteur
- Header avec onglets Chat/Files

2. SIDEBAR COMPONENTS
- Logo StudyRAG + collapse button
- "New Chat" button (primary blue)
- Conversation item (hover states)
- User profile section

3. CHAT COMPONENTS  
- Message bubble utilisateur (blue, right-aligned)
- Message bubble IA (gray, left-aligned, with avatar)
- Source citation cards
- Suggestion pills (empty state)
- Welcome message centered

4. FILE MANAGER COMPONENTS
- Document card (thumbnail + metadata)
- Drag & drop zone (dashed border, hover states)
- File actions dropdown
- Status badges (processing, ready, failed)
- Search input with filters

5. INPUT COMPONENTS
- Chat input (auto-resize, placeholder)
- Attach button with file picker
- Send button (disabled/enabled states)
- Typing indicator

DESIGN TOKENS :
- Colors: Primary #3b82f6, Gray scale, Success #10b981, Error #ef4444
- Typography: Inter (16px base, 14px secondary, 12px captions)
- Spacing: 4px grid system
- Radius: 8px cards, 20px buttons, 12px inputs
- Shadows: Subtle elevation system

STATES À INCLURE :
- Empty chat state
- Active conversation
- Loading states
- Error states  
- Mobile responsive breakpoints

Inspiration : ChatGPT, Claude, Notion, Discord, Slack
Style : Moderne, professionnel, académique, accessible
```

---

## 💻 PROMPT POUR CURSOR/CODEIUM (Développement assisté)

```
Développe l'interface StudyRAG avec cette architecture :

STRUCTURE NEXT.JS :
```
src/
├── app/
│   ├── layout.tsx          # Layout principal avec sidebar
│   ├── page.tsx            # Page chat par défaut
│   └── files/page.tsx      # Page file manager
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx     # Sidebar avec conversations
│   │   ├── Header.tsx      # Header avec onglets
│   │   └── Layout.tsx      # Layout wrapper
│   ├── chat/
│   │   ├── ChatInterface.tsx    # Zone de chat principale
│   │   ├── MessageBubble.tsx    # Bulles de messages
│   │   ├── ChatInput.tsx        # Barre de saisie
│   │   ├── WelcomeScreen.tsx    # Écran d'accueil
│   │   └── ConversationList.tsx # Liste conversations
│   ├── files/
│   │   ├── FileManager.tsx      # Gestionnaire de fichiers
│   │   ├── FileCard.tsx         # Carte de fichier
│   │   ├── DropZone.tsx         # Zone drag & drop
│   │   └── FileActions.tsx      # Actions sur fichiers
│   └── ui/                      # Composants ShadCN
└── lib/
    ├── api.ts              # Client API
    ├── websocket.ts        # WebSocket client
    └── types.ts            # Types TypeScript
```

FONCTIONNALITÉS CLÉS :
1. Chat interface avec état vide élégant
2. Sidebar rétractable avec conversations
3. File manager avec drag & drop
4. WebSocket pour temps réel
5. Responsive design mobile-first

STYLE REQUIREMENTS :
- ShadCN/UI components
- Tailwind CSS classes
- Framer Motion animations
- Mode sombre/clair
- Accessibilité WCAG

API ENDPOINTS :
- POST /api/v1/chat/message
- GET /api/v1/chat/conversations  
- POST /api/v1/documents/upload
- GET /api/v1/database/documents
- WS /ws/processing

Utilise les types fournis dans shared/types/TYPESCRIPT_TYPES.ts
Suis les spécifications dans shared/docs/API_DOCUMENTATION_FOR_UI.md

Crée une interface moderne, performante et intuitive.
```

---

## 🎯 PROMPT POUR V0.DEV (Génération rapide)

```
Crée une interface de chat moderne pour StudyRAG (système d'analyse de documents académiques) avec :

Layout : Sidebar gauche + zone chat centrale + barre de saisie fixe en bas

Sidebar (300px, rétractable) :
- Logo "StudyRAG" en haut
- Bouton "New Chat" 
- Liste des conversations avec dates
- Bouton settings en bas

Zone centrale :
- État vide : Message "Que veux-tu étudier aujourd'hui ?" centré avec suggestions cliquables
- État actif : Messages en bulles (utilisateur à droite en bleu, IA à gauche en gris)
- Sources citées sous les réponses IA

Barre de saisie (fixe en bas) :
- Input large avec placeholder
- Bouton attach (📎) et send (➤)
- Auto-resize du textarea

Onglets en haut : "Chat" et "File Manager"

File Manager :
- Grille de documents avec thumbnails
- Zone drag & drop en haut
- Actions : view, delete, reindex
- Statuts : processing, ready, failed

Style : Moderne, inspiré ChatGPT/Claude, couleurs neutres avec accents bleus, responsive

Tech : Next.js 14, TypeScript, Tailwind CSS, ShadCN/UI

Génère le code complet avec composants modulaires.
```

---

## 🚀 PROMPT POUR BOLT.NEW/STACKBLITZ

```
Crée StudyRAG - Interface de chat académique moderne

Description : Système RAG pour analyser des documents académiques avec interface type ChatGPT

Fonctionnalités :
✅ Chat interface avec sidebar conversations
✅ File manager avec drag & drop
✅ Upload de documents (PDF, DOCX, etc.)
✅ Recherche sémantique intégrée
✅ Mises à jour temps réel

Tech Stack :
- Next.js 14 + TypeScript
- Tailwind CSS + ShadCN/UI  
- Framer Motion (animations)
- React Query (state management)

Layout requis :
- Sidebar gauche rétractable (conversations)
- Zone chat centrale responsive
- Onglets Chat/Files en header
- Barre de saisie fixe en bas
- File manager avec grille de documents

Design :
- Style moderne type ChatGPT/Claude
- Palette : blanc/gris avec accents bleus
- Responsive mobile-first
- Mode sombre optionnel

API Backend : http://localhost:8000 (FastAPI)
WebSocket : ws://localhost:8000/ws/processing

Crée une interface professionnelle et intuitive pour l'analyse de documents académiques.
```

---

## 📱 PROMPT POUR INTERFACE MOBILE

```
Adapte l'interface StudyRAG pour mobile avec :

Navigation : Bottom tab bar (Chat, Files, Settings)
Chat : Full screen avec header collapsible
Sidebar : Drawer overlay (swipe depuis la gauche)
Input : Sticky bottom avec keyboard handling
Files : Liste verticale avec swipe actions

Interactions mobiles :
- Swipe pour ouvrir sidebar
- Pull to refresh conversations
- Long press pour actions contextuelles
- Haptic feedback sur actions importantes

Responsive breakpoints :
- Mobile : < 768px (single column)
- Tablet : 768-1024px (sidebar overlay)
- Desktop : > 1024px (sidebar fixe)

Optimisations :
- Touch targets 44px minimum
- Scroll momentum natif
- Keyboard avoidance
- Offline state handling
```

Ces prompts couvrent tous les aspects de votre vision ! Choisissez celui qui correspond à l'outil que vous voulez utiliser. L'interface ressemblera exactement aux chatbots modernes avec votre twist académique ! 🎨✨