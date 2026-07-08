import { useState, useEffect } from 'react'
import api from '../../services/api'
import { descargarInforme } from '../../services/informes.service'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string; activo: boolean }
interface Informe { id: number; tipo_informe: number; contenido_json: Record<string, unknown>; estado: string; ruta_docx: string | null }

const SECCIONES: { campo: string; label: string; placeholder: string }[] = [
  { campo: 'agenda', label: '1. Agenda tratada en la reunión', placeholder: 'Describa los puntos tratados en la reunión del Centro Docente...' },
  { campo: 'designaciones', label: '2. Designaciones de Jefes de Área', placeholder: 'Liste los docentes designados como jefes de área para este período...' },
  { campo: 'observaciones_curriculares', label: '3. Observaciones curriculares de docentes', placeholder: 'Registre las observaciones sobre el currículo presentadas por los docentes...' },
  { campo: 'resultados_encuestas', label: '4. Resultados de encuestas estudiantiles', placeholder: 'Resuma los resultados de las encuestas de satisfacción estudiantil...' },
  { campo: 'resoluciones', label: '5. Resoluciones y compromisos', placeholder: 'Detalle las resoluciones adoptadas y compromisos asumidos...' },
  { campo: 'observaciones_adicionales', label: '6. Observaciones adicionales', placeholder: 'Cualquier otra observación relevante...' },
]

export default function Informe1() {
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [informe, setInforme] = useState<Informe | null>(null)
  const [secciones, setSecciones] = useState<Record<string, string>>({})
  const [nombreDirector, setNombreDirector] = useState('')
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
      // Auto-seleccionar el último consejo (el más reciente viene primero)
      if (c.data.data.length > 0) seleccionarConsejo(String(c.data.data[0].id))
    })
  }, [])

  const pintarInforme = (inf1: Informe) => {
    setInforme(inf1)
    const contenido = inf1.contenido_json as Record<string, unknown>
    const secsRaw = (contenido.secciones as Record<string, string>) ?? {}
    setSecciones(secsRaw)
    setNombreDirector((contenido.nombre_director as string) ?? '')
  }

  const cargarInforme = async (cId: string) => {
    if (!cId) return
    try {
      const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: cId } })
      let inf1 = data.data.find((i) => i.tipo_informe === 1) ?? null
      if (!inf1) {
        // No existe aún: lo generamos para que se auto-llenen jefes de área y director
        await api.post('/informes/generar-borrador', { consejo_id: Number(cId), area_id: 1, tipo_informe: 1 })
        await new Promise((r) => setTimeout(r, 1200))
        const res = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: cId } })
        inf1 = res.data.data.find((i) => i.tipo_informe === 1) ?? null
      }
      if (inf1) pintarInforme(inf1)
    } catch { /* sin permisos o error */ }
  }

  const seleccionarConsejo = (id: string) => {
    setConsejoId(id)
    setInforme(null)
    setSecciones({})
    setMsg('')
    cargarInforme(id)
  }

  const guardar = async () => {
    if (!consejoId) { setError('Selecciona un consejo.'); return }
    setGuardando(true); setError(''); setMsg('')
    try {
      if (informe) {
        await api.put(`/informes/${informe.id}/secciones`, { secciones })
        setMsg('Cambios guardados.')
      } else {
        // Crear borrador primero
        await api.post('/informes/generar-borrador', { consejo_id: Number(consejoId), area_id: 1, tipo_informe: 1 })
        await new Promise((r) => setTimeout(r, 1500))
        await cargarInforme(consejoId)
        setMsg('Informe 1 creado. Puedes seguir editando.')
      }
    } catch { setError('Error al guardar.') } finally { setGuardando(false) }
  }

  const generarDocx = async () => {
    if (!informe) return
    setGenerando(true); setMsg('')
    try {
      await api.put(`/informes/${informe.id}/secciones`, { secciones })
      await api.post(`/informes/${informe.id}/generar-docx`)
      await cargarInforme(consejoId)
      setMsg('Documento .docx generado correctamente.')
    } catch { setError('Error al generar .docx.') } finally { setGenerando(false) }
  }

  const nombrePeriodo = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Informe 1 — Centro Docente</h1>
      <p className="text-sm text-gray-500 mb-6">Formulario de la reunión del Centro Docente</p>

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

      {consejoId && (
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
            <label className="block text-sm font-semibold text-gray-700 mb-1">Nombre del/la Director/a de Carrera</label>
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
              {guardando ? 'Guardando...' : 'Guardar'}
            </button>
            {informe && (
              <>
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
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
