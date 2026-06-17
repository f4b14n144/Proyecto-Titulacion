import { useState, useEffect } from 'react'
import api from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import type { ApiResponse } from '../../types'

interface MiAsignacion {
  id: number
  asignatura: string
  codigo: string
  grupo: string
  periodo: string
  periodo_activo: boolean
}

export default function DocenteDashboard() {
  const { user } = useAuth()
  const [asignaciones, setAsignaciones] = useState<MiAsignacion[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<ApiResponse<MiAsignacion[]>>('/asignaciones/mias')
      .then((res) => setAsignaciones(res.data.data))
      .catch(() => setError('No se pudieron cargar tus asignaciones.'))
      .finally(() => setCargando(false))
  }, [])

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">
        Bienvenido, {user?.nombre_completo}
      </h1>
      <p className="text-gray-500 text-sm mb-6">Panel del Docente</p>

      {/* Explicación del flujo por correo */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4 mb-6 text-sm text-blue-800">
        <p className="font-medium mb-1">¿Cómo participas en el proceso de informes?</p>
        <p>
          Cuando la Dirección active el flujo de un Consejo de Carrera, recibirás un
          <strong> correo institucional</strong> solicitando tus observaciones sobre cada
          asignatura que dictas. Solo debes <strong>responder ese correo</strong> — tu respuesta
          se registra automáticamente y se incorpora al análisis del informe del área.
        </p>
      </div>

      {/* Mis asignaciones */}
      <h2 className="font-semibold text-gray-700 mb-3">Mis asignaturas asignadas</h2>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      {cargando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : asignaciones.length === 0 ? (
        <div className="bg-white rounded-xl border p-10 text-center text-gray-400 text-sm">
          No tienes asignaturas asignadas todavía.
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Código</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Asignatura</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Grupo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Período</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {asignaciones.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-gray-600">{a.codigo}</td>
                  <td className="px-4 py-3 font-medium text-gray-800">{a.asignatura}</td>
                  <td className="px-4 py-3 font-mono text-gray-600">{a.grupo}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {a.periodo}
                    {a.periodo_activo && (
                      <span className="ml-2 bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs">activo</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
