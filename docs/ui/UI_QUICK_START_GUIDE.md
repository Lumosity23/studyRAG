# 🚀 Guide de démarrage rapide pour l'agent UI

## 🎯 Objectif
Créer une interface utilisateur moderne et professionnelle pour StudyRAG avec Next.js et ShadCN/UI qui remplace complètement l'interface actuelle.

## 📋 Prérequis
- Backend StudyRAG fonctionnel sur `http://localhost:8000`
- Node.js 18+ installé
- Connaissance de Next.js, TypeScript, et Tailwind CSS

## 🏗️ Étapes de création

### 1. Initialisation du projet
```bash
# Créer le projet Next.js
npx create-next-app@latest studyrag-ui --typescript --tailwind --eslint --app --src-dir

cd studyrag-ui

# Installer ShadCN/UI
npx shadcn-ui@latest init

# Installer les composants ShadCN nécessaires
npx shadcn-ui@latest add button card input label textarea table badge toast dialog dropdown-menu tabs separator progress avatar sheet

# Installer les dépendances supplémentaires
npm install @tanstack/react-query react-dropzone lucide-react @hookform/resolvers zod react-hook-form date-fns clsx tailwind-merge
```

### 2. Configuration de base

#### `next.config.js`
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
      {
        source: '/health',
        destination: 'http://localhost:8000/health',
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,POST,PUT,DELETE,OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

#### `src/lib/api.ts` - Client API
```typescript
export class StudyRAGAPI {
  private baseURL = process.env.NODE_ENV === 'production' 
    ? 'https://your-domain.com' 
    : 'http://localhost:8000';

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Documents
  async uploadDocuments(files: File[]) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return fetch(`${this.baseURL}/api/v1/documents/upload`, {
      method: 'POST',
      body: formData,
    }).then(res => res.json());
  }

  async getDocuments(params?: any) {
    const searchParams = new URLSearchParams(params);
    return this.request(`/api/v1/database/documents?${searchParams}`);
  }

  async deleteDocument(id: string) {
    return this.request(`/api/v1/database/documents/${id}`, {
      method: 'DELETE',
    });
  }

  // Search
  async search(query: string, options?: any) {
    return this.request('/api/v1/search', {
      method: 'POST',
      body: JSON.stringify({ query, ...options }),
    });
  }

  // Chat
  async sendMessage(message: string, conversationId?: string) {
    return this.request('/api/v1/chat/message', {
      method: 'POST',
      body: JSON.stringify({ message, conversation_id: conversationId }),
    });
  }

  async getConversations() {
    return this.request('/api/v1/chat/conversations');
  }
}

export const api = new StudyRAGAPI();
```

### 3. Structure des composants prioritaires

#### `src/components/layout/Navbar.tsx`
```typescript
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, Search, MessageCircle, Settings, Activity } from "lucide-react";
import Link from "next/link";

export function Navbar() {
  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center">
        <div className="mr-8 flex items-center space-x-2">
          <Activity className="h-6 w-6" />
          <span className="font-bold">StudyRAG</span>
        </div>
        
        <div className="flex items-center space-x-6">
          <Link href="/documents" className="flex items-center space-x-2 text-sm font-medium">
            <FileText className="h-4 w-4" />
            <span>Documents</span>
          </Link>
          <Link href="/search" className="flex items-center space-x-2 text-sm font-medium">
            <Search className="h-4 w-4" />
            <span>Search</span>
          </Link>
          <Link href="/chat" className="flex items-center space-x-2 text-sm font-medium">
            <MessageCircle className="h-4 w-4" />
            <span>Chat</span>
          </Link>
          <Link href="/settings" className="flex items-center space-x-2 text-sm font-medium">
            <Settings className="h-4 w-4" />
            <span>Settings</span>
          </Link>
        </div>

        <div className="ml-auto">
          <Badge variant="outline" className="text-green-600">
            System Online
          </Badge>
        </div>
      </div>
    </nav>
  );
}
```

#### `src/components/documents/DocumentUpload.tsx`
```typescript
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Upload, File, X } from "lucide-react";
import { api } from '@/lib/api';

export function DocumentUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/html': ['.html'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadFiles = async () => {
    if (files.length === 0) return;
    
    setUploading(true);
    try {
      await api.uploadDocuments(files);
      setFiles([]);
      // Show success toast
    } catch (error) {
      // Show error toast
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-6">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium mb-2">
              {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              or click to browse files
            </p>
            <p className="text-xs text-muted-foreground">
              Supports PDF, DOCX, HTML, TXT, MD (max 50MB each)
            </p>
          </div>
        </CardContent>
      </Card>

      {files.length > 0 && (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-2 mb-4">
              {files.map((file, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-muted rounded">
                  <div className="flex items-center space-x-2">
                    <File className="h-4 w-4" />
                    <span className="text-sm">{file.name}</span>
                    <span className="text-xs text-muted-foreground">
                      ({(file.size / 1024 / 1024).toFixed(1)} MB)
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(index)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
            
            {uploading && (
              <div className="mb-4">
                <Progress value={progress} className="w-full" />
                <p className="text-sm text-muted-foreground mt-1">
                  Uploading files... {progress}%
                </p>
              </div>
            )}
            
            <Button onClick={uploadFiles} disabled={uploading} className="w-full">
              {uploading ? 'Uploading...' : `Upload ${files.length} file(s)`}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

### 4. Pages principales

#### `src/app/documents/page.tsx`
```typescript
import { DocumentUpload } from '@/components/documents/DocumentUpload';
import { DocumentList } from '@/components/documents/DocumentList';

export default function DocumentsPage() {
  return (
    <div className="container mx-auto py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Documents</h1>
        <p className="text-muted-foreground">
          Upload and manage your documents for AI-powered analysis
        </p>
      </div>
      
      <DocumentUpload />
      <DocumentList />
    </div>
  );
}
```

#### `src/app/search/page.tsx`
```typescript
import { SearchInterface } from '@/components/search/SearchInterface';

export default function SearchPage() {
  return (
    <div className="container mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Search</h1>
        <p className="text-muted-foreground">
          Find information across all your documents using semantic search
        </p>
      </div>
      
      <SearchInterface />
    </div>
  );
}
```

### 5. Hooks personnalisés

#### `src/hooks/useDocuments.ts`
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useDocuments(params?: any) {
  return useQuery({
    queryKey: ['documents', params],
    queryFn: () => api.getDocuments(params),
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}
```

#### `src/hooks/useWebSocket.ts`
```typescript
import { useEffect, useState } from 'react';

export function useWebSocket(url: string) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [connectionStatus, setConnectionStatus] = useState<'Connecting' | 'Open' | 'Closing' | 'Closed'>('Closed');

  useEffect(() => {
    const ws = new WebSocket(url);
    setSocket(ws);

    ws.onopen = () => setConnectionStatus('Open');
    ws.onclose = () => setConnectionStatus('Closed');
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setLastMessage(message);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  return { socket, lastMessage, connectionStatus };
}
```

## 🎨 Design Guidelines

### Couleurs et thème
- Utiliser les couleurs ShadCN par défaut
- Implémenter le mode sombre
- Badges colorés pour les statuts :
  - 🟢 Vert : Completed, Online, Success
  - 🟡 Jaune : Processing, Pending, Warning  
  - 🔴 Rouge : Failed, Error, Offline
  - 🔵 Bleu : Info, Primary actions

### Typographie
- Titres : `text-3xl font-bold` pour h1, `text-xl font-semibold` pour h2
- Corps : `text-base` par défaut
- Texte secondaire : `text-muted-foreground`

### Espacement
- Conteneurs : `container mx-auto py-8`
- Sections : `space-y-8` ou `space-y-6`
- Composants : `space-y-4`

## 🚀 Fonctionnalités à implémenter en priorité

1. **Upload de documents** avec drag & drop et progress
2. **Liste des documents** avec tri, filtres, et actions
3. **Recherche sémantique** avec résultats en temps réel
4. **Interface de chat** avec historique des conversations
5. **Mises à jour temps réel** via WebSocket
6. **Configuration des modèles** dans les settings

## 🔧 Intégration WebSocket

```typescript
// Dans un composant ou hook
const { lastMessage } = useWebSocket('ws://localhost:8000/ws/processing');

useEffect(() => {
  if (lastMessage?.type === 'document_processing') {
    // Mettre à jour l'UI avec le nouveau statut
    queryClient.invalidateQueries(['documents']);
  }
}, [lastMessage]);
```

## 📱 Responsive Design

- Mobile-first avec Tailwind CSS
- Breakpoints : `sm:`, `md:`, `lg:`, `xl:`
- Navigation mobile avec Sheet/Drawer
- Tables responsive avec scroll horizontal

## ✅ Checklist de validation

- [ ] Upload de fichiers fonctionne
- [ ] Liste des documents se charge
- [ ] Recherche retourne des résultats
- [ ] Chat envoie et reçoit des messages
- [ ] WebSocket se connecte et reçoit des mises à jour
- [ ] Interface responsive sur mobile
- [ ] Mode sombre fonctionne
- [ ] Gestion d'erreurs appropriée
- [ ] Loading states partout
- [ ] Accessibilité (ARIA labels, navigation clavier)

Cette structure vous donnera une base solide pour créer une interface moderne et professionnelle qui s'intègre parfaitement avec votre backend StudyRAG ! 🎨✨