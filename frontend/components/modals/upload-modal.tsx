'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { useAppStore } from '@/lib/store'
import { useDocumentUpload } from '@/hooks/use-api'
import { formatFileSize } from '@/lib/utils'
import { cn } from '@/lib/utils'
import {
  Upload,
  X,
  FileText,
  CheckCircle,
  AlertCircle,
  Loader2
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'

export function UploadModal() {
  const { uploadModalOpen, setUploadModalOpen } = useAppStore()
  const { uploadDocuments, uploading, uploadProgress, clearProgress } = useDocumentUpload()
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Filtrer les fichiers supportés
    const supportedTypes = ['.pdf', '.docx', '.html', '.txt', '.md']
    const validFiles = acceptedFiles.filter(file => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase()
      return supportedTypes.includes(extension)
    })

    if (validFiles.length !== acceptedFiles.length) {
      toast.error('Certains fichiers ne sont pas supportés')
    }

    setSelectedFiles(prev => [...prev, ...validFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/html': ['.html'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md']
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  })

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return

    try {
      await uploadDocuments(selectedFiles)
      setSelectedFiles([])
    } catch (error) {
      console.error('Upload failed:', error)
    }
  }

  const handleClose = () => {
    if (!uploading) {
      setUploadModalOpen(false)
      setSelectedFiles([])
      // Nettoyer les progress terminés
      uploadProgress.forEach((status, taskId) => {
        if (status.status === 'completed' || status.status === 'failed') {
          clearProgress(taskId)
        }
      })
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      case 'processing':
      case 'pending':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
      default:
        return <FileText className="w-4 h-4 text-muted-foreground" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-500'
      case 'failed':
        return 'text-red-500'
      case 'processing':
      case 'pending':
        return 'text-blue-500'
      default:
        return 'text-muted-foreground'
    }
  }

  return (
    <Dialog open={uploadModalOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Uploader des documents
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-6">
          {/* Zone de drop */}
          <div
            {...getRootProps()}
            className={cn(
              "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200",
              isDragActive 
                ? "border-primary bg-primary/5" 
                : "border-border hover:border-primary/50 hover:bg-muted/50"
            )}
          >
            <input {...getInputProps()} />
            <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg font-medium mb-2">
              {isDragActive ? "Déposez vos fichiers ici" : "Glissez-déposez vos fichiers"}
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              ou cliquez pour sélectionner
            </p>
            <p className="text-xs text-muted-foreground">
              Formats supportés: PDF, DOCX, HTML, TXT, MD (max 50MB par fichier)
            </p>
          </div>

          {/* Fichiers sélectionnés */}
          {selectedFiles.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-medium">Fichiers sélectionnés ({selectedFiles.length})</h3>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                <AnimatePresence>
                  {selectedFiles.map((file, index) => (
                    <motion.div
                      key={`${file.name}-${index}`}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="flex items-center justify-between p-3 bg-muted rounded-lg"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{file.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatFileSize(file.size)}
                          </p>
                        </div>
                      </div>
                      {!uploading && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFile(index)}
                          className="flex-shrink-0"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          )}

          {/* Progress des uploads */}
          {Object.keys(progress).length > 0 && (
            <div className="space-y-3">
              <h3 className="font-medium">Traitement en cours</h3>
              <div className="space-y-3 max-h-60 overflow-y-auto">
                {Object.entries(progress).map(([filename, progressValue]) => (
                  <motion.div
                    key={taskId}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 bg-muted rounded-lg space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(status.status)}
                        <span className="text-sm font-medium">
                          Document {status.document_id.slice(-8)}
                        </span>
                      </div>
                      <span className={cn("text-xs", getStatusColor(status.status))}>
                        {status.status === 'completed' && '100%'}
                        {status.status === 'processing' && `${Math.round(status.progress)}%`}
                        {status.status === 'pending' && 'En attente'}
                        {status.status === 'failed' && 'Échec'}
                      </span>
                    </div>
                    
                    {status.status === 'processing' && (
                      <Progress value={status.progress} className="h-2" />
                    )}
                    
                    <p className="text-xs text-muted-foreground">
                      {status.message}
                    </p>
                    
                    {status.error_details && (
                      <p className="text-xs text-red-500">
                        {status.error_details}
                      </p>
                    )}
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t">
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={uploading}
          >
            {uploading ? 'Upload en cours...' : 'Fermer'}
          </Button>
          
          <Button
            onClick={handleUpload}
            disabled={selectedFiles.length === 0 || uploading}
            className="bg-gradient-to-r from-pastel-purple to-pastel-blue hover:from-pastel-pink hover:to-pastel-green"
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Upload en cours...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                Uploader {selectedFiles.length} fichier{selectedFiles.length > 1 ? 's' : ''}
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}