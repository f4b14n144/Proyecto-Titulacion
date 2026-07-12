import { useState, useEffect } from 'react'
import api from '../services/api'
import { CalendarClock, BellRing, X } from 'lucide-react'
import type { ApiResponse } from '../types'

interface Fila {
  tipo_informe: number
  fecha_entrega: string
  fecha_recordatorio: string
}

interface Props {
  consejoId: number
  etiqueta: string
  onCerrar: () => void
}

const INFORMES = [
  { tipo: 1, nombre: 'Informe 1 — Centro Docente' },
  { tipo: 2, nombre: 'Informe 2 — Revisión AVAC' },
  { tipo: 3, nombre: 'Informe 3 — Visitas Áulicas e Interciclo' },
  { tipo: 4, nombre: 'Informe 4 — Análisis Final' },
]

/** Fecha del recordatorio: 2 días antes de la entrega. Se calcula al vuelo. */
const dosDiasAntes = (fecha: string): string => {
  if (!fecha) return ''
  const d = new Date(fecha + 'T00:00:00')
  d.setDate(d.getDate() - 2)
  return d.toISOString().slice(0, 10)
}

const hoy = () => new Date().toISOString().slice(0, 10)

/**
 * Fechas de entrega de los 4 informes de un consejo.
 *
 * El sistema envía un recordatorio automático 2 días antes de cada una, a los
 * jefes de área (que elaboran el informe) y a los docentes (que registran sus
 * observaciones y acciones de mejora).
 */
export default function FechasEntrega({ consejoId, etiqueta, onCerrar }: Props) {
  const [fechas, setFechas] = useState<Record<number, string>>({})
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<ApiResponse<Fila[]>>(`/consejos/${consejoId}/fechas-entrega`)
      .then(({ data }) => {
        const actual: Record<number, string> = {}
        data.data.forEach((f) => { actual[f.tipo_informe] = f.fecha_entrega })
        setFechas(actual)
      })
      .catch(() => setError('No se pudieron cargar las fechas.'))
      .finally(() => setCargando(false))
  }, [consejoId])

  const guardar = async () => {
    const aGuardar = INFORMES
      .filter((i) => fechas[i.tipo])
      .map((i) => ({ tipo_informe: i.tipo, fecha_entrega: fechas[i.tipo] }))

    if (aGuardar.length === 0) { setError('Fija al menos una fecha.'); return }

    setGuardando(true); setError(''); setMsg('')
    try {
      const { data } = await api.put<ApiResponse<{ recordatorios_programados: number }>>(
        `/consejos/${consejoId}/fechas-entrega`, { fechas: aGuardar },
      )
      setMsg(data.message)
    } catch {
      setError('No se pudieron guardar las fechas.')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-6">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl">
        <div className="border-b px-5 py-3 flex items-start justify-between">
          <div>
            <h2 className="font-bold text-gray-800 flex items-center gap-2">
              <CalendarClock size={18} /> Fechas de entrega de los informes
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">{etiqueta}</p>
          </div>
          <button onClick={onCerrar} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="p-5">
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-4 text-sm text-blue-900">
            <BellRing size={15} className="inline mr-1 -mt-0.5" />
            Dos días antes de cada fecha, el sistema envía un <strong>recordatorio automático</strong>
            {' '}a los jefes de área y a los docentes.
          </div>

          {cargando ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-7 w-7 border-b-2 border-ups-blue" />
            </div>
          ) : (
            <div className="space-y-3">
              {INFORMES.map(({ tipo, nombre }) => {
                const valor = fechas[tipo] ?? ''
                const aviso = dosDiasAntes(valor)
                const pasado = Boolean(aviso) && aviso < hoy()
                return (
                  <div key={tipo} className="flex items-center gap-3 flex-wrap border rounded-lg px-3 py-2.5">
                    <span className="text-sm font-medium text-gray-700 flex-1 min-w-[15rem]">
                      {nombre}
                    </span>
                    <input
                      type="date"
                      value={valor}
                      onChange={(e) => setFechas({ ...fechas, [tipo]: e.target.value })}
                      className="border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                    />
                    <span className={`text-xs w-52 ${pasado ? 'text-amber-600' : 'text-gray-500'}`}>
                      {aviso
                        ? pasado
                          ? `Aviso: ${aviso} (ya pasó, no se enviará)`
                          : `Recordatorio: ${aviso}`
                        : 'Sin fecha'}
                    </span>
                  </div>
                )
              })}
            </div>
          )}

          {msg && <p className="text-green-700 text-sm bg-green-50 px-3 py-2 rounded mt-4">{msg}</p>}
          {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded mt-4">{error}</p>}
        </div>

        <div className="border-t px-5 py-3 flex justify-end gap-2">
          <button onClick={onCerrar} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
            Cerrar
          </button>
          <button onClick={guardar} disabled={guardando || cargando}
            className="bg-ups-blue text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
            {guardando ? 'Guardando...' : 'Guardar y programar recordatorios'}
          </button>
        </div>
      </div>
    </div>
  )
}
