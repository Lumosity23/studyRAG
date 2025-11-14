'use client'

import { useEffect } from 'react'
import { MainLayout } from '@/components/layout/main-layout'
import { ChatInterface } from '@/components/chat/chat-interface'
import { UploadModal } from '@/components/modals/upload-modal-simple'
import { useAppStore } from '@/lib/store'
import { useHealth } from '@/hooks/use-api'

export default function HomePage() {
  const { setIsConnected } = useAppStore()
  const { health: healthData, error: healthError } = useHealth()

  // Mettre à jour le statut de connexion
  useEffect(() => {
    setIsConnected(!healthError && healthData?.status === 'healthy')
  }, [healthData, healthError, setIsConnected])

  return (
    <MainLayout>
      <ChatInterface />
      
      {/* Modals */}
      <UploadModal />
    </MainLayout>
  )
}