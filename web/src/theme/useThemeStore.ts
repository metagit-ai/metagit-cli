import { create } from 'zustand'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'metagit-web-theme'

function readStoredMode(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'system'
  }
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored
  }
  return 'system'
}

function resolveTheme(mode: ThemeMode): 'light' | 'dark' {
  if (mode === 'light' || mode === 'dark') {
    return mode
  }
  if (typeof window === 'undefined') {
    return 'light'
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

function applyTheme(mode: ThemeMode): void {
  if (typeof document === 'undefined') {
    return
  }
  const resolved = resolveTheme(mode)
  document.documentElement.dataset.theme = resolved
}

interface ThemeState {
  mode: ThemeMode
  resolved: 'light' | 'dark'
  setMode: (mode: ThemeMode) => void
  toggleResolved: () => void
  init: () => void
  syncSystemTheme: () => void
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  mode: readStoredMode(),
  resolved: resolveTheme(readStoredMode()),

  setMode: (mode) => {
    window.localStorage.setItem(STORAGE_KEY, mode)
    applyTheme(mode)
    set({ mode, resolved: resolveTheme(mode) })
  },

  toggleResolved: () => {
    const next = get().resolved === 'dark' ? 'light' : 'dark'
    get().setMode(next)
  },

  init: () => {
    const mode = readStoredMode()
    applyTheme(mode)
    set({ mode, resolved: resolveTheme(mode) })
  },

  syncSystemTheme: () => {
    if (get().mode === 'system') {
      applyTheme('system')
      set({ resolved: resolveTheme('system') })
    }
  },
}))

applyTheme(readStoredMode())
