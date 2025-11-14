// StudyRAG TypeScript Types pour l'agent UI
// À copier dans src/lib/types.ts du projet Next.js

// ============================================================================
// API Response Types
// ============================================================================

export interface APIError {
  detail: string;
  error_code?: string;
  timestamp?: string;
}

// ============================================================================
// Health & System Types
// ============================================================================

export interface HealthResponse {
  status: "healthy" | "unhealthy";
  timestamp: string;
  version: string;
  services: {
    database: "up" | "down";
    vector_db: "up" | "down";
    ollama: "up" | "down";
  };
}

// ============================================================================
// Document Types
// ============================================================================

export type FileType = "pdf" | "docx" | "html" | "txt" | "md";
export type ProcessingStatus = "pending" | "processing" | "completed" | "failed";

export interface Document {
  id: string;
  filename: string;
  file_type: FileType;
  file_size: number;
  upload_date: string; // ISO 8601
  processing_status: ProcessingStatus;
  chunk_count: number;
  embedding_model: string;
  metadata: Record<string, any>;
  error_message?: string;
}

export interface UploadResponse {
  uploaded_files: {
    filename: string;
    document_id: string;
    file_size: number;
    file_type: string;
    status: "uploaded" | "processing" | "failed";
    task_id?: string;
  }[];
  total_uploaded: number;
  failed_uploads: {
    filename: string;
    error: string;
  }[];
}

export interface ProcessingStatus {
  task_id: string;
  document_id: string;
  status: ProcessingStatus;
  progress: number; // 0-100
  message: string;
  started_at: string;
  completed_at?: string;
  error_details?: string;
}

