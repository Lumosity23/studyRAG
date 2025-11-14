# StudyRAG API Documentation pour UI Agent

## 🎯 Vue d'ensemble

Cette documentation est destinée à un agent UI qui va créer une interface moderne avec Next.js et ShadCN/UI pour l'application StudyRAG (système RAG pour l'analyse de documents académiques).

**Backend:** FastAPI sur `http://localhost:8000`
**Frontend suggéré:** Next.js + TypeScript + ShadCN/UI + Tailwind CSS

## 🏗️ Architecture API

### Base URL
```
http://localhost:8000
```

### Headers requis
```typescript
{
  "Content-Type": "application/json",
  "Accept": "application/json"
}
```

### Gestion des erreurs
Toutes les erreurs suivent le format :
```typescript
interface APIError {
  detail: string;
  error_code?: string;
  timestamp?: string;
}
```

## 📚 Endpoints API détaillés

### 1. 🏥 Health & Status

#### GET `/health`
**Description:** Vérification de l'état du serveur
**Réponse:**
```typescript
interface HealthResponse {
  status: "healthy" | "unhealthy";
  timestamp: string;
  version: string;
  services: {
    database: "up" | "down";
    vector_db: "up" | "down";
    ollama: "up" | "down";
  };
}
```

**Exemple d'utilisation UI:**
- Indicateur de statut dans la barre de navigation
- Page de monitoring système
- Vérification avant actions critiques

---

### 2. 📄 Gestion des Documents

#### POST `/api/v1/documents/upload`
**Description:** Upload de documents avec support multi-fichiers
**Content-Type:** `multipart/form-data`
**Body:**
```typescript
FormData {
  files: File[]; // Fichiers à uploader
}
```

**Réponse:**
```typescript
interface UploadResponse {
  uploaded_files: {
    filename: string;
    document_id: string;
    file_size: number;
    file_type: string;
    status: "uploaded" | "processing" | "failed";
    task_id?: string; // Pour suivre le traitement
  }[];
  total_uploaded: number;
  failed_uploads: {
    filename: string;
    error: string;
  }[];
}
```

**Composants UI suggérés:**
- Zone de drag & drop avec `react-dropzone`
- Barre de progression par fichier
- Liste des fichiers avec statuts
- Notifications toast pour succès/erreurs

#### GET `/api/v1/documents/status/{task_id}`
**Description:** Suivi du statut de traitement d'un document
**Réponse:**
```typescript
interface ProcessingStatus {
  task_id: string;
  document_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number; // 0-100
  message: string;
  started_at: string;
  completed_at?: string;
  error_details?: string;
}
```

---

### 3. 🗄️ Base de données et gestion

#### GET `/api/v1/database/documents`
**Description:** Liste tous les documents avec pagination
**Query Parameters:**
```typescript
interface DocumentsQuery {
  page?: number; // défaut: 1
  limit?: number; // défaut: 20, max: 100
  status?: "pending" | "processing" | "completed" | "failed";
  file_type?: "pdf" | "docx" | "html" | "txt" | "md";
  sort_by?: "upload_date" | "filename" | "file_size";
  sort_order?: "asc" | "desc";
  search?: string; // recherche dans les noms de fichiers
}
```

**Réponse:**
```typescript
interface DocumentsListResponse {
  documents: Document[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

interface Document {
  id: string;
  filename: string;
  file_type: "pdf" | "docx" | "html" | "txt" | "md";
  file_size: number;
  upload_date: string; // ISO 8601
  processing_status: "pending" | "processing" | "completed" | "failed";
  chunk_count: number;
  embedding_model: string;
  metadata: Record<string, any>;
  error_message?: string;
}
```

**Composants UI suggérés:**
- Table avec tri et filtres (ShadCN Table)
- Pagination (ShadCN Pagination)
- Badges de statut colorés
- Barre de recherche avec debounce

#### GET `/api/v1/database/documents/{document_id}`
**Description:** Détails d'un document spécifique
**Réponse:** `Document` (voir interface ci-dessus)

#### DELETE `/api/v1/database/documents/{document_id}`
**Description:** Suppression d'un document et de ses données associées
**Réponse:**
```typescript
interface DeleteResponse {
  message: string;
  document_id: string;
  deleted_chunks: number;
}
```

#### POST `/api/v1/database/reindex/{document_id}`
**Description:** Réindexation d'un document avec le modèle d'embedding actuel
**Réponse:**
```typescript
interface ReindexResponse {
  message: string;
  document_id: string;
  task_id: string;
  new_embedding_model: string;
}
```

