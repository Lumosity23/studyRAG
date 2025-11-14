'use client'

import { DatabaseStats } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  FileText,
  Database,
  Layers,
  HardDrive,
  Clock,
  TrendingUp,
  PieChart,
  BarChart3,
  Activity,
  Zap
} from 'lucide-react'
import { motion } from 'framer-motion'

interface DocumentsStatsProps {
  stats: DatabaseStats | null
  loading: boolean
}

export function DocumentsStats({ stats, loading }: DocumentsStatsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-4 bg-muted rounded w-3/4"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-muted rounded w-1/2 mb-2"></div>
              <div className="h-3 bg-muted rounded w-full"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Database className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Statistiques indisponibles</h3>
          <p className="text-muted-foreground">
            Impossible de charger les statistiques de la base de données.
          </p>
        </div>
      </div>
    )
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('fr-FR').format(num)
  }

  const getStorageUsagePercentage = () => {
    // Estimation basée sur la taille moyenne des documents
    const avgDocSize = stats.total_size / Math.max(stats.total_documents, 1)
    const estimatedMaxStorage = 10 * 1024 * 1024 * 1024 // 10GB
    return Math.min((stats.total_size / estimatedMaxStorage) * 100, 100)
  }

  const getProcessingSuccessRate = () => {
    const total = stats.documents_by_status.completed + 
                  stats.documents_by_status.failed + 
                  stats.documents_by_status.processing + 
                  stats.documents_by_status.pending
    
    if (total === 0) return 0
    return (stats.documents_by_status.completed / total) * 100
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <motion.div variants={itemVariants}>
          <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/10 border-blue-500/20">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
              <FileText className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {formatNumber(stats.total_documents)}
              </div>
              <p className="text-xs text-muted-foreground">
                documents indexés
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="bg-gradient-to-br from-green-500/10 to-green-600/10 border-green-500/20">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Chunks</CardTitle>
              <Layers className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {formatNumber(stats.total_chunks)}
              </div>
              <p className="text-xs text-muted-foreground">
                segments de texte
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/10 border-purple-500/20">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Stockage Utilisé</CardTitle>
              <HardDrive className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-600">
                {formatFileSize(stats.total_size)}
              </div>
              <p className="text-xs text-muted-foreground">
                espace de stockage
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="bg-gradient-to-br from-orange-500/10 to-orange-600/10 border-orange-500/20">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Taux de Réussite</CardTitle>
              <TrendingUp className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">
                {getProcessingSuccessRate().toFixed(1)}%
              </div>
              <p className="text-xs text-muted-foreground">
                traitement réussi
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Detailed Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Documents by Status */}
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChart className="w-5 h-5" />
                Statut des Documents
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm flex items-center gap-2">
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    Terminés
                  </span>
                  <span className="font-medium">{stats.documents_by_status.completed}</span>
                </div>
                <Progress 
                  value={(stats.documents_by_status.completed / Math.max(stats.total_documents, 1)) * 100} 
                  className="h-2"
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm flex items-center gap-2">
                    <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                    En traitement
                  </span>
                  <span className="font-medium">{stats.documents_by_status.processing}</span>
                </div>
                <Progress 
                  value={(stats.documents_by_status.processing / Math.max(stats.total_documents, 1)) * 100} 
                  className="h-2"
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm flex items-center gap-2">
                    <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                    En attente
                  </span>
                  <span className="font-medium">{stats.documents_by_status.pending}</span>
                </div>
                <Progress 
                  value={(stats.documents_by_status.pending / Math.max(stats.total_documents, 1)) * 100} 
                  className="h-2"
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm flex items-center gap-2">
                    <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                    Échecs
                  </span>
                  <span className="font-medium">{stats.documents_by_status.failed}</span>
                </div>
                <Progress 
                  value={(stats.documents_by_status.failed / Math.max(stats.total_documents, 1)) * 100} 
                  className="h-2"
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Documents by Type */}
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Types de Fichiers
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {Object.entries(stats.documents_by_type).map(([type, count]) => (
                <div key={type} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium uppercase">{type}</span>
                    <span className="text-sm text-muted-foreground">{count} fichier{count > 1 ? 's' : ''}</span>
                  </div>
                  <Progress 
                    value={(count / Math.max(stats.total_documents, 1)) * 100} 
                    className="h-2"
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Storage and Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HardDrive className="w-5 h-5" />
                Utilisation du Stockage
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Espace utilisé</span>
                  <span className="text-sm font-medium">{formatFileSize(stats.total_size)}</span>
                </div>
                <Progress value={getStorageUsagePercentage()} className="h-3" />
                <p className="text-xs text-muted-foreground">
                  {getStorageUsagePercentage().toFixed(1)}% de l'espace estimé utilisé
                </p>
              </div>

              <div className="pt-4 border-t border-border">
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div>
                    <div className="text-lg font-bold">
                      {formatFileSize(stats.total_size / Math.max(stats.total_documents, 1))}
                    </div>
                    <div className="text-xs text-muted-foreground">Taille moyenne</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold">
                      {Math.round(stats.total_chunks / Math.max(stats.total_documents, 1))}
                    </div>
                    <div className="text-xs text-muted-foreground">Chunks par doc</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5" />
                Métriques de Performance
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-4 bg-muted/30 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {getProcessingSuccessRate().toFixed(0)}%
                  </div>
                  <div className="text-xs text-muted-foreground">Taux de réussite</div>
                </div>
                
                <div className="text-center p-4 bg-muted/30 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {stats.documents_by_status.processing}
                  </div>
                  <div className="text-xs text-muted-foreground">En cours</div>
                </div>
              </div>

              <div className="pt-4 border-t border-border">
                <div className="flex items-center justify-between text-sm">
                  <span>Documents traités avec succès</span>
                  <span className="font-medium text-green-600">
                    {stats.documents_by_status.completed}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm mt-2">
                  <span>Documents en échec</span>
                  <span className="font-medium text-red-600">
                    {stats.documents_by_status.failed}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </motion.div>
  )
}