export interface DocumentsQuery {
  page?: number;
  limit?: number;
  status?: ProcessingStatus;
  file_type?: FileType;
  sort_by?: "upload_date" | "filename" | "file_size";
  sort_order?: "asc" | "desc";
  search?: string;
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface DocumentsListResponse {
  documents: Document[];
  pagination: Pagination;
}

export interface DeleteResponse {
  message: string;
  document_id: string;
  deleted_chunks: number;
}

export interface ReindexResponse {
  message: string;
  document_id: string;
  task_id: string;
  new_embedding_model: string;
}

export interface DatabaseStats {
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

// ============================================================================
// Search Types
// ============================================================================

export interface SearchRequest {
  query: string;
  limit?: number;
  min_score?: number;
  document_ids?: string[];
  file_types?: FileType[];
}

export interface SearchResult {
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
  highlighted_content?: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
}

// ============================================================================
// Chat Types
// ============================================================================

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  context_documents?: string[];
  model_settings?: {
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
  };
}

export interface ChatResponse {
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

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_preview: string;
}

export interface ConversationsResponse {
  conversations: ConversationSummary[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: {
    document_id: string;
    document_filename: string;
    chunk_content: string;
  }[];
}

export interface ConversationHistory {
  id: string;
  title: string;
  messages: ChatMessage[];
}

// ============================================================================
// Configuration Types
// ============================================================================

export interface EmbeddingModel {
  name: string;
  description: string;
  dimensions: number;
  max_sequence_length: number;
  languages: string[];
}

export interface EmbeddingConfig {
  current_model: string;
  available_models: EmbeddingModel[];
  model_settings: {
    batch_size: number;
    normalize_embeddings: boolean;
  };
}

export interface UpdateEmbeddingConfig {
  model_name: string;
  batch_size?: number;
  normalize_embeddings?: boolean;
}

export interface ChatConfig {
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

// ============================================================================
// WebSocket Types
// ============================================================================

export interface ProcessingUpdate {
  type: "document_processing";
  document_id: string;
  status: ProcessingStatus;
  progress: number;
  message: string;
  timestamp: string;
}

export interface SystemUpdate {
  type: "system_status";
  service: "database" | "vector_db" | "ollama";
  status: "up" | "down";
  timestamp: string;
}

export type WebSocketMessage = ProcessingUpdate | SystemUpdate;

// ============================================================================
// UI State Types
// ============================================================================

export interface UploadState {
  files: File[];
  uploading: boolean;
  progress: number;
  error?: string;
}

export interface SearchState {
  query: string;
  results: SearchResult[];
  loading: boolean;
  error?: string;
  filters: {
    file_types: FileType[];
    min_score: number;
  };
}

export interface ChatState {
  messages: ChatMessage[];
  loading: boolean;
  error?: string;
  conversationId?: string;
}

// ============================================================================
// Form Types
// ============================================================================

export interface SearchFormData {
  query: string;
  file_types: FileType[];
  min_score: number;
}

export interface ChatFormData {
  message: string;
}

export interface SettingsFormData {
  embedding_model: string;
  chat_model: string;
  temperature: number;
  max_tokens: number;
}

// ============================================================================
// Component Props Types
// ============================================================================

export interface DocumentCardProps {
  document: Document;
  onDelete: (id: string) => void;
  onReindex: (id: string) => void;
  onView: (id: string) => void;
}

export interface SearchResultCardProps {
  result: SearchResult;
  query: string;
}

export interface MessageBubbleProps {
  message: ChatMessage;
  isUser: boolean;
}

export interface ProgressBarProps {
  value: number;
  max?: number;
  label?: string;
  animated?: boolean;
}

// ============================================================================
// API Client Types
// ============================================================================

export interface APIClientConfig {
  baseURL: string;
  timeout?: number;
  retries?: number;
}

export interface RequestOptions extends RequestInit {
  timeout?: number;
  retries?: number;
}

// ============================================================================
// Utility Types
// ============================================================================

export type SortOrder = "asc" | "desc";
export type LoadingState = "idle" | "loading" | "success" | "error";

export interface PaginationState {
  page: number;
  limit: number;
  total: number;
}

export interface FilterState {
  search: string;
  status: ProcessingStatus[];
  file_types: FileType[];
  sort_by: string;
  sort_order: SortOrder;
}

// ============================================================================
// Error Types
// ============================================================================

export class APIClientError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string
  ) {
    super(message);
    this.name = "APIClientError";
  }
}

export class ValidationError extends Error {
  constructor(
    message: string,
    public field?: string
  ) {
    super(message);
    this.name = "ValidationError";
  }
}

// ============================================================================
// Constants
// ============================================================================

export const FILE_TYPES: Record<FileType, string> = {
  pdf: "PDF Document",
  docx: "Word Document", 
  html: "HTML File",
  txt: "Text File",
  md: "Markdown File"
};

export const STATUS_COLORS: Record<ProcessingStatus, string> = {
  pending: "yellow",
  processing: "blue", 
  completed: "green",
  failed: "red"
};

export const STATUS_LABELS: Record<ProcessingStatus, string> = {
  pending: "⏳ Pending",
  processing: "⚙️ Processing",
  completed: "✅ Ready", 
  failed: "❌ Failed"
};

export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
export const SUPPORTED_FILE_TYPES = ["pdf", "docx", "html", "txt", "md"];
export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

// ============================================================================
// Type Guards
// ============================================================================

export function isDocument(obj: any): obj is Document {
  return obj && typeof obj.id === "string" && typeof obj.filename === "string";
}

export function isSearchResult(obj: any): obj is SearchResult {
  return obj && typeof obj.document_id === "string" && typeof obj.content === "string";
}

export function isChatMessage(obj: any): obj is ChatMessage {
  return obj && typeof obj.id === "string" && ["user", "assistant"].includes(obj.role);
}

export function isProcessingUpdate(obj: any): obj is ProcessingUpdate {
  return obj && obj.type === "document_processing" && typeof obj.document_id === "string";
}

export function isSystemUpdate(obj: any): obj is SystemUpdate {
  return obj && obj.type === "system_status" && typeof obj.service === "string";
}

// ============================================================================
// Validation Schemas (pour react-hook-form avec zod)
// ============================================================================

import { z } from "zod";

export const searchSchema = z.object({
  query: z.string().min(1, "Query is required").max(500, "Query too long"),
  file_types: z.array(z.enum(["pdf", "docx", "html", "txt", "md"])).optional(),
  min_score: z.number().min(0).max(1).optional(),
});

export const chatSchema = z.object({
  message: z.string().min(1, "Message is required").max(2000, "Message too long"),
});

export const settingsSchema = z.object({
  embedding_model: z.string().min(1, "Embedding model is required"),
  chat_model: z.string().min(1, "Chat model is required"),
  temperature: z.number().min(0).max(1),
  max_tokens: z.number().min(1).max(4000),
});

// ============================================================================
// React Query Keys
// ============================================================================

export const queryKeys = {
  health: ["health"] as const,
  documents: {
    all: ["documents"] as const,
    lists: () => [...queryKeys.documents.all, "list"] as const,
    list: (params: DocumentsQuery) => [...queryKeys.documents.lists(), params] as const,
    details: () => [...queryKeys.documents.all, "detail"] as const,
    detail: (id: string) => [...queryKeys.documents.details(), id] as const,
    stats: ["documents", "stats"] as const,
  },
  search: {
    all: ["search"] as const,
    results: (query: string) => [...queryKeys.search.all, query] as const,
  },
  chat: {
    all: ["chat"] as const,
    conversations: ["chat", "conversations"] as const,
    conversation: (id: string) => ["chat", "conversation", id] as const,
  },
  config: {
    all: ["config"] as const,
    embeddings: ["config", "embeddings"] as const,
    chat: ["config", "chat"] as const,
  },
} as const;