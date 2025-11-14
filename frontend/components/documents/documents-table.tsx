'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { DocumentsListResponse, Document } from '@/lib/api-client'
import {
  FileText,
  Download,
  Trash2,
  RefreshCw,
  Eye,
  Calendar,
  HardDrive,
  AlertCircle,
  CheckCircle,
  Clock,
  Loader2,
  ChevronLeft,
  ChevronRight,
  MoreHorizontal
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'

interface DocumentsTableProps {
  documents: DocumentsResponse | null
  loading: boolean
  onDelete: (documentId: string) => Promise<void>
  onReindex: (documentId: string) => Promise<void>
  onPageChange: (page: number) => void
  currentPage: number
}

export function DocumentsTable({
  documents,
  loading,
  onDelete,
  onReindex,
  onPageChange,
  currentPage
}: DocumentsTableProps) {
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())
  const [reindexingIds, setReindexingIds] = useState<Set<string>>(new Set())

  const handleDelete = async (documentId: string) => {
    if (confirm('Êtes-vous sûr de vouloir supprimer ce document ?')) {
      setDeletingIds(prev => new Set(prev).add(documentId))
      try {
        await onDelete(documentId)
      } finally {
        setDeletingIds(prev => {
          const newSet = new Set(prev)
          newSet.delete(documentId)
          return newSet
        })
      }
    }
  }

  const handleReindex = async (documentId: string) => {
    setReindexingIds(prev => new Set(prev).add(documentId))
    try {
      await onReindex(documentId)
    } finally {
      setReindexingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(documentId)
        return newSet
      })
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <Badge variant="default" className="bg-green-500/10 text-green-500 border-green-500/20">
            <CheckCircle className="w-3 h-3 mr-1" />
            Terminé
          </Badge>
        )
      case 'processing':
        return (
          <Badge variant="default" className="bg-blue-500/10 text-blue-500 border-blue-500/20">
            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            En traitement
          </Badge>
        )
      case 'pending':
        return (
          <Badge variant="default" className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
            <Clock className="w-3 h-3 mr-1" />
            En attente
          </Badge>
        )
      case 'failed':
        return (
          <Badge variant="destructive" className="bg-red-500/10 text-red-500 border-red-500/20">
            <AlertCircle className="w-3 h-3 mr-1" />
            Échec
          </Badge>
        )
      default:
        return (
          <Badge variant="secondary">
            {status}
          </Badge>
        )
    }
  }

  const getFileIcon = (fileType: string) => {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return <FileText className="w-4 h-4 text-red-500" />
      case 'docx':
        return <FileText className="w-4 h-4 text-blue-500" />
      case 'pptx':
        return <FileText className="w-4 h-4 text-orange-500" />
      case 'txt':
      case 'md':
        return <FileText className="w-4 h-4 text-gray-500" />
      case 'html':
        return <FileText className="w-4 h-4 text-green-500" />
      default:
        return <FileText className="w-4 h-4" />
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), { 
        addSuffix: true, 
        locale: fr 
      })
    } catch {
      return dateString
    }
  }

  if (loading && !documents) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
          <span className="text-muted-foreground">Chargement des documents...</span>
        </div>
      </div>
    )
  }

  if (!documents || documents.documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <FileText className="w-12 h-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">Aucun document trouvé</h3>
        <p className="text-muted-foreground mb-4">
          Commencez par uploader vos premiers documents pour les voir apparaître ici.
        </p>
        <Button variant="outline">
          <Download className="w-4 h-4 mr-2" />
          Uploader des documents
        </Button>
      </div>
    )
  }

  const { documents: docs, pagination } = documents
  const totalPages = Math.ceil(pagination.total / pagination.limit)

  return (
    <div className="space-y-4">
      {/* Table */}
      <div className="bg-card rounded-lg border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/30">
              <tr>
                <th className="text-left p-4 font-medium">Document</th>
                <th className="text-left p-4 font-medium">Statut</th>
                <th className="text-left p-4 font-medium">Taille</th>
                <th className="text-left p-4 font-medium">Chunks</th>
                <th className="text-left p-4 font-medium">Uploadé</th>
                <th className="text-right p-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence>
                {docs.map((doc, index) => (
                  <motion.tr
                    key={doc.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ delay: index * 0.05 }}
                    className="border-t border-border hover:bg-muted/20 transition-colors"
                  >
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        {getFileIcon(doc.file_type)}
                        <div className="min-w-0 flex-1">
                          <div className="font-medium truncate" title={doc.filename}>
                            {doc.filename}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {doc.file_type.toUpperCase()}
                          </div>
                        </div>
                      </div>
                    </td>
                    
                    <td className="p-4">
                      {getStatusBadge(doc.status)}
                    </td>
                    
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <HardDrive className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm">
                          {formatFileSize(doc.file_size)}
                        </span>
                      </div>
                    </td>
                    
                    <td className="p-4">
                      <div className="text-sm">
                        {doc.chunk_count || 0} chunk{(doc.chunk_count || 0) > 1 ? 's' : ''}
                      </div>
                    </td>
                    
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm">
                          {formatDate(doc.upload_date)}
                        </span>
                      </div>
                    </td>
                    
                    <td className="p-4">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleReindex(doc.id)}
                          disabled={reindexingIds.has(doc.id) || doc.status === 'processing'}
                          title="Re-indexer le document"
                        >
                          {reindexingIds.has(doc.id) ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <RefreshCw className="w-4 h-4" />
                          )}
                        </Button>
                        
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(doc.id)}
                          disabled={deletingIds.has(doc.id)}
                          title="Supprimer le document"
                          className="text-red-500 hover:text-red-600 hover:bg-red-500/10"
                        >
                          {deletingIds.has(doc.id) ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Page {currentPage} sur {totalPages} • {pagination.total} document{pagination.total > 1 ? 's' : ''} au total
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage <= 1}
            >
              <ChevronLeft className="w-4 h-4" />
              Précédent
            </Button>
            
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum
                if (totalPages <= 5) {
                  pageNum = i + 1
                } else if (currentPage <= 3) {
                  pageNum = i + 1
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i
                } else {
                  pageNum = currentPage - 2 + i
                }
                
                return (
                  <Button
                    key={pageNum}
                    variant={currentPage === pageNum ? "default" : "outline"}
                    size="sm"
                    onClick={() => onPageChange(pageNum)}
                    className="w-8 h-8 p-0"
                  >
                    {pageNum}
                  </Button>
                )
              })}
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
            >
              Suivant
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}