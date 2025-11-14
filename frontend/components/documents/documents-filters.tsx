'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { DocumentsQuery } from '@/lib/api-client'
import {
  Search,
  Filter,
  X,
  SortAsc,
  SortDesc,
  FileText,
  Clock,
  HardDrive
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface DocumentsFiltersProps {
  query: DocumentsQuery
  onQueryChange: (query: Partial<DocumentsQuery>) => void
  totalDocuments: number
}

export function DocumentsFilters({ query, onQueryChange, totalDocuments }: DocumentsFiltersProps) {
  const [searchValue, setSearchValue] = useState(query.search || '')
  const [showFilters, setShowFilters] = useState(false)

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onQueryChange({ search: searchValue || undefined })
  }

  const handleSearchClear = () => {
    setSearchValue('')
    onQueryChange({ search: undefined })
  }

  const handleStatusChange = (status: string) => {
    onQueryChange({ 
      status: status === 'all' ? undefined : status as any
    })
  }

  const handleFileTypeChange = (fileType: string) => {
    onQueryChange({ 
      file_type: fileType === 'all' ? undefined : fileType as any
    })
  }

  const handleSortChange = (sortBy: string) => {
    onQueryChange({ sort_by: sortBy as any })
  }

  const handleSortOrderToggle = () => {
    onQueryChange({ 
      sort_order: query.sort_order === 'asc' ? 'desc' : 'asc'
    })
  }

  const getActiveFiltersCount = () => {
    let count = 0
    if (query.search) count++
    if (query.status) count++
    if (query.file_type) count++
    return count
  }

  const clearAllFilters = () => {
    setSearchValue('')
    onQueryChange({
      search: undefined,
      status: undefined,
      file_type: undefined,
      sort_by: 'upload_date',
      sort_order: 'desc'
    })
  }

  return (
    <div className="space-y-4">
      {/* Search and main controls */}
      <div className="flex items-center gap-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher par nom de fichier..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              className="pl-10 pr-10"
            />
            {searchValue && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleSearchClear}
                className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
              >
                <X className="w-3 h-3" />
              </Button>
            )}
          </div>
        </form>

        <Button
          variant="outline"
          onClick={() => setShowFilters(!showFilters)}
          className={`relative ${getActiveFiltersCount() > 0 ? 'border-primary' : ''}`}
        >
          <Filter className="w-4 h-4 mr-2" />
          Filtres
          {getActiveFiltersCount() > 0 && (
            <Badge 
              variant="secondary" 
              className="ml-2 h-5 w-5 p-0 flex items-center justify-center text-xs bg-primary text-primary-foreground"
            >
              {getActiveFiltersCount()}
            </Badge>
          )}
        </Button>

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {totalDocuments} document{totalDocuments > 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Advanced filters */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="bg-muted/30 rounded-lg p-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Status Filter */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Statut</label>
                  <Select
                    value={query.status || 'all'}
                    onValueChange={handleStatusChange}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tous les statuts</SelectItem>
                      <SelectItem value="pending">En attente</SelectItem>
                      <SelectItem value="processing">En traitement</SelectItem>
                      <SelectItem value="completed">Terminé</SelectItem>
                      <SelectItem value="failed">Échec</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* File Type Filter */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Type de fichier</label>
                  <Select
                    value={query.file_type || 'all'}
                    onValueChange={handleFileTypeChange}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tous les types</SelectItem>
                      <SelectItem value="pdf">PDF</SelectItem>
                      <SelectItem value="docx">Word</SelectItem>
                      <SelectItem value="pptx">PowerPoint</SelectItem>
                      <SelectItem value="txt">Texte</SelectItem>
                      <SelectItem value="md">Markdown</SelectItem>
                      <SelectItem value="html">HTML</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Sort By */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Trier par</label>
                  <Select
                    value={query.sort_by || 'upload_date'}
                    onValueChange={handleSortChange}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="upload_date">Date d'upload</SelectItem>
                      <SelectItem value="filename">Nom de fichier</SelectItem>
                      <SelectItem value="file_size">Taille</SelectItem>
                      <SelectItem value="status">Statut</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Sort Order */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Ordre</label>
                  <Button
                    variant="outline"
                    onClick={handleSortOrderToggle}
                    className="w-full justify-start"
                  >
                    {query.sort_order === 'asc' ? (
                      <>
                        <SortAsc className="w-4 h-4 mr-2" />
                        Croissant
                      </>
                    ) : (
                      <>
                        <SortDesc className="w-4 h-4 mr-2" />
                        Décroissant
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Active filters and clear */}
              {getActiveFiltersCount() > 0 && (
                <div className="flex items-center justify-between pt-4 border-t border-border">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm text-muted-foreground">Filtres actifs:</span>
                    {query.search && (
                      <Badge variant="secondary" className="gap-1">
                        <Search className="w-3 h-3" />
                        {query.search}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSearchValue('')
                            onQueryChange({ search: undefined })
                          }}
                          className="h-4 w-4 p-0 ml-1"
                        >
                          <X className="w-3 h-3" />
                        </Button>
                      </Badge>
                    )}
                    {query.status && (
                      <Badge variant="secondary" className="gap-1">
                        <Clock className="w-3 h-3" />
                        {query.status}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onQueryChange({ status: undefined })}
                          className="h-4 w-4 p-0 ml-1"
                        >
                          <X className="w-3 h-3" />
                        </Button>
                      </Badge>
                    )}
                    {query.file_type && (
                      <Badge variant="secondary" className="gap-1">
                        <FileText className="w-3 h-3" />
                        {query.file_type}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onQueryChange({ file_type: undefined })}
                          className="h-4 w-4 p-0 ml-1"
                        >
                          <X className="w-3 h-3" />
                        </Button>
                      </Badge>
                    )}
                  </div>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearAllFilters}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    Effacer tout
                  </Button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}