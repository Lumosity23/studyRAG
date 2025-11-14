/**
 * Hook personnalisé pour gérer les messages de chat avec le store
 */

import { useCallback } from 'react'
import { useAppStore } from '@/lib/store'
import { useChat } from './use-api'
import { ChatRequest } from '@/lib/api-client'
import toast from 'react-hot-toast'

export function useChatMessages() {
  const {
    currentConversationId,
    currentConversationHistory,
    setCurrentConversationHistory,
    addConversation,
    setCurrentConversationId,
    updateConversation
  } = useAppStore()

  const { sendMessage: apiSendMessage, sending } = useChat()

  const sendMessage = useCallback(async (request: ChatRequest) => {
    try {
      // Ajouter le message utilisateur au store immédiatement
      const userMessage = {
        id: `user_${Date.now()}`,
        role: 'user' as const,
        content: request.message,
        timestamp: new Date().toISOString(),
        sources: []
      }

      // Mettre à jour l'historique local
      if (currentConversationHistory) {
        const existingMessages = Array.isArray(currentConversationHistory.messages) 
          ? currentConversationHistory.messages 
          : []
        const updatedHistory = {
          ...currentConversationHistory,
          messages: [...existingMessages, userMessage]
        }
        setCurrentConversationHistory(updatedHistory)
      }

      // Envoyer le message à l'API
      const response = await apiSendMessage(request)

      // Ajouter la réponse de l'assistant au store
      const assistantMessage = {
        id: response.message.id,
        role: 'assistant' as const,
        content: response.message.content,
        timestamp: response.message.created_at,
        sources: response.message.sources || []
      }

      // Mettre à jour l'historique avec la réponse
      const existingMessages = currentConversationHistory && Array.isArray(currentConversationHistory.messages)
        ? currentConversationHistory.messages
        : []
      
      const finalHistory = {
        id: response.conversation.id,
        title: response.conversation.title,
        messages: [...existingMessages, userMessage, assistantMessage],
        created_at: response.conversation.created_at,
        updated_at: response.conversation.updated_at,
        message_count: response.conversation.message_count,
        last_message_at: response.conversation.last_message_at,
        model_name: response.conversation.model_name
      }

      setCurrentConversationHistory(finalHistory)

      // Mettre à jour la conversation dans la liste
      updateConversation(response.conversation.id, {
        id: response.conversation.id,
        title: response.conversation.title,
        created_at: response.conversation.created_at,
        updated_at: response.conversation.updated_at,
        message_count: response.conversation.message_count,
        last_message_preview: response.message.content.slice(0, 100)
      })

      return response
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('Erreur lors de l\'envoi du message')
      throw error
    }
  }, [
    currentConversationId,
    currentConversationHistory,
    setCurrentConversationHistory,
    addConversation,
    setCurrentConversationId,
    updateConversation,
    apiSendMessage
  ])

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

    const newHistory = {
      id: conversationId,
      title: newConversation.title,
      messages: [],
      created_at: newConversation.created_at,
      updated_at: newConversation.updated_at,
      message_count: 0,
      last_message_at: newConversation.created_at,
      model_name: 'deepseek-r1:1.5b'
    }

    addConversation(newConversation)
    setCurrentConversationId(conversationId)
    setCurrentConversationHistory(newHistory)

    return conversationId
  }, [addConversation, setCurrentConversationId, setCurrentConversationHistory])

  return {
    sendMessage,
    sending,
    createNewConversation,
    currentConversationId,
    currentConversationHistory
  }
}