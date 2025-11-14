'use client'

import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { useAppStore } from '@/lib/store'
import { useDocumentUpload } from '@/hooks/use-api'
import { Upload, X, FileText, CheckCircle, AlertCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export function UploadModal() {
  const { uploadModalOpen, setUploadModalOpen } = useAppStore()
  const { uploadDocuments, uploading, progress } = useDocumentUpload()
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/html': ['.html']
    },
    multiple: true,
    onDrop: (acceptedFiles) => {
      setSelectedFiles(prev => [...prev, ...acceptedFiles])
    }
  })

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return

    try {
      await uploadDocuments(selectedFiles)
      setSelectedFiles([])
      // Fermer le modal après un délai
      setTimeout(() => {
        setUploadModalOpen(false)
      }, 2000)
    } catch (error) {
      console.error('Upload error:', error)
    }
  }

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <Dialog open={uploadModalOpen} onOpenChange={setUploadModalOpen}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Upload de Documents
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Zone de drop */}
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
              ${isDragActive 
                ? 'border-primary bg-primary/5' 
                : 'border-muted-foreground/25 hover:border-primary/50'
              }
            `}
          >
            <input {...getInputProps()} />
            <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg font-medium mb-2">
              {isDragActive ? 'Déposez vos fichiers ici' : 'Glissez-déposez vos documents'}
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              ou cliquez pour sélectionner des fichiers
            </p>
            <p className="text-xs text-muted-foreground">
              Formats supportés: PDF, DOCX, TXT, MD, HTML
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
                      className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">{file.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatFileSize(file.size)}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                        disabled={uploading}
                      >
                        <X className="h-4 w-4" />
                      </Button>
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
              <div className="space-y-3">
                {Object.entries(progress).map(([filename, progressValue]) => (
                  <div key={filename} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{filename}</span>
                      <span className="text-xs text-muted-foreground">
                        {progressValue}%
                      </span>
                    </div>
                    <Progress value={progressValue} className="h-2" />
                    <div className="flex items-center gap-2 text-xs">
                      {progressValue === 100 ? (
                        <>
                          <CheckCircle className="h-3 w-3 text-green-500" />
                          <span className="text-green-600">Terminé</span>
                        </>
                      ) : (
                        <>
                          <div className="h-3 w-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                          <span className="text-blue-600">En cours...</span>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => setUploadModalOpen(false)}
              disabled={uploading}
            >
              Annuler
            </Button>
            <Button
              onClick={handleUpload}
              disabled={selectedFiles.length === 0 || uploading}
            >
              {uploading ? (
                <>
                  <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Upload en cours...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload {selectedFiles.length} fichier{selectedFiles.length > 1 ? 's' : ''}
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}