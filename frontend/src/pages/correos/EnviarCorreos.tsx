import { useState, useEffect } from 'react'
import api from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import { Mail, Eye, Send, AlertTriangle, X } from 'lucide-react'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string; activo: boolean }

interface CorreoPreview {
  destinatario: string
  asunto: string
  materia: string
  cuerpo_html: string
}
interface Resultado {
  modo_prueba: boolean
  total: number
  correos?: CorreoPreview[]
  materias_sin_docente?: string[]
}

type Flujo = 'estudiantes' | 'docentes' | 'visitas-aulicas'

const FLUJOS: { id: Flujo; titulo: string; descripcion: string; boton: string }[] = [
  {
    id: 'estudiantes',
    titulo: 'Consulta a estudiantes',
    descripcion:
      'Un correo por cada materia que cursa cada estudiante, con el nombre de la materia y su docente.',
    // Texto exacto solicitado
    boton: 'Enviar Correo de Consulta a Estudiantes',
  },
  {
    id: 'docentes',
    titulo: 'Observaciones y acciones de mejora a docentes',
    descripcion:
      'Un correo por cada materia que dicta cada docente, solicitando observaciones y propuestas de mejora.',
    boton: 'Enviar Correo a Docentes',
  },
  {
    id: 'visitas-aulicas',
    titulo: 'Visitas áulicas',
    descripcion: 'Coordina la visita áulica con cada docente, por materia.',
    boton: 'Enviar Correo de Visitas Áulicas',
  },
]

