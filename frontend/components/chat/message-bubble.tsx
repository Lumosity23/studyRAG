'use client'

import { AppMessage } from '@/lib/store'
import { cn } from '@/lib/utils'
import { User, Bot, Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useState } from 'react'
import { motion } from 'framer-motion'

interface MessageBubbleProps {
  message: AppMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "flex gap-4 group",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
        isUser 
          ? "bg-gradient-to-br from-pastel-green to-pastel-blue" 
          : "bg-gradient-to-br from-pastel-purple to-pastel-pink"
      )}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={cn(
        "flex-1 max-w-3xl",
        isUser ? "text-right" : "text-left"
      )}>
        <div className={cn(
          "inline-block px-4 py-3 rounded-2xl relative group/message",
          isUser 
            ? "bg-gradient-to-br from-pastel-blue to-pastel-green text-white ml-auto" 
            : "bg-card border border-border"
        )}>
          {/* Message Text */}
          <div className={cn(
            "prose prose-sm max-w-none",
            isUser ? "prose-invert" : "prose-neutral dark:prose-invert"
          )}>
            <p className="whitespace-pre-wrap break-words m-0">
              {message.content}
            </p>
          </div>

          {/* Copy Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={copyToClipboard}
            className={cn(
              "absolute -top-2 -right-2 w-6 h-6 opacity-0 group-hover/message:opacity-100 transition-opacity",
              isUser 
                ? "bg-white/20 hover:bg-white/30 text-white" 
                : "bg-muted hover:bg-muted/80"
            )}
          >
            {copied ? (
              <Check className="w-3 h-3" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </Button>
        </div>

        {/* Timestamp */}
        <div className={cn(
          "text-xs text-muted-foreground mt-1 px-1",
          isUser ? "text-right" : "text-left"
        )}>
          {new Date(message.timestamp).toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>

        {/* Sources (for assistant messages) */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Sources :</p>
            <div className="space-y-1">
              {message.sources.map((source, index) => (
                <div
                  key={index}
                  className="text-xs bg-muted/50 rounded-lg p-2 border border-border/50"
                >
                  <div className="font-medium text-foreground mb-1">
                    {source.document_filename}
                  </div>
                  <div className="text-muted-foreground line-clamp-2">
                    {source.chunk_content}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}