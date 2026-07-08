import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import api from '../../services/api'
import type { ApiResponse } from '../../types'
import {
  Users, Calendar, Gavel, Layers, BookOpen, ClipboardList,
  Upload, FileText, Files, type LucideIcon,
} from 'lucide-react'

interface Periodo { id: number; nombre: string; activo: boolean }
interface Informe { id: number; estado: string }

const ACCESOS: { to: string; label: string; icon: LucideIcon }[] = [
  { to: '/director/usuarios', label: 'Usuarios', icon: Users },
  { to: '/director/periodos', label: 'Períodos', icon: Calendar },
  { to: '/director/consejos', label: 'Consejos de Carrera', icon: Gavel },
  { to: '/director/areas', label: 'Áreas', icon: Layers },
  { to: '/director/asignaturas', label: 'Asignaturas', icon: BookOpen },
  { to: '/director/asignaciones', label: 'Asignaciones docente', icon: ClipboardList },
  { to: '/director/calificaciones', label: 'Subir Calificaciones', icon: Upload },
  { to: '/director/informe1', label: 'Informe 1', icon: FileText },
  { to: '/director/informes', label: 'Ver Informes', icon: Files },
]

export default function DirectorDashboard() {
  const { user } = useAuth()
  const [periodoActivo, setPeriodoActivo] = useState<string>('—')
  const [generados, setGenerados] = useState(0)
  const [pendientes, setPendientes] = useState(0)

  useEffect(() => {
    api.get<ApiResponse<Periodo | null>>('/periodos/activo')
      .then((r) => { if (r.data.data) setPeriodoActivo(r.data.data.nombre) })
      .catch(() => {})
    api.get<ApiResponse<Informe[]>>('/informes/')
      .then((r) => {
        const lista = r.data.data
        setGenerados(lista.length)
        setPendientes(lista.filter((i) => i.estado !== 'APROBADO').length)
      })
      .catch(() => {})
  }, [])

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">
        Bienvenido, {user?.nombre_completo}
      </h1>
      <p className="text-gray-500 text-sm mb-6">Panel de la Dirección de Carrera</p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Período activo" value={periodoActivo} />
        <StatCard label="Informes generados" value={String(generados)} />
        <StatCard label="Informes pendientes" value={String(pendientes)} />
      </div>

      <div className="mt-8">
        <h2 className="font-semibold text-gray-700 mb-3">Accesos rápidos</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {ACCESOS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="bg-white rounded-xl border p-4 flex items-center gap-3 hover:border-ups-blue hover:shadow-sm transition"
            >
              <span className="bg-ups-blue/10 text-ups-blue rounded-lg p-2">
                <Icon size={20} strokeWidth={1.9} />
              </span>
              <span className="text-sm font-medium text-gray-700">{label}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-xl border p-5 flex flex-col gap-1">
      <span className="text-3xl font-bold text-ups-blue truncate">{value}</span>
      <span className="text-sm text-gray-500">{label}</span>
    </div>
  )
}