#### GET `/api/v1/database/stats`
**Description:** Statistiques de la base de données
**Réponse:**
```typescript
interface DatabaseStats {
  total_documents: number;
  total_chunks: number;
  total_size_bytes: number;
  documents_by_status: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  documents_by_type: {
    pdf: number;
    docx: number;
    html: number;
    txt: number;
    md: number;
  };
  embedding_models: {
    model_name: string;
    document_count: number;
  }[];
}
```

---

### 4. 🔍 Recherche sémantique

#### POST `/api/v1/search`
**Description:** Recherche sémantique dans les documents
**Body:**
```typescript
interface SearchRequest {
  query: string;
  limit?: number; // défaut: 10, max: 50
  min_score?: number; // défaut: 0.0, seuil de pertinence
  document_ids?: string[]; // limiter à certains documents
  file_types?: ("pdf" | "docx" | "html" | "txt" | "md")[];
}
```

**Réponse:**
```typescript
interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
}

interface SearchResult {
  document_id: string;
  document_filename: string;
  chunk_id: string;
  content: string;
  score: number; // 0.0 à 1.0
  metadata: {
    page_number?: number;
    section?: string;
    [key: string]: any;
  };
  highlighted_content?: string; // contenu avec surlignage
}
```

**Composants UI suggérés:**
- Barre de recherche avec suggestions
- Résultats avec highlighting
- Filtres par type de fichier
- Tri par pertinence/date
- Pagination des résultats

---

### 5. 💬 Chat avec l'IA

#### POST `/api/v1/chat/message`
**Description:** Envoi d'un message au chat IA
**Body:**
```typescript
interface ChatRequest {
  message: string;
  conversation_id?: string; // pour continuer une conversation
  context_documents?: string[]; // IDs des documents pour le contexte
  model_settings?: {
    temperature?: number; // 0.0 à 1.0
    max_tokens?: number;
    top_p?: number;
  };
}
```

**Réponse:**
```typescript
interface ChatResponse {
  message: string;
  conversation_id: string;
  response_time_ms: number;
  sources: {
    document_id: string;
    document_filename: string;
    chunk_content: string;
    relevance_score: number;
  }[];
  model_used: string;
}
```

#### GET `/api/v1/chat/conversations`
**Description:** Liste des conversations
**Réponse:**
```typescript
interface ConversationsResponse {
  conversations: {
    id: string;
    title: string; // généré automatiquement ou défini par l'utilisateur
    created_at: string;
    updated_at: string;
    message_count: number;
    last_message_preview: string;
  }[];
}
```

#### GET `/api/v1/chat/conversations/{conversation_id}`
**Description:** Historique d'une conversation
**Réponse:**
```typescript
interface ConversationHistory {
  id: string;
  title: string;
  messages: {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: string;
    sources?: {
      document_id: string;
      document_filename: string;
      chunk_content: string;
    }[];
  }[];
}
```

#### DELETE `/api/v1/chat/conversations/{conversation_id}`
**Description:** Suppression d'une conversation

**Composants UI suggérés:**
- Interface de chat avec bulles de messages
- Sidebar avec liste des conversations
- Affichage des sources utilisées
- Indicateur de frappe
- Export de conversations

---

### 6. ⚙️ Configuration

#### GET `/api/v1/config/models/embeddings`
**Description:** Configuration des modèles d'embedding
**Réponse:**
```typescript
interface EmbeddingConfig {
  current_model: string;
  available_models: {
    name: string;
    description: string;
    dimensions: number;
    max_sequence_length: number;
    languages: string[];
  }[];
  model_settings: {
    batch_size: number;
    normalize_embeddings: boolean;
  };
}
```

#### PUT `/api/v1/config/models/embeddings`
**Description:** Mise à jour de la configuration des embeddings
**Body:**
```typescript
interface UpdateEmbeddingConfig {
  model_name: string;
  batch_size?: number;
  normalize_embeddings?: boolean;
}
```

#### GET `/api/v1/config/models/chat`
**Description:** Configuration des modèles de chat (Ollama)
**Réponse:**
```typescript
interface ChatConfig {
  current_model: string;
  available_models: string[];
  model_settings: {
    temperature: number;
    max_tokens: number;
    top_p: number;
    top_k: number;
  };
  ollama_status: "connected" | "disconnected";
  ollama_url: string;
}
```

---

## 🔌 WebSocket pour temps réel

### WS `/ws/processing`
**Description:** Mises à jour en temps réel du traitement des documents

