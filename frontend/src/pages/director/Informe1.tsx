import { useState, useEffect } from 'react'
import api from '../../services/api'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string; activo: boolean }
interface ContenidoDireccion {
  consejo_id: number
  secciones: Record<string, string>
  nombre_director: string
}

const SECCIONES: { campo: string; label: string; placeholder: string }[] = [
  { campo: 'agenda', label: '1. Agenda tratada en la reunión', placeholder: 'Describa los puntos tratados en la reunión del Centro Docente...' },
  { campo: 'designaciones', label: '2. Designaciones de Jefes de Área', placeholder: 'Se llena automáticamente con las jefaturas del período...' },
  { campo: 'observaciones_curriculares', label: '3. Observaciones curriculares de docentes', placeholder: 'Registre las observaciones sobre el currículo presentadas por los docentes...' },
  { campo: 'resultados_encuestas', label: '4. Resultados de encuestas estudiantiles', placeholder: 'Resuma los resultados de las encuestas de satisfacción estudiantil...' },
  { campo: 'resoluciones', label: '5. Resoluciones y compromisos', placeholder: 'Detalle las resoluciones adoptadas y compromisos asumidos...' },
  { campo: 'observaciones_adicionales', label: '6. Observaciones adicionales', placeholder: 'Cualquier otra observación relevante...' },
]

export default function Informe1() {
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [secciones, setSecciones] = useState<Record<string, string>>({})
  const [nombreDirector, setNombreDirector] = useState('')
  const [cargando, setCargando] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get<ApiResponse<Periodo[]>>('/periodos/'),
      api.get<ApiResponse<Consejo[]>>('/consejos/'),
    ]).then(([p, c]) => {
      setPeriodos(p.data.data)
      setConsejos(c.data.data)
      if (c.data.data.length > 0) seleccionarConsejo(String(c.data.data[0].id))
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const cargarContenido = async (cId: string) => {
    if (!cId) return
    setCargando(true); setError('')
    try {
      const { data } = await api.get<ApiResponse<ContenidoDireccion>>(
        `/consejos/${cId}/contenido-direccion`
      )
      setSecciones(data.data.secciones ?? {})
      setNombreDirector(data.data.nombre_director ?? '')
    } catch {
      setError('No se pudo cargar el contenido del consejo.')
    } finally {
      setCargando(false)
    }
  }

  const seleccionarConsejo = (id: string) => {
    setConsejoId(id)
    setSecciones({})
    setMsg('')
    cargarContenido(id)
  }

  const guardar = async () => {
    if (!consejoId) { setError('Selecciona un consejo.'); return }
    setGuardando(true); setError(''); setMsg('')
    try {
      await api.put(`/consejos/${consejoId}/contenido-direccion`, {
        secciones,
        nombre_director: nombreDirector,
      })
      setMsg('Guardado. Este contenido aparecerá en el Informe 1 de todas las áreas.')
    } catch {
      setError('Error al guardar.')
    } finally {
      setGuardando(false)
    }
  }

  const nombrePeriodo = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Informe 1 — Centro Docente</h1>
      <p className="text-sm text-gray-500 mb-4">
        Contenido de dirección para la reunión del Centro Docente
      </p>

      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-5 text-sm text-blue-900">
        Lo que escribas aquí se copia al <strong>Informe 1 de cada área</strong> en modo solo
        lectura. Cada jefe de área añade encima su propio aporte, sin poder modificar este texto.
      </div>

      <div className="mb-5">
        <label className="block text-sm font-medium text-gray-700 mb-1">Consejo de Carrera</label>
        <select
          value={consejoId}
          onChange={(e) => seleccionarConsejo(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue w-72"
        >
          <option value="">Seleccionar consejo</option>
          {consejos.map((c) => (
            <option key={c.id} value={c.id}>
              {nombrePeriodo(c.periodo_id)} — {c.fecha_consejo}
            </option>
          ))}
        </select>
      </div>

      {cargando && (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      )}

      {consejoId && !cargando && (
        <div className="space-y-5">
          {SECCIONES.map(({ campo, label, placeholder }) => (
            <div key={campo}>
              <label className="block text-sm font-semibold text-gray-700 mb-1">{label}</label>
              <textarea
                value={secciones[campo] ?? ''}
                onChange={(e) => setSecciones({ ...secciones, [campo]: e.target.value })}
                placeholder={placeholder}
                rows={4}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue resize-none"
              />
            </div>
          ))}

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              Nombre del/la Director/a de Carrera
            </label>
            <input
              type="text"
              value={nombreDirector}
              onChange={(e) => setNombreDirector(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
            />
          </div>

          {msg && <p className="text-green-600 text-sm bg-green-50 px-3 py-2 rounded">{msg}</p>}
          {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button onClick={guardar} disabled={guardando}
              className="bg-ups-blue text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
              {guardando ? 'Guardando...' : 'Guardar contenido de dirección'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
