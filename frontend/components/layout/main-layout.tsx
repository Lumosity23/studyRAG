'use client'

import { Sidebar } from './sidebar'
import { TopBar } from './top-bar'
import { useAppStore } from '@/lib/store'
import { cn } from '@/lib/utils'

interface MainLayoutProps {
  children: React.ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  const { sidebarOpen } = useAppStore()

  return (
    <div className="h-screen flex bg-gradient-to-br from-background via-background to-muted/20">
      {/* Sidebar */}
      <div className={cn(
        "transition-all duration-300 ease-in-out",
        sidebarOpen ? "w-80" : "w-0"
      )}>
        <Sidebar />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  )
}