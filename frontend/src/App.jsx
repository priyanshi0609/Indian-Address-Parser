import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'

function ProtectedRoute({ children }) {
  const { isSignedIn, isLoaded } = useAuth()
  if (!isLoaded) return null
  return isSignedIn ? children : <Navigate to="/" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}