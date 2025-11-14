'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { useAppStore } from '@/lib/store'
import { useConversations, useConversationHistory } from '@/hooks/use-api'
import { formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'
import {
  Brain,
  Plus,
  MessageCircle,
  FileText,
  Search,
  Settings,
  Trash2,
  Calendar,
  FolderOpen
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'

export function Sidebar() {
  const {
    sidebarOpen,
    currentConversationId,
    setCurrentConversationId,
    setCurrentConversationHistory,
    setUploadModalOpen,
    setSearchModalOpen,
    setSettingsModalOpen
  } = useAppStore()

  const {
    conversations,
    loading: conversationsLoading,
    deleteConversation: deleteConv
  } = useConversations()

  const [hoveredConversation, setHoveredConversation] = useState<string | null>(null)

  const createNewConversation = () => {
    // Réinitialiser la conversation actuelle pour déclencher l'écran de bienvenue
    setCurrentConversationId(null)
    toast.success('Nouvelle conversation créée')
  }

  const handleSelectConversation = async (conversationId: string) => {
    try {
      setCurrentConversationId(conversationId)
      
      // Charger l'historique de la conversation
      const response = await fetch(`http://localhost:8000/api/v1/chat/conversations/${conversationId}`)
      if (response.ok) {
        const history = await response.json()
        setCurrentConversationHistory(history)
      } else {
        console.error('Failed to load conversation history')
        toast.error('Erreur lors du chargement de la conversation')
      }
    } catch (error) {
      console.error('Error loading conversation:', error)
      toast.error('Erreur lors du chargement de la conversation')
    }
  }

  const handleDeleteConversation = async (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation()
    await deleteConv(conversationId)
  }

  if (!sidebarOpen) return null

  return (
    <motion.div
      initial={{ x: -320 }}
      animate={{ x: 0 }}
      exit={{ x: -320 }}
      transition={{ type: "spring", damping: 20, stiffness: 300 }}
      className="h-full w-80 bg-card/50 backdrop-blur-xl border-r border-border/50 flex flex-col"
    >
      {/* Header */}
      <div className="p-6 border-b border-border/50">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-gradient-to-br from-pastel-purple to-pastel-blue rounded-xl flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
              StudyRAG
            </h1>
            <p className="text-xs text-muted-foreground">Assistant IA</p>
          </div>
        </div>

        <Button
          onClick={createNewConversation}
          className="w-full bg-gradient-to-r from-pastel-pink to-pastel-blue hover:from-pastel-purple hover:to-pastel-green text-foreground font-medium transition-all duration-300"
          size="lg"
        >
          <Plus className="w-4 h-4 mr-2" />
          Nouvelle conversation
        </Button>
      </div>

      {/* Navigation */}
      <div className="px-4 py-4">
        <div className="space-y-1">
          <Button
            variant="ghost"
            className="w-full justify-start hover:bg-pastel-pink/20"
            onClick={() => window.location.href = '/documents'}
          >
            <FileText className="w-4 h-4 mr-3" />
            Gestion Documents
          </Button>
          
          <Button
            variant="ghost"
            className="w-full justify-start hover:bg-pastel-blue/20"
            onClick={() => setSearchModalOpen(true)}
          >
            <Search className="w-4 h-4 mr-3" />
            Recherche
          </Button>
          
          <Button
            variant="ghost"
            className="w-full justify-start hover:bg-pastel-green/20"
          >
            <Calendar className="w-4 h-4 mr-3" />
            Calendrier
          </Button>
          
          <Button
            variant="ghost"
            className="w-full justify-start hover:bg-pastel-orange/20"
          >
            <FolderOpen className="w-4 h-4 mr-3" />
            Gestionnaire
          </Button>
        </div>
      </div>

      <Separator className="mx-4" />

      {/* Conversations */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="px-4 py-3">
          <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <MessageCircle className="w-4 h-4" />
            Conversations
          </h3>
        </div>

        <ScrollArea className="flex-1 px-2">
          <AnimatePresence>
            {conversationsLoading ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="px-4 py-8 text-center text-muted-foreground"
              >
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="text-sm">Chargement...</p>
              </motion.div>
            ) : !conversations || conversations.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="px-4 py-8 text-center text-muted-foreground"
              >
                <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Aucune conversation</p>
              </motion.div>
            ) : (
              <div className="space-y-1 pb-4">
                {conversations.map((conversation) => (
                  <motion.div
                    key={conversation.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.2 }}
                    className="relative group"
                    onMouseEnter={() => setHoveredConversation(conversation.id)}
                    onMouseLeave={() => setHoveredConversation(null)}
                  >
                    <Button
                      variant="ghost"
                      className={cn(
                        "w-full justify-start text-left p-3 h-auto hover:bg-accent/50 transition-all duration-200",
                        currentConversationId === conversation.id && "bg-accent text-accent-foreground"
                      )}
                      onClick={() => handleSelectConversation(conversation.id)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {conversation.title}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
                          {conversation.last_message_preview || 'Pas de messages'}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatDate(conversation.updated_at)}
                        </p>
                      </div>
                    </Button>

                    {/* Delete button */}
                    <AnimatePresence>
                      {hoveredConversation === conversation.id && (
                        <motion.button
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.8 }}
                          transition={{ duration: 0.1 }}
                          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
                          onClick={(e) => handleDeleteConversation(e, conversation.id)}
                        >
                          <Trash2 className="w-3 h-3" />
                        </motion.button>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))}
              </div>
            )}
          </AnimatePresence>
        </ScrollArea>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border/50">
        <Button
          variant="ghost"
          className="w-full justify-start hover:bg-muted/50"
          onClick={() => setSettingsModalOpen(true)}
        >
          <Settings className="w-4 h-4 mr-3" />
          Paramètres
        </Button>
      </div>
    </motion.div>
  )
}