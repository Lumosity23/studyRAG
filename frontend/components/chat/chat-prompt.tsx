'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useAppStore } from '@/lib/store'
import { useSimpleChat } from '@/hooks/use-simple-chat'
import { cn } from '@/lib/utils'
import {
  Send,
  Paperclip,
  Loader2,
  Plus,
  Sparkles
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface ChatPromptProps {
  centered?: boolean
  onStartChat?: () => void
}

export function ChatPrompt({ centered = false, onStartChat }: ChatPromptProps) {
  const {
    isTyping,
    setIsTyping
  } = useAppStore()

  const { 
    sendMessage, 
    sending, 
    createNewConversation,
    currentConversationId 
  } = useSimpleChat()

  const [message, setMessage] = useState('')
  const [charCount, setCharCount] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const maxChars = 4000

  useEffect(() => {
    if (centered && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [centered])

  const handleInputChange = (value: string) => {
    setMessage(value)
    setCharCount(value.length)
    
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const newHeight = Math.min(textareaRef.current.scrollHeight, centered ? 200 : 128)
      textareaRef.current.style.height = newHeight + 'px'
    }
  }

  const handleSendMessage = async () => {
    if (!message.trim() || charCount > maxChars || sending) return

    const messageContent = message.trim()
    
    // Si pas de conversation active, en créer une nouvelle
    let conversationId = currentConversationId
    if (!conversationId) {
      conversationId = createNewConversation(messageContent)
      // Déclencher l'animation de transition
      onStartChat?.()
    }

    setMessage('')
    setCharCount(0)
    setIsTyping(true)

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    try {
      await sendMessage({
        message: messageContent,
        conversation_id: conversationId,
      })
    } catch (error) {
      console.error('Error sending message:', error)
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const suggestions = [
    "Résume ce document en 3 points clés",
    "Quelles sont les idées principales ?",
    "Explique-moi ce concept en détail",
    "Compare ces deux approches"
  ]

  return (
    <motion.div
      layout
      className={cn(
        "w-full transition-all duration-500 ease-out",
        centered ? "max-w-3xl mx-auto" : "max-w-4xl mx-auto"
      )}
    >
      {/* Suggestions (uniquement en mode centré) */}
      <AnimatePresence>
        {centered && !message && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ delay: 0.2 }}
            className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-3"
          >
            {suggestions.map((suggestion, index) => (
              <motion.button
                key={suggestion}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + index * 0.1 }}
                onClick={() => setMessage(suggestion)}
                className="p-4 text-left bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl hover:bg-card/80 hover:border-border transition-all duration-200 group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-pastel-purple to-pastel-blue rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-sm font-medium">{suggestion}</span>
                </div>
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Container */}
      <motion.div
        layout
        className={cn(
          "relative bg-card/50 backdrop-blur-xl border border-border/50 rounded-2xl shadow-lg transition-all duration-300",
          centered ? "shadow-2xl" : "shadow-sm",
          "focus-within:border-primary/50 focus-within:shadow-xl"
        )}
      >
        <Textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={centered 
            ? "Que voulez-vous savoir sur vos documents ?" 
            : "Posez votre question ici... (Shift + Entrée pour une nouvelle ligne)"
          }
          className={cn(
            "resize-none bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 pr-24",
            centered ? "min-h-[80px] max-h-[200px] text-lg" : "min-h-[60px] max-h-32"
          )}
          disabled={isTyping}
        />

        {/* Action Buttons */}
        <div className="absolute right-3 bottom-3 flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 hover:bg-muted/50 transition-colors"
            disabled={isTyping}
          >
            <Paperclip className="w-4 h-4" />
          </Button>

          <Button
            onClick={handleSendMessage}
            disabled={!message.trim() || charCount > maxChars || sending || isTyping}
            size="icon"
            className={cn(
              "h-9 w-9 transition-all duration-300",
              centered 
                ? "bg-gradient-to-r from-pastel-purple via-pastel-blue to-pastel-green hover:scale-110 shadow-lg" 
                : "bg-gradient-to-r from-pastel-purple to-pastel-blue hover:from-pastel-pink hover:to-pastel-green"
            )}
          >
            {(sending || isTyping) ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </motion.div>

      {/* Footer Info */}
      <motion.div
        layout
        className="flex items-center justify-between mt-3 text-xs text-muted-foreground px-1"
      >
        <span>
          {centered ? "Appuyez sur Entrée pour envoyer" : "Utilisez Shift + Entrée pour une nouvelle ligne"}
        </span>
        <span className={cn(
          "transition-colors",
          charCount > maxChars && "text-destructive"
        )}>
          {charCount} / {maxChars}
        </span>
      </motion.div>

      {/* New Chat Button (mode non-centré seulement) */}
      {!centered && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute -top-12 right-0"
        >
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              // Utiliser le store pour réinitialiser
              const { setCurrentConversationId, setCurrentConversationHistory } = useAppStore.getState()
              setCurrentConversationId(null)
              setCurrentConversationHistory(null)
              setMessage('')
              setCharCount(0)
            }}
            className="gap-2 hover:bg-card/50"
          >
            <Plus className="w-4 h-4" />
            Nouvelle conversation
          </Button>
        </motion.div>
      )}
    </motion.div>
  )
}