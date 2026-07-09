import { useState, useEffect } from 'react'
import api from '../../services/api'
import type { ApiResponse } from '../../types'
import { Trash2 } from 'lucide-react'

export type TipoAporte = 'OBSERVACION' | 'ACCION_MEJORA'

interface Aporte {
  id: number
  tipo: TipoAporte
  texto: string
  creado_en: string | null
}

interface Materia {
  asignatura_id: number
  asignatura: string
  codigo: string
  grupo: string
  observaciones: Aporte[]
  acciones_mejora: Aporte[]
}

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string }

interface Props {
  tipo: TipoAporte
  titulo: string
  subtitulo: string
  etiquetaCampo: string
  placeholder: string
}

const formatFechaHora = (iso: string | null) => {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('es-EC', { day: '2-digit', month: 'short', year: 'numeric' })
}

/**
 * Registro de aportes del docente por materia. Es sumativo: cada envío se
 * agrega al historial de esa materia y no reemplaza los anteriores.
 */
export default function AportesPorMateria({ tipo, titulo, subtitulo, etiquetaCampo, placeholder }: Props) {
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [materias, setMaterias] = useState<Materia[]>([])
  const [borradores, setBorradores] = useState<Record<string, string>>({})
  const [cargando, setCargando] = useState(false)
  const [enviando, setEnviando] = useState<string | null>(null)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get<ApiResponse<Consejo[]>>('/consejos/'),
      api.get<ApiResponse<Periodo[]>>('/periodos/'),
    ]).then(([c, p]) => {
      setConsejos(c.data.data)
      setPeriodos(p.data.data)
      if (c.data.data.length > 0) seleccionar(String(c.data.data[0].id))
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const cargar = async (cId: string) => {
    if (!cId) return
    setCargando(true); setError('')
    try {
      const { data } = await api.get<ApiResponse<Materia[]>>('/aportes/mis-materias', {
        params: { consejo_id: cId },
      })
      setMaterias(data.data)
    } catch {
      setError('No se pudieron cargar tus materias.')
    } finally {
      setCargando(false)
    }
  }

  const seleccionar = (id: string) => {
    setConsejoId(id); setMaterias([]); setBorradores({}); setMsg('')
    cargar(id)
  }

  const clave = (m: Materia) => `${m.asignatura_id}-${m.grupo}`

  const enviar = async (m: Materia) => {
    const k = clave(m)
    const texto = (borradores[k] ?? '').trim()
    if (!texto) return
    setEnviando(k); setError(''); setMsg('')
    try {
      await api.post('/aportes/', {
        consejo_id: Number(consejoId),
        asignatura_id: m.asignatura_id,
        grupo: m.grupo,
        tipo,
        texto,
      })
      setBorradores({ ...borradores, [k]: '' })
      await cargar(consejoId)
      setMsg('Registrado. Se agregó al historial de la materia.')
    } catch {
      setError('No se pudo registrar el aporte.')
    } finally {
      setEnviando(null)
    }
  }

  const eliminar = async (aporteId: number) => {
    if (!confirm('¿Eliminar este registro?')) return
    try {
      await api.delete(`/aportes/${aporteId}`)
      await cargar(consejoId)
    } catch {
      setError('No se pudo eliminar.')
    }
  }

  const nombrePeriodo = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`
  const listaDe = (m: Materia) => (tipo === 'OBSERVACION' ? m.observaciones : m.acciones_mejora)

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">{titulo}</h1>
      <p className="text-sm text-gray-500 mb-4">{subtitulo}</p>

      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-5 text-sm text-blue-900">
        Cada registro se <strong>acumula</strong> en el historial de la materia: puedes añadir
        varios a lo largo del período y todos llegan al informe del área.
      </div>

      <div className="mb-5">
        <label className="block text-sm font-medium text-gray-700 mb-1">Consejo de Carrera</label>
        <select value={consejoId} onChange={(e) => seleccionar(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue w-72">
          <option value="">Seleccionar consejo</option>
          {consejos.map((c) => (
            <option key={c.id} value={c.id}>{nombrePeriodo(c.periodo_id)} — {c.fecha_consejo}</option>
          ))}
        </select>
      </div>

      {msg && <p className="text-green-600 text-sm bg-green-50 px-3 py-2 rounded mb-4">{msg}</p>}
      {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded mb-4">{error}</p>}

      {cargando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : materias.length === 0 ? (
        <div className="bg-white rounded-xl border p-10 text-center text-gray-400 text-sm">
          No tienes materias asignadas en el período de este consejo.
        </div>
      ) : (
        <div className="space-y-5">
          {materias.map((m) => {
            const k = clave(m)
            const historial = listaDe(m)
            return (
              <div key={k} className="bg-white rounded-xl border overflow-hidden">
                <div className="bg-gray-50 border-b px-4 py-3 flex items-center gap-3">
                  <span className="font-semibold text-gray-800">{m.asignatura}</span>
                  <span className="bg-ups-blue text-white text-xs font-bold px-2 py-0.5 rounded">
                    Grupo {m.grupo}
                  </span>
                  <span className="ml-auto text-xs text-gray-400">
                    {historial.length} registro(s)
                  </span>
                </div>

                {historial.length > 0 && (
                  <ul className="divide-y border-b">
                    {historial.map((a) => (
                      <li key={a.id} className="px-4 py-3 flex items-start gap-3">
                        <div className="flex-1">
                          <p className="text-sm text-gray-700 whitespace-pre-line">{a.texto}</p>
                          <p className="text-xs text-gray-400 mt-1">{formatFechaHora(a.creado_en)}</p>
                        </div>
                        <button onClick={() => eliminar(a.id)} title="Eliminar"
                          className="text-gray-300 hover:text-red-500 transition">
                          <Trash2 size={15} />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                <div className="p-4">
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {etiquetaCampo}
                  </label>
                  <textarea
                    value={borradores[k] ?? ''}
                    onChange={(e) => setBorradores({ ...borradores, [k]: e.target.value })}
                    rows={3}
                    placeholder={placeholder}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue resize-none"
                  />
                  <button
                    onClick={() => enviar(m)}
                    disabled={enviando === k || !(borradores[k] ?? '').trim()}
                    className="mt-2 bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-40"
                  >
                    {enviando === k ? 'Registrando...' : 'Añadir al historial'}
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
