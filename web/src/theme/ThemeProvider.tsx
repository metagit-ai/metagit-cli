import { useEffect, type ReactNode } from 'react'
import { useThemeStore } from './useThemeStore'

interface ThemeProviderProps {
  children: ReactNode
}

export default function ThemeProvider({ children }: ThemeProviderProps) {
  const init = useThemeStore((state) => state.init)
  const syncSystemTheme = useThemeStore((state) => state.syncSystemTheme)

  useEffect(() => {
    init()
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => syncSystemTheme()
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [init, syncSystemTheme])

  return <>{children}</>
}
