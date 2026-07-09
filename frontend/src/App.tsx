import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import ProtectedRoute from './components/ProtectedRoute'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'

import Login from './pages/auth/Login'
import DirectorDashboard from './pages/director/Dashboard'
import Usuarios from './pages/director/Usuarios'
import Periodos from './pages/director/Periodos'
import Consejos from './pages/director/Consejos'
import Areas from './pages/director/Areas'
import Asignaturas from './pages/director/Asignaturas'
import Asignaciones from './pages/director/Asignaciones'
import SubirCalificaciones from './pages/director/SubirCalificaciones'
import Informe1 from './pages/director/Informe1'
import VerInformes from './pages/director/VerInformes'
import JefeDashboard from './pages/jefe_area/Dashboard'
import Informe1Jefe from './pages/jefe_area/Informe1'
import Informe2 from './pages/jefe_area/Informe2'
import Informe3 from './pages/jefe_area/Informe3'
import Informe4 from './pages/jefe_area/Informe4'
import DocenteDashboard from './pages/docente/Dashboard'
import DocenteObservaciones from './pages/docente/Observaciones'
import DocenteAccionesMejora from './pages/docente/AccionesMejora'
import { destinoPorRol } from './utils/roles'

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  )
}

function RootRedirect() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={destinoPorRol(user.rol)} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<RootRedirect />} />

      {/* Rutas del director */}
      <Route
        path="/director/*"
        element={
          <ProtectedRoute roles={['DIRECTOR_CARRERA']}>
            <AppLayout>
              <Routes>
                <Route index element={<DirectorDashboard />} />
                <Route path="usuarios" element={<Usuarios />} />
                <Route path="periodos" element={<Periodos />} />
                <Route path="consejos" element={<Consejos />} />
                <Route path="areas" element={<Areas />} />
                <Route path="asignaturas" element={<Asignaturas />} />
                <Route path="asignaciones" element={<Asignaciones />} />
                <Route path="calificaciones" element={<SubirCalificaciones />} />
                <Route path="informe1" element={<Informe1 />} />
                <Route path="informes" element={<VerInformes />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* Rutas del jefe de área */}
      <Route
        path="/jefe/*"
        element={
          <ProtectedRoute roles={['JEFE_AREA']}>
            <AppLayout>
              <Routes>
                <Route index element={<JefeDashboard />} />
                <Route path="calificaciones" element={<SubirCalificaciones />} />
                <Route path="informe1" element={<Informe1Jefe />} />
                <Route path="informe2" element={<Informe2 />} />
                <Route path="informe3" element={<Informe3 />} />
                <Route path="informe4" element={<Informe4 />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* Rutas del docente */}
      <Route
        path="/docente/*"
        element={
          <ProtectedRoute roles={['DOCENTE']}>
            <AppLayout>
              {/* El docente NO sube notas: solo consulta sus materias y registra aportes */}
              <Routes>
                <Route index element={<DocenteDashboard />} />
                <Route path="acciones-mejora" element={<DocenteAccionesMejora />} />
                <Route path="observaciones" element={<DocenteObservaciones />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/sin-acceso"
        element={
          <div className="flex items-center justify-center h-screen">
            <p className="text-gray-500">No tienes permisos para acceder a esta sección.</p>
          </div>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