export default function EnviarCorreos() {
  const { user } = useAuth()
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [flujoActivo, setFlujoActivo] = useState<Flujo | null>(null)
  const [ocupado, setOcupado] = useState<string | null>(null)
  const [verCorreo, setVerCorreo] = useState<CorreoPreview | null>(null)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get<ApiResponse<Consejo[]>>('/consejos/'),
      api.get<ApiResponse<Periodo[]>>('/periodos/'),
    ]).then(([c, p]) => {
      setConsejos(c.data.data)
      setPeriodos(p.data.data)
      if (c.data.data.length > 0) setConsejoId(String(c.data.data[0].id))
    })
  }, [])

  const periodoDeConsejo = () =>
    consejos.find((c) => c.id === Number(consejoId))?.periodo_id ?? null

  const llamar = async (flujo: Flujo, modoPrueba: boolean) => {
    if (!consejoId) { setError('Selecciona un consejo de carrera.'); return }
    const periodoId = periodoDeConsejo()
    setOcupado(`${flujo}-${modoPrueba}`); setError(''); setMsg('')
    try {
      const cuerpo =
        flujo === 'estudiantes'
          ? { periodo_id: periodoId, modo_prueba: modoPrueba }
          : { consejo_id: Number(consejoId), area_id: user?.area_id ?? undefined, modo_prueba: modoPrueba }

      const { data } = await api.post<ApiResponse<Resultado>>(`/correos/${flujo}`, cuerpo)
      setFlujoActivo(flujo)
      setResultado(data.data)
      setMsg(data.message)
    } catch (e: unknown) {
      const detalle = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detalle ?? 'No se pudo procesar la solicitud.')
    } finally {
      setOcupado(null)
    }
  }

  const enviarDeVerdad = async (flujo: Flujo, total: number) => {
    if (!confirm(`Se enviarán ${total} correo(s) reales. ¿Continuar?`)) return
    await llamar(flujo, false)
  }

  const nombrePeriodo = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Correos institucionales</h1>
      <p className="text-sm text-gray-500 mb-4">
        Correos personalizados por materia, con el nombre del docente y del estudiante
      </p>

      <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-5 text-sm text-amber-900">
        <AlertTriangle size={15} className="inline mr-1 -mt-0.5" />
        Usa <strong>Previsualizar</strong> para revisar los correos sin enviarlos. El envío real
        solo ocurre al pulsar el botón de envío y confirmar.
      </div>

      <div className="mb-5">
        <label className="block text-sm font-medium text-gray-700 mb-1">Consejo de Carrera</label>
        <select value={consejoId} onChange={(e) => { setConsejoId(e.target.value); setResultado(null) }}
          className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue w-80">
          <option value="">Seleccionar consejo</option>
          {consejos.map((c) => (
            <option key={c.id} value={c.id}>{nombrePeriodo(c.periodo_id)} — {c.fecha_consejo}</option>
          ))}
        </select>
      </div>

      {msg && <p className="text-green-700 text-sm bg-green-50 px-3 py-2 rounded mb-4">{msg}</p>}
      {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded mb-4">{error}</p>}

      <div className="space-y-4">
        {FLUJOS.map((f) => (
          <div key={f.id} className="bg-white rounded-xl border p-5">
            <div className="flex items-start gap-3 mb-3">
              <span className="bg-ups-blue/10 text-ups-blue rounded-lg p-2">
                <Mail size={18} strokeWidth={1.9} />
              </span>
              <div>
                <h2 className="font-semibold text-gray-800">{f.titulo}</h2>
                <p className="text-sm text-gray-500">{f.descripcion}</p>
              </div>
            </div>
            <div className="flex gap-3 flex-wrap">
              <button onClick={() => llamar(f.id, true)} disabled={ocupado !== null || !consejoId}
                className="flex items-center gap-2 border border-ups-blue text-ups-blue px-4 py-2 rounded-lg text-sm font-medium hover:bg-ups-blue hover:text-white transition disabled:opacity-40">
                <Eye size={15} /> {ocupado === `${f.id}-true` ? 'Preparando...' : 'Previsualizar'}
              </button>
              <button
                onClick={() => enviarDeVerdad(f.id, resultado && flujoActivo === f.id ? resultado.total : 0)}
                disabled={ocupado !== null || !resultado || flujoActivo !== f.id}
                title={flujoActivo === f.id ? '' : 'Primero previsualiza este envío'}
                className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-40">
                <Send size={15} /> {ocupado === `${f.id}-false` ? 'Enviando...' : f.boton}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Previsualización */}
      {resultado?.modo_prueba && resultado.correos && (
        <div className="mt-6 bg-white rounded-xl border overflow-hidden">
          <div className="bg-gray-50 border-b px-4 py-3 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">
              {resultado.total} correo(s) preparados — no se envió ninguno
            </span>
            <button onClick={() => setResultado(null)} className="text-gray-400 hover:text-gray-600">
              <X size={16} />
            </button>
          </div>

          {resultado.materias_sin_docente && resultado.materias_sin_docente.length > 0 && (
            <p className="px-4 py-2 text-xs text-amber-800 bg-amber-50 border-b">
              Omitidas por no tener docente asignado: {resultado.materias_sin_docente.join(', ')}
            </p>
          )}

          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Destinatario</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Materia</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {resultado.correos.slice(0, 15).map((c, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-700">{c.destinatario}</td>
                  <td className="px-4 py-2 text-gray-500">{c.materia}</td>
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => setVerCorreo(c)} className="text-ups-blue hover:underline text-xs">
                      Ver correo
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {resultado.correos.length > 15 && (
            <p className="px-4 py-2 text-xs text-gray-400 border-t">
              …y {resultado.correos.length - 15} más.
            </p>
          )}
        </div>
      )}

      {/* Vista de un correo */}
      {verCorreo && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-6">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
            <div className="border-b px-5 py-3 flex items-start justify-between">
              <div>
                <p className="text-xs text-gray-400">Para: {verCorreo.destinatario}</p>
                <p className="font-semibold text-gray-800 text-sm">{verCorreo.asunto}</p>
              </div>
              <button onClick={() => setVerCorreo(null)} className="text-gray-400 hover:text-gray-600">
                <X size={18} />
              </button>
            </div>
            <div className="overflow-y-auto p-5"
              dangerouslySetInnerHTML={{ __html: verCorreo.cuerpo_html }} />
          </div>
        </div>
      )}
    </div>
  )
}
