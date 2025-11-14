'use client'

import { Button } from '@/components/ui/button'
import { useAppStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import {
  Menu,
  Upload,
  Share,
  Calendar,
  FolderOpen,
  Search,
  Settings,
  Palette
} from 'lucide-react'
import { motion } from 'framer-motion'

export function TopBar() {
  const {
    sidebarOpen,
    setSidebarOpen,
    currentConversationId,
    conversations,
    setUploadModalOpen,
    setSearchModalOpen,
    setSettingsModalOpen
  } = useAppStore()

  const currentConversation = conversations.find(c => c.id === currentConversationId)

  return (
    <motion.header
      initial={{ y: -60 }}
      animate={{ y: 0 }}
      transition={{ type: "spring", damping: 20, stiffness: 300 }}
      className="h-16 bg-card/30 backdrop-blur-xl border-b border-border/50 flex items-center justify-between px-6"
    >
      {/* Left Section */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="hover:bg-pastel-pink/20 transition-colors"
        >
          <Menu className="w-5 h-5" />
        </Button>

        <div className="flex flex-col">
          <h2 className="text-lg font-semibold">
            {currentConversation?.title || 'StudyRAG Assistant'}
          </h2>
          <p className="text-sm text-muted-foreground">
            {currentConversation 
              ? `${currentConversation.message_count} messages`
              : 'Posez vos questions sur vos documents'
            }
          </p>
        </div>
      </div>

      {/* Center Section - Quick Actions */}
      <div className="hidden md:flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setUploadModalOpen(true)}
          className="hover:bg-pastel-blue/20 transition-colors"
        >
          <Upload className="w-4 h-4 mr-2" />
          Upload
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setSearchModalOpen(true)}
          className="hover:bg-pastel-green/20 transition-colors"
        >
          <Search className="w-4 h-4 mr-2" />
          Recherche
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className="hover:bg-pastel-purple/20 transition-colors"
        >
          <Calendar className="w-4 h-4 mr-2" />
          Calendrier
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className="hover:bg-pastel-orange/20 transition-colors"
        >
          <FolderOpen className="w-4 h-4 mr-2" />
          Fichiers
        </Button>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-2">
        {/* Connection Status */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 text-green-500">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-xs font-medium">Connecté</span>
        </div>

        <div className="w-px h-6 bg-border mx-2" />

        <Button
          variant="ghost"
          size="icon"
          className="hover:bg-pastel-yellow/20 transition-colors"
        >
          <Palette className="w-4 h-4" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          className="hover:bg-muted/50 transition-colors"
        >
          <Share className="w-4 h-4" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => setSettingsModalOpen(true)}
          className="hover:bg-muted/50 transition-colors"
        >
          <Settings className="w-4 h-4" />
        </Button>
      </div>
    </motion.header>
  )
}