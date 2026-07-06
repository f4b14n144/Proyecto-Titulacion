import { useState, useEffect } from 'react'
import api from '../../services/api'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string }
interface Materia {
  asignatura_id: number
  asignatura: string
  codigo: string
  grupo: string
  contenido: string
}

export default function Observaciones() {
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [materias, setMaterias] = useState<Materia[]>([])
  const [borradores, setBorradores] = useState<Record<string, string>>({})
  const [cargando, setCargando] = useState(false)
  const [guardando, setGuardando] = useState<string | null>(null)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    Promise.all([
      api.get<ApiResponse<Consejo[]>>('/consejos/'),
      api.get<ApiResponse<Periodo[]>>('/periodos/'),
    ]).then(([c, p]) => { setConsejos(c.data.data); setPeriodos(p.data.data) })
  }, [])

  const seleccionar = async (cId: string) => {
    setConsejoId(cId); setMaterias([]); setBorradores({}); setMsg('')
    if (!cId) return
    setCargando(true)
    try {
      const { data } = await api.get<ApiResponse<Materia[]>>('/observaciones/mis-materias', { params: { consejo_id: cId } })
      setMaterias(data.data)
      const init: Record<string, string> = {}
      data.data.forEach((m) => { init[`${m.asignatura_id}-${m.grupo}`] = m.contenido })
      setBorradores(init)
    } finally {
      setCargando(false)
    }
  }

  const guardar = async (m: Materia) => {
    const key = `${m.asignatura_id}-${m.grupo}`
    setGuardando(key); setMsg('')
    try {
      await api.post('/observaciones/', {
        consejo_id: Number(consejoId),
        asignatura_id: m.asignatura_id,
        grupo: m.grupo,
        contenido: borradores[key] ?? '',
      })
      setMsg(`Observación de ${m.asignatura} (${m.grupo}) guardada.`)
    } catch {
      setMsg('No se pudo guardar la observación.')
    } finally {
      setGuardando(null)
    }
  }

  const nombreP = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Observaciones y Sugerencias</h1>
      <p className="text-sm text-gray-500 mb-5">
        Escribe tus observaciones sobre cada materia. Se incorporan al Informe Final del área.
      </p>

      <div className="mb-5">
        <label className="block text-sm font-medium text-gray-700 mb-1">Consejo de Carrera</label>
        <select value={consejoId} onChange={(e) => seleccionar(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none w-80">
          <option value="">Seleccionar consejo</option>
          {consejos.map((c) => (
            <option key={c.id} value={c.id}>{nombreP(c.periodo_id)} — {c.fecha_consejo}</option>
          ))}
        </select>
      </div>

      {msg && <div className="bg-green-50 text-green-700 px-4 py-3 rounded-lg mb-4 text-sm">{msg}</div>}

      {cargando ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : consejoId && materias.length === 0 ? (
        <div className="bg-white rounded-xl border p-8 text-center text-gray-400 text-sm">
          No tienes materias asignadas en el período de este consejo.
        </div>
      ) : (
        <div className="space-y-4">
          {materias.map((m) => {
            const key = `${m.asignatura_id}-${m.grupo}`
            return (
              <div key={key} className="bg-white rounded-xl border p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-mono text-xs text-gray-500">{m.codigo}</span>
                  <span className="font-semibold text-gray-800">{m.asignatura}</span>
                  <span className="text-gray-400 text-sm">— Grupo {m.grupo}</span>
                </div>
                <textarea
                  value={borradores[key] ?? ''}
                  onChange={(e) => setBorradores((prev) => ({ ...prev, [key]: e.target.value }))}
                  placeholder="Observaciones sobre el desarrollo de la materia, dificultades, sugerencias de mejora..."
                  rows={4}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-ups-blue focus:outline-none resize-none"
                />
                <div className="flex justify-end mt-2">
                  <button onClick={() => guardar(m)} disabled={guardando === key}
                    className="bg-ups-blue text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
                    {guardando === key ? 'Guardando...' : 'Guardar observación'}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
