'use client'

import { useState, useEffect } from 'react'
import { ChatArea } from './chat-area'
import { ChatPrompt } from './chat-prompt'
import { WelcomeScreen } from './welcome-screen'
import { useAppStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'

export function ChatInterface() {
  const { currentConversationId, currentConversationHistory } = useAppStore()
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [showCenteredPrompt, setShowCenteredPrompt] = useState(true)

  // Gérer la transition quand une conversation commence
  useEffect(() => {
    if (currentConversationId) {
      if (showCenteredPrompt) {
        setIsTransitioning(true)
        // Délai pour l'animation de transition
        setTimeout(() => {
          setShowCenteredPrompt(false)
          setIsTransitioning(false)
        }, 600)
      }
    } else {
      setShowCenteredPrompt(true)
      setIsTransitioning(false)
    }
  }, [currentConversationId, showCenteredPrompt])

  const handleStartChat = () => {
    setIsTransitioning(true)
  }

  // Mode conversation active
  if (currentConversationId && !showCenteredPrompt) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="flex-1 flex flex-col h-full"
      >
        <ChatArea />
      </motion.div>
    )
  }

  // Mode centré (accueil ou transition)
  return (
    <div className="flex-1 flex flex-col h-full relative overflow-hidden">
      <AnimatePresence mode="wait">
        {!isTransitioning && (
          <motion.div
            key="welcome"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className="flex-1 flex flex-col"
          >
            {/* Welcome Content */}
            <div className="flex-1 flex items-center justify-center p-8">
              <WelcomeScreen />
            </div>

            {/* Centered Chat Prompt */}
            <motion.div
              layout
              className="pb-8 px-8"
              initial={{ y: 50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.5 }}
            >
              <ChatPrompt 
                centered={true} 
                onStartChat={handleStartChat}
              />
            </motion.div>
          </motion.div>
        )}

        {isTransitioning && (
          <motion.div
            key="transition"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex-1 flex items-center justify-center"
          >
            <motion.div
              initial={{ scale: 1, y: 0 }}
              animate={{ scale: 0.8, y: -100 }}
              transition={{ duration: 0.6, ease: "easeInOut" }}
              className="w-full max-w-3xl px-8"
            >
              <ChatPrompt 
                centered={true} 
                onStartChat={handleStartChat}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Background Gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-muted/10 -z-10" />
      
      {/* Floating Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none -z-10">
        <motion.div
          animate={{
            x: [0, 100, 0],
            y: [0, -50, 0],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          }}
          className="absolute top-1/4 left-1/4 w-64 h-64 bg-gradient-to-br from-pastel-purple/10 to-pastel-blue/10 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            x: [0, -80, 0],
            y: [0, 60, 0],
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: "linear"
          }}
          className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-gradient-to-br from-pastel-green/10 to-pastel-pink/10 rounded-full blur-3xl"
        />
      </div>
    </div>
  )
}