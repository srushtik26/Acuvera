import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import './index.css'

const LoginPage = React.lazy(() => import('./pages/LoginPage'))
const NurseDashboard = React.lazy(() => import('./pages/Nurse/NurseDashboard'))
const DoctorDashboard = React.lazy(() => import('./pages/Doctor/DoctorDashboard'))
const AdminDashboard = React.lazy(() => import('./pages/Admin/AdminDashboard'))
const ParamedicPage = React.lazy(() => import('./pages/ParamedicPage'))

function getRoleHome(role) {
  if (role === 'nurse') return '/nurse'
  if (role === 'doctor') return '/doctor'
  return '/admin'
}

// ─── Route guards ─────────────────────────────────────────────
function RequireAuth({ children, allowedRoles }) {
  const { user, isLoading } = useAuthStore()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="loading-center" style={{ height: '100vh' }}>
        <div className="spinner" /><span>Loading...</span>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={getRoleHome(user.role)} replace />
  }
  return children
}

// AutoRoute waits for isLoading before deciding — breaks the Clerk redirect loop
function AutoRoute() {
  const { user, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="loading-center" style={{ height: '100vh' }}>
        <div className="spinner" /><span>Signing in...</span>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={getRoleHome(user.role)} replace />
}

export default function App() {
  const { fetchUser, token } = useAuthStore()

  // On app load: restore session from any persisted token (JWT or dev-bypass)
  useEffect(() => {
    if (token) {
      fetchUser()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <BrowserRouter>
      <React.Suspense fallback={
        <div className="loading-center" style={{ height: '100vh' }}>
          <div className="spinner" />
        </div>
      }>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<AutoRoute />} />
          <Route path="/nurse/*" element={
            <RequireAuth allowedRoles={['nurse', 'admin']}>
              <NurseDashboard />
            </RequireAuth>
          } />
          <Route path="/doctor/*" element={
            <RequireAuth allowedRoles={['doctor', 'admin', 'dept_head']}>
              <DoctorDashboard />
            </RequireAuth>
          } />
          <Route path="/admin/*" element={
            <RequireAuth allowedRoles={['admin', 'dept_head']}>
              <AdminDashboard />
            </RequireAuth>
          } />
          <Route path="/paramedic" element={<ParamedicPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </React.Suspense>
    </BrowserRouter>
  )
}
