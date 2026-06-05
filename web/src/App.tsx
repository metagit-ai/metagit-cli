import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ThemeProvider from './theme/ThemeProvider'
import AppconfigPage from './pages/AppconfigPage'
import MetagitConfigPage from './pages/MetagitConfigPage'
import AgentsPage from './pages/AgentsPage'
import WorkspacePage from './pages/WorkspacePage'
import './App.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Navigate to="/workspace" replace />} />
              <Route path="/workspace" element={<WorkspacePage />} />
              <Route path="/agents" element={<AgentsPage />} />
              <Route path="/config/metagit" element={<MetagitConfigPage />} />
              <Route path="/config/appconfig" element={<AppconfigPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
