/**
 * Hook simplifié pour le chat sans gestion complexe du store
 */

import { useCallback } from 'react'
import { useAppStore } from '@/lib/store'
import { useChat } from './use-api'
import { ChatRequest } from '@/lib/api-client'
import toast from 'react-hot-toast'

export function useSimpleChat() {
  const {
    currentConversationId,
    setCurrentConversationId,
    addConversation,
    updateConversation
  } = useAppStore()

  const { sendMessage: apiSendMessage, sending } = useChat()

  const sendMessage = useCallback(async (request: ChatRequest) => {
    try {
      // Envoyer directement à l'API sans gestion complexe du store
      const response = await apiSendMessage(request)

      // Mettre à jour seulement la liste des conversations
      if (response.conversation) {
        updateConversation(response.conversation.id, {
          id: response.conversation.id,
          title: response.conversation.title,
          created_at: response.conversation.created_at,
          updated_at: response.conversation.updated_at,
          message_count: response.conversation.message_count,
          last_message_preview: response.message.content.slice(0, 100)
        })
      }

      return response
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('Erreur lors de l\'envoi du message')
      throw error
    }
  }, [apiSendMessage, updateConversation])

  const createNewConversation = useCallback((title: string) => {
    const conversationId = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    const newConversation = {
      id: conversationId,
      title: title.slice(0, 50) + (title.length > 50 ? '...' : ''),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message_count: 0,
      last_message_preview: ''
    }

    addConversation(newConversation)
    setCurrentConversationId(conversationId)

    return conversationId
  }, [addConversation, setCurrentConversationId])

  return {
    sendMessage,
    sending,
    createNewConversation,
    currentConversationId
  }
}