'use client'

import * as React from 'react'
import { useAppStore } from '@/lib/store'

interface ThemeProviderProps {
  children: React.ReactNode
  attribute?: string
  defaultTheme?: string
  enableSystem?: boolean
  disableTransitionOnChange?: boolean
}

export function ThemeProvider({ 
  children, 
  attribute = "class",
  defaultTheme = "dark",
  enableSystem = true,
  disableTransitionOnChange = false 
}: ThemeProviderProps) {
  const { theme, colorTheme, setTheme } = useAppStore()

  React.useEffect(() => {
    // Appliquer le thème sombre/clair
    const root = document.documentElement
    
    if (theme === 'system' && enableSystem) {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      root.classList.toggle('dark', systemTheme === 'dark')
    } else {
      root.classList.toggle('dark', theme === 'dark')
    }
  }, [theme, enableSystem])

  React.useEffect(() => {
    // Appliquer le thème de couleur au body
    const body = document.body
    
    // Supprimer tous les anciens thèmes
    body.classList.remove('theme-rose', 'theme-ocean', 'theme-forest', 'theme-lavender', 'theme-sunset')
    
    // Ajouter le nouveau thème
    if (colorTheme !== 'default') {
      body.classList.add(`theme-${colorTheme}`)
    }
  }, [colorTheme])

  React.useEffect(() => {
    // Écouter les changements de préférence système
    if (enableSystem) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handleChange = () => {
        if (theme === 'system') {
          const root = document.documentElement
          root.classList.toggle('dark', mediaQuery.matches)
        }
      }
      
      mediaQuery.addEventListener('change', handleChange)
      return () => mediaQuery.removeEventListener('change', handleChange)
    }
  }, [theme, enableSystem])

  // Initialiser le thème par défaut
  React.useEffect(() => {
    if (!theme) {
      setTheme(defaultTheme as any)
    }
  }, [theme, defaultTheme, setTheme])

  return <>{children}</>
}