'use client'

import { Button } from '@/components/ui/button'
import { useAppStore } from '@/lib/store'
import { generateId } from '@/lib/utils'
import {
  Brain,
  Upload,
  Search,
  FileSearch,
  FileText,
  Sparkles
} from 'lucide-react'
import { motion } from 'framer-motion'

export function WelcomeScreen() {
  const {
    addConversation,
    setCurrentConversationId,
    setUploadModalOpen,
    setSearchModalOpen
  } = useAppStore()

  const handleQuickAction = (action: string) => {
    const newConversation = {
      id: generateId(),
      title: 'Nouvelle conversation',
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    
    addConversation(newConversation)
    setCurrentConversationId(newConversation.id)

    // Vous pouvez ajouter ici la logique pour pré-remplir le message selon l'action
  }

  const quickActions = [
    {
      id: 'upload',
      title: 'Uploader',
      description: 'Documents PDF, DOCX',
      icon: Upload,
      color: 'from-pastel-pink to-pastel-blue',
      action: () => setUploadModalOpen(true)
    },
    {
      id: 'search',
      title: 'Rechercher',
      description: 'Recherche sémantique',
      icon: Search,
      color: 'from-pastel-green to-pastel-blue',
      action: () => setSearchModalOpen(true)
    },
    {
      id: 'analyze',
      title: 'Analyser',
      description: 'Analyse de contenu',
      icon: FileSearch,
      color: 'from-pastel-purple to-pastel-pink',
      action: () => handleQuickAction('analyze')
    },
    {
      id: 'summarize',
      title: 'Résumer',
      description: 'Synthèse automatique',
      icon: FileText,
      color: 'from-pastel-orange to-pastel-yellow',
      action: () => handleQuickAction('summarize')
    }
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="max-w-4xl text-center space-y-8"
    >
      {/* Hero Section */}
      <div className="space-y-4">
        <motion.div
          initial={{ scale: 0.8 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring", damping: 20 }}
          className="w-20 h-20 bg-gradient-to-br from-pastel-purple via-pastel-blue to-pastel-green rounded-3xl flex items-center justify-center mx-auto shadow-2xl"
        >
          <Brain className="w-10 h-10 text-white" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="space-y-3"
        >
          <h1 className="text-4xl font-bold bg-gradient-to-r from-primary via-pastel-purple to-pastel-blue bg-clip-text text-transparent">
            StudyRAG Assistant
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Votre assistant IA pour l'analyse de documents académiques
          </p>
          <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
            Uploadez vos documents, posez des questions et obtenez des réponses contextualisées 
            avec des citations précises.
          </p>
        </motion.div>
      </div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="grid grid-cols-2 lg:grid-cols-4 gap-4"
      >
          {quickActions.map((action, index) => (
            <motion.div
              key={action.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 + index * 0.1 }}
              whileHover={{ scale: 1.05, y: -5 }}
              whileTap={{ scale: 0.95 }}
            >
              <Button
                variant="ghost"
                className="h-auto p-4 flex flex-col items-center space-y-3 bg-card/50 backdrop-blur-sm border border-border/50 hover:bg-card/80 transition-all duration-300 group"
                onClick={action.action}
              >
                <div className={`w-12 h-12 bg-gradient-to-br ${action.color} rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300`}>
                  <action.icon className="w-6 h-6 text-white" />
                </div>
                <div className="space-y-1">
                  <p className="font-medium text-sm">{action.title}</p>
                  <p className="text-xs text-muted-foreground">{action.description}</p>
                </div>
              </Button>
            </motion.div>
          ))}
        </motion.div>

      {/* Features */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
      >
        <div className="space-y-2">
          <div className="w-10 h-10 bg-gradient-to-br from-pastel-pink to-pastel-purple rounded-lg flex items-center justify-center mx-auto">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <h3 className="font-medium text-sm">IA Locale</h3>
          <p className="text-xs text-muted-foreground">
            Traitement local avec Ollama
          </p>
        </div>

        <div className="space-y-2">
          <div className="w-10 h-10 bg-gradient-to-br from-pastel-blue to-pastel-green rounded-lg flex items-center justify-center mx-auto">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <h3 className="font-medium text-sm">Multi-formats</h3>
          <p className="text-xs text-muted-foreground">
            PDF, DOCX, TXT, MD et plus
          </p>
        </div>

        <div className="space-y-2">
          <div className="w-10 h-10 bg-gradient-to-br from-pastel-green to-pastel-yellow rounded-lg flex items-center justify-center mx-auto">
            <Search className="w-5 h-5 text-white" />
          </div>
          <h3 className="font-medium text-sm">Recherche Sémantique</h3>
          <p className="text-xs text-muted-foreground">
            Trouvez sans mots-clés exacts
          </p>
        </div>
      </motion.div>
    </motion.div>
  )
}