import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AppconfigPage from './pages/AppconfigPage'
import MetagitConfigPage from './pages/MetagitConfigPage'
import WorkspacePage from './pages/WorkspacePage'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/workspace" replace />} />
          <Route path="/workspace" element={<WorkspacePage />} />
          <Route path="/config/metagit" element={<MetagitConfigPage />} />
          <Route path="/config/appconfig" element={<AppconfigPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