**Messages reçus:**
```typescript
interface ProcessingUpdate {
  type: "document_processing";
  document_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number; // 0-100
  message: string;
  timestamp: string;
}

interface SystemUpdate {
  type: "system_status";
  service: "database" | "vector_db" | "ollama";
  status: "up" | "down";
  timestamp: string;
}
```

**Composants UI suggérés:**
- Notifications toast en temps réel
- Barre de progression live
- Indicateurs de statut système
- Mise à jour automatique des listes

---

## 🎨 Suggestions d'architecture UI

### Structure Next.js recommandée
```
frontend/
├── app/
│   ├── (dashboard)/
│   │   ├── documents/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── search/
│   │   │   └── page.tsx
│   │   ├── chat/
│   │   │   ├── page.tsx
│   │   │   └── [conversationId]/page.tsx
│   │   └── settings/
│   │       └── page.tsx
│   ├── api/ (pour les routes API Next.js si nécessaire)
│   ├── globals.css
│   └── layout.tsx
├── components/
│   ├── ui/ (ShadCN components)
│   ├── documents/
│   │   ├── DocumentUpload.tsx
│   │   ├── DocumentList.tsx
│   │   └── DocumentCard.tsx
│   ├── search/
│   │   ├── SearchBar.tsx
│   │   └── SearchResults.tsx
│   ├── chat/
│   │   ├── ChatInterface.tsx
│   │   ├── MessageBubble.tsx
│   │   └── ConversationSidebar.tsx
│   └── layout/
│       ├── Navbar.tsx
│       ├── Sidebar.tsx
│       └── StatusIndicator.tsx
├── lib/
│   ├── api.ts (client API)
│   ├── websocket.ts
│   ├── utils.ts
│   └── types.ts
└── hooks/
    ├── useDocuments.ts
    ├── useSearch.ts
    ├── useChat.ts
    └── useWebSocket.ts
```

### Client API TypeScript
```typescript
// lib/api.ts
class StudyRAGAPI {
  private baseURL = 'http://localhost:8000';
  
  async uploadDocuments(files: File[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    const response = await fetch(`${this.baseURL}/api/v1/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  }
  
  async getDocuments(params?: DocumentsQuery): Promise<DocumentsListResponse> {
    const url = new URL(`${this.baseURL}/api/v1/database/documents`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) url.searchParams.set(key, String(value));
      });
    }
    
    const response = await fetch(url.toString());
    if (!response.ok) throw new Error('Failed to fetch documents');
    return response.json();
  }
  
  async search(query: SearchRequest): Promise<SearchResponse> {
    const response = await fetch(`${this.baseURL}/api/v1/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(query),
    });
    
    if (!response.ok) throw new Error('Search failed');
    return response.json();
  }
  
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.baseURL}/api/v1/chat/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    
    if (!response.ok) throw new Error('Chat request failed');
    return response.json();
  }
}

export const api = new StudyRAGAPI();
```

### Hook WebSocket
```typescript
// hooks/useWebSocket.ts
export function useWebSocket() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [lastMessage, setLastMessage] = useState<ProcessingUpdate | SystemUpdate | null>(null);
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/processing');
    
    ws.onopen = () => setStatus('connected');
    ws.onclose = () => setStatus('disconnected');
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setLastMessage(message);
    };
    
    return () => ws.close();
  }, []);
  
  return { status, lastMessage };
}
```

## 🚀 Démarrage rapide pour l'agent UI

1. **Créer le projet Next.js:**
```bash
npx create-next-app@latest studyrag-ui --typescript --tailwind --eslint --app
cd studyrag-ui
```

2. **Installer ShadCN/UI:**
```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card input table badge toast
```

3. **Installer les dépendances supplémentaires:**
```bash
npm install react-dropzone @tanstack/react-query lucide-react
```

4. **Configurer le proxy pour l'API** (next.config.js):
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
```

## 🎯 Points clés pour l'intégration

1. **CORS:** Le backend FastAPI est configuré pour accepter les requêtes du frontend
2. **WebSocket:** Utiliser pour les mises à jour temps réel
3. **Upload:** Gérer les gros fichiers avec progress tracking
4. **Erreurs:** Implémenter une gestion d'erreur robuste avec toast notifications
5. **État:** Utiliser React Query pour la gestion du cache et des états de chargement
6. **Types:** Tous les types TypeScript sont fournis pour une intégration parfaite

Cette documentation devrait permettre à votre agent UI de créer une interface moderne et parfaitement intégrée avec votre backend StudyRAG ! 🎨✨