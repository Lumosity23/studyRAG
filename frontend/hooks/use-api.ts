/**
 * Hooks React pour l'API StudyRAG
 * Intégration complète avec le backend FastAPI
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  api,
  HealthResponse,
  Document,
  DocumentsQuery,
  DocumentsListResponse,
  SearchRequest,
  SearchResponse,
  ChatRequest,
  ChatResponse,
  ConversationSummary,
  ConversationHistory,
  ProcessingStatus,
  DatabaseStats,
  WebSocketMessage,
  ProcessingUpdate,
  SystemUpdate
} from '@/lib/api-client';
import toast from 'react-hot-toast';

// Hook pour la santé du système
export function useHealth() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const healthData = await api.getHealth();
      setHealth(healthData);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur de connexion';
      setError(message);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    // Vérifier la santé toutes les 30 secondes
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return { health, loading, error, refetch: checkHealth };
}

// Hook pour l'upload de documents
export function useDocumentUpload() {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<Record<string, number>>({});

  const uploadDocuments = useCallback(async (files: File[]) => {
    try {
      setUploading(true);
      setProgress({});

      // Initialiser le progrès pour chaque fichier
      const initialProgress: Record<string, number> = {};
      files.forEach(file => {
        initialProgress[file.name] = 0;
      });
      setProgress(initialProgress);

      const result = await api.uploadDocuments(files);

      // Mettre à jour le progrès à 100% pour les fichiers réussis
      const finalProgress: Record<string, number> = {};
      result.uploaded_files.forEach(file => {
        finalProgress[file.filename] = 100;
      });
      setProgress(finalProgress);

      // Afficher les notifications
      if (result.total_uploaded > 0) {
        toast.success(`${result.total_uploaded} document(s) uploadé(s) avec succès`);
      }
      
      if (result.failed_uploads.length > 0) {
        result.failed_uploads.forEach(failure => {
          toast.error(`Échec upload ${failure.filename}: ${failure.error}`);
        });
      }

      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erreur upload';
      toast.error(message);
      throw error;
    } finally {
      setUploading(false);
    }
  }, []);

  return { uploadDocuments, uploading, progress };
}

// Hook pour le suivi du statut de traitement
export function useProcessingStatus(taskId: string | null) {
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!taskId) return;

    const checkStatus = async () => {
      try {
        setLoading(true);
        const statusData = await api.getDocumentStatus(taskId);
        setStatus(statusData);
        
        // Arrêter le polling si terminé
        if (statusData.status === 'completed' || statusData.status === 'failed') {
          return;
        }
      } catch (error) {
        console.error('Erreur statut:', error);
      } finally {
        setLoading(false);
      }
    };

    checkStatus();
    
    // Polling toutes les 2 secondes si en cours
    const interval = setInterval(checkStatus, 2000);
    return () => clearInterval(interval);
  }, [taskId]);

  return { status, loading };
}

// Hook pour la liste des documents
export function useDocuments(query?: DocumentsQuery) {
  const [documents, setDocuments] = useState<DocumentsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async (newQuery?: DocumentsQuery) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDocuments(newQuery || query);
      setDocuments(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur chargement documents';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const deleteDocument = useCallback(async (documentId: string) => {
    try {
      await api.deleteDocument(documentId);
      toast.success('Document supprimé');
      // Recharger la liste
      fetchDocuments();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erreur suppression';
      toast.error(message);
    }
  }, [fetchDocuments]);

  return { 
    documents, 
    loading, 
    error, 
    refetch: fetchDocuments,
    deleteDocument
  };
}

// Hook pour la recherche
export function useSearch() {
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (request: SearchRequest) => {
    try {
      setLoading(true);
      setError(null);
      const searchResults = await api.search(request);
      setResults(searchResults);
      return searchResults;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur recherche';
      setError(message);
      toast.error(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setResults(null);
    setError(null);
  }, []);

  return { search, results, loading, error, clearResults };
}

// Hook pour le chat
export function useChat() {
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (request: ChatRequest) => {
    try {
      setSending(true);
      setError(null);
      const response = await api.sendMessage(request);
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur envoi message';
      setError(message);
      toast.error(message);
      throw err;
    } finally {
      setSending(false);
    }
  }, []);

  return { sendMessage, sending, error };
}

// Hook pour les conversations
export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConversations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getConversations();
      setConversations(data.conversations);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur chargement conversations';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const deleteConversation = useCallback(async (conversationId: string) => {
    try {
      await api.deleteConversation(conversationId);
      toast.success('Conversation supprimée');
      fetchConversations();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erreur suppression';
      toast.error(message);
    }
  }, [fetchConversations]);

  return { 
    conversations, 
    loading, 
    error, 
    refetch: fetchConversations,
    deleteConversation
  };
}

// Hook pour l'historique d'une conversation
export function useConversationHistory(conversationId: string | null) {
  const [history, setHistory] = useState<ConversationHistory | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!conversationId) {
      setHistory(null);
      return;
    }

    const fetchHistory = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getConversationHistory(conversationId);
        setHistory(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Erreur chargement historique';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [conversationId]);

  return { history, loading, error };
}

// Hook pour les statistiques
export function useDatabaseStats() {
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDatabaseStats();
      setStats(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur chargement statistiques';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, loading, error, refetch: fetchStats };
}

// Hook pour WebSocket
export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      try {
        const ws = api.createWebSocket();
        wsRef.current = ws;

        ws.onopen = () => {
          setConnected(true);
          console.log('WebSocket connecté');
        };

        ws.onclose = () => {
          setConnected(false);
          console.log('WebSocket déconnecté');
          // Reconnexion automatique après 5 secondes
          setTimeout(connect, 5000);
        };

        ws.onerror = (error) => {
          console.error('Erreur WebSocket:', error);
          setConnected(false);
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            setLastMessage(message);

            // Afficher des notifications pour certains événements
            if (message.type === 'document_processing') {
              const update = message as ProcessingUpdate;
              if (update.status === 'completed') {
                toast.success(`Document traité: ${update.message}`);
              } else if (update.status === 'failed') {
                toast.error(`Erreur traitement: ${update.message}`);
              }
            }
          } catch (error) {
            console.error('Erreur parsing message WebSocket:', error);
          }
        };
      } catch (error) {
        console.error('Erreur connexion WebSocket:', error);
        setConnected(false);
      }
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { connected, lastMessage };
}