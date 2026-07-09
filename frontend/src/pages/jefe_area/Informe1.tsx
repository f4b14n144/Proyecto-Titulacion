import { useState, useEffect } from 'react'
import api from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import { descargarInforme } from '../../services/informes.service'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string; activo: boolean }
interface Informe {
  id: number
  tipo_informe: number
  area_id: number
  contenido_json: Record<string, unknown>
  estado: string
  ruta_docx: string | null
}

const SECCIONES: { campo: string; label: string }[] = [
  { campo: 'agenda', label: '1. Agenda tratada en la reunión' },
  { campo: 'designaciones', label: '2. Designaciones de Jefes de Área' },
  { campo: 'observaciones_curriculares', label: '3. Observaciones curriculares de docentes' },
  { campo: 'resultados_encuestas', label: '4. Resultados de encuestas estudiantiles' },
  { campo: 'resoluciones', label: '5. Resoluciones y compromisos' },
  { campo: 'observaciones_adicionales', label: '6. Observaciones adicionales' },
]

export default function Informe1Jefe() {
  const { user } = useAuth()
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [informe, setInforme] = useState<Informe | null>(null)
  const [secciones, setSecciones] = useState<Record<string, string>>({})
  const [seccionesDireccion, setSeccionesDireccion] = useState<Record<string, string>>({})
  const [cargando, setCargando] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [generando, setGenerando] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get<ApiResponse<Periodo[]>>('/periodos/'),
      api.get<ApiResponse<Consejo[]>>('/consejos/'),
    ]).then(([p, c]) => {
      setPeriodos(p.data.data)
      setConsejos(c.data.data)
      if (c.data.data.length > 0) seleccionar(String(c.data.data[0].id))
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const pintar = (inf: Informe) => {
    setInforme(inf)
    const c = inf.contenido_json ?? {}
    setSecciones((c.secciones as Record<string, string>) ?? {})
    setSeccionesDireccion((c.secciones_direccion as Record<string, string>) ?? {})
  }

  const cargar = async (cId: string) => {
    if (!cId || !user?.area_id) return
    setCargando(true); setError('')
    try {
      let { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: cId } })
      let inf = data.data.find((i) => i.tipo_informe === 1) ?? null
      if (!inf) {
        // Aún no existe el Informe 1 de mi área: lo creamos (hereda lo de dirección)
        await api.post('/informes/generar-borrador', {
          consejo_id: Number(cId), area_id: user.area_id, tipo_informe: 1,
        })
        await new Promise((r) => setTimeout(r, 1200))
        ;({ data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: cId } }))
        inf = data.data.find((i) => i.tipo_informe === 1) ?? null
      }
      if (inf) pintar(inf)
    } catch {
      setError('No se pudo cargar el Informe 1 de tu área.')
    } finally {
      setCargando(false)
    }
  }

  const seleccionar = (id: string) => {
    setConsejoId(id); setInforme(null); setSecciones({}); setSeccionesDireccion({}); setMsg('')
    cargar(id)
  }

  const guardar = async () => {
    if (!informe) return
    setGuardando(true); setError(''); setMsg('')
    try {
      await api.put(`/informes/${informe.id}/secciones`, { secciones })
      setMsg('Tu aporte fue guardado.')
    } catch { setError('Error al guardar.') } finally { setGuardando(false) }
  }

  const generarDocx = async () => {
    if (!informe) return
    setGenerando(true); setError(''); setMsg('')
    try {
      await api.put(`/informes/${informe.id}/secciones`, { secciones })
      await api.post(`/informes/${informe.id}/generar-docx`)
      await cargar(consejoId)
      setMsg('Documento .docx generado.')
    } catch { setError('Error al generar el .docx.') } finally { setGenerando(false) }
  }

  const nombrePeriodo = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`

  if (user && !user.area_id) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Informe 1 — Centro Docente</h1>
        <p className="text-gray-500 text-sm">No tienes un área asignada como jefe.</p>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Informe 1 — Centro Docente</h1>
      <p className="text-sm text-gray-500 mb-4">
        Área: <span className="font-medium text-gray-700">{user?.area_nombre}</span>
      </p>

      <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-5 text-sm text-amber-900">
        El texto en gris lo escribió la <strong>Dirección de Carrera</strong> y es igual para todas
        las áreas: no puedes modificarlo. Debajo de cada sección añade el aporte de tu área.
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

      {cargando && (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      )}

      {informe && !cargando && (
        <div className="space-y-6">
          {SECCIONES.map(({ campo, label }) => (
            <div key={campo} className="bg-white border rounded-xl overflow-hidden">
              <div className="bg-gray-50 border-b px-4 py-2">
                <span className="text-sm font-semibold text-gray-700">{label}</span>
              </div>

              <div className="px-4 py-3 border-b bg-gray-50/50">
                <p className="text-xs font-medium text-gray-400 mb-1 uppercase tracking-wide">
                  Dirección de Carrera (solo lectura)
                </p>
                <p className="text-sm text-gray-600 whitespace-pre-line">
                  {seccionesDireccion[campo]?.trim() || '—'}
                </p>
              </div>

              <div className="px-4 py-3">
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Aporte de tu área
                </label>
                <textarea
                  value={secciones[campo] ?? ''}
                  onChange={(e) => setSecciones({ ...secciones, [campo]: e.target.value })}
                  rows={3}
                  placeholder="Escribe aquí lo que corresponde a tu área (opcional)"
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue resize-none"
                />
              </div>
            </div>
          ))}

          {msg && <p className="text-green-600 text-sm bg-green-50 px-3 py-2 rounded">{msg}</p>}
          {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded">{error}</p>}

          <div className="flex gap-3 flex-wrap">
            <button onClick={guardar} disabled={guardando}
              className="bg-ups-blue text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
              {guardando ? 'Guardando...' : 'Guardar aporte'}
            </button>
            <button onClick={generarDocx} disabled={generando}
              className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60">
              {generando ? 'Generando...' : 'Generar .docx'}
            </button>
            {informe.ruta_docx && (
              <button type="button" onClick={() => descargarInforme(informe.id)}
                className="border border-ups-blue text-ups-blue px-5 py-2 rounded-lg text-sm font-medium hover:bg-ups-blue hover:text-white transition">
                Descargar .docx
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
