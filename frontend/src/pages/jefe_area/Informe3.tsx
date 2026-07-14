import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Mail } from 'lucide-react'
import api from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import { descargarInforme } from '../../services/informes.service'
import GraficoInforme from '../../components/GraficoInforme'
import GenerarConIA from '../../components/GenerarConIA'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string; activo: boolean }
interface Asignacion { id: number; usuario_id: number; asignatura_id: number; periodo_id: number; grupo: string }
interface Usuario { id: number; nombre_completo: string }
interface Asignatura { id: number; nombre: string; area_id: number }
interface Informe { id: number; tipo_informe: number; contenido_json: Record<string, unknown>; estado: string; ruta_docx: string | null }

const PARAMS_VISITA = [
  { campo: 'visita_realizada', label: 'Visita realizada' },
  { campo: 'puntualidad_docente', label: 'Puntualidad del docente' },
  { campo: 'cumplimiento_silabo', label: 'Cumplimiento del sílabo' },
  { campo: 'cumplimiento_practicas', label: 'Cumplimiento de prácticas' },
  { campo: 'actividades_con_rubrica', label: 'Actividades con rúbrica' },
  { campo: 'actividad_investigacion', label: 'Actividad de investigación' },
]

/** Una visita áulica, tal como viaja al backend. */
interface VisitaRow {
  usuario_id: number
  asignatura_id: number
  grupo: string
  observaciones_estudiantes: string
  observaciones_docente: string
  acciones_docente: string
  [campo: string]: boolean | string | number
}

/** Clave estable de una asignación: la misma que usa el backend. */
const clave = (asignaturaId: number, grupo: string) => `${asignaturaId}|${grupo}`

export default function Informe3() {
  const { user } = useAuth()
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [asignaturas, setAsignaturas] = useState<Asignatura[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [informe, setInforme] = useState<Informe | null>(null)
  const [visitas, setVisitas] = useState<Record<string, VisitaRow>>({})
  const [guardando, setGuardando] = useState(false)
  const [generando, setGenerando] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  // Los botones "Notificar a estudiantes" y "Enviar reporte de mejoras" se
  // quitaron: fabricaban direcciones de correo inexistentes
  // (estudiantes.{codigo}.{grupo}@est.ups.edu.ec) y decían "enviado" aunque no
  // llegara a nadie. Los correos a estudiantes se envían desde "Enviar correos",
  // que usa los destinatarios reales del Excel del período.

  useEffect(() => {
    Promise.all([
      api.get<ApiResponse<Consejo[]>>('/consejos/'),
      api.get<ApiResponse<Periodo[]>>('/periodos/'),
      api.get<ApiResponse<Usuario[]>>('/usuarios/'),
      api.get<ApiResponse<Asignatura[]>>('/asignaturas/'),
    ]).then(([c, p, u, a]) => {
      setConsejos(c.data.data); setPeriodos(p.data.data)
      setUsuarios(u.data.data); setAsignaturas(a.data.data)
    })
  }, [])

  // Auto-seleccionar el último consejo (el más reciente viene primero)
  useEffect(() => {
    if (consejos.length > 0 && !consejoId) seleccionar(String(consejos[0].id))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consejos])

  const seleccionar = async (cId: string) => {
    setConsejoId(cId); setInforme(null); setVisitas({}); setMsg(''); setError('')
    if (!cId || !user?.area_id) return
    const consejo = consejos.find((c) => c.id === Number(cId))
    if (!consejo) return

    try {
      const asigRes = await api.get<ApiResponse<Asignacion[]>>('/asignaciones/', {
        params: { periodo_id: consejo.periodo_id },
      })
      const asigs = asigRes.data.data
      setAsignaciones(asigs)

      // Partir de un checklist vacío…
      const estado: Record<string, VisitaRow> = {}
      asigs.forEach((a) => {
        estado[clave(a.asignatura_id, a.grupo)] = {
          usuario_id: a.usuario_id,
          asignatura_id: a.asignatura_id,
          grupo: a.grupo,
          observaciones_estudiantes: '', observaciones_docente: '', acciones_docente: '',
          ...PARAMS_VISITA.reduce((acc, p) => ({ ...acc, [p.campo]: false }), {}),
        }
      })

      // …y rellenarlo con lo ya guardado (aquí estaba el bug: nunca se leía)
      const guardado = await api.get<ApiResponse<{ items: VisitaRow[] }>>('/avac/visitas', {
        params: { consejo_id: cId, area_id: user.area_id },
      })
      guardado.data.data.items.forEach((item) => {
        const k = clave(item.asignatura_id, item.grupo)
        if (estado[k]) estado[k] = { ...estado[k], ...item }
      })
      setVisitas(estado)

      const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: cId } })
      setInforme(data.data.find((i) => i.tipo_informe === 3) ?? null)
    } catch {
      setError('No se pudo cargar el checklist de visitas.')
    }
  }

  const toggle = (k: string, campo: string) =>
    setVisitas((prev) => ({ ...prev, [k]: { ...prev[k], [campo]: !prev[k][campo] } }))

  const texto = (k: string, campo: string, val: string) =>
    setVisitas((prev) => ({ ...prev, [k]: { ...prev[k], [campo]: val } }))

  const nombreU = (id: number) => usuarios.find((u) => u.id === id)?.nombre_completo ?? `#${id}`
  const nombreA = (id: number) => asignaturas.find((a) => a.id === id)?.nombre ?? `#${id}`
  const nombreP = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`

  // Solo las asignaciones del área del jefe (antes se listaban las de todas las áreas)
  const misAsignaciones = asignaciones.filter((a) => {
    const asig = asignaturas.find((x) => x.id === a.asignatura_id)
    return asig?.area_id === user?.area_id
  })

  const releerInforme = async (): Promise<Informe | null> => {
    const res = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: consejoId } })
    const inf = res.data.data.find((i) => i.tipo_informe === 3) ?? null
    setInforme(inf)
    return inf
  }

  const guardar = async () => {
    if (!consejoId || !user?.area_id) return
    setGuardando(true); setError(''); setMsg('')
    try {
      const { data } = await api.put<ApiResponse<{ informe_id: number; guardados: number }>>(
        '/avac/visitas',
        { consejo_id: Number(consejoId), area_id: user.area_id, items: Object.values(visitas) },
      )
      setMsg(data.message)
      if (!informe) await releerInforme()
    } catch {
      setError('No se pudieron guardar las visitas.')
    } finally { setGuardando(false) }
  }

  /**
   * Guarda las visitas y pide a la IA la PARTE B: análisis del interciclo y los
   * gráficos de distribución por rango.
   *
   * Antes esta pantalla NO llamaba a la IA en ningún momento — solo regeneraba el
   * .docx, que se limita a renderizar la plantilla. En un consejo nuevo la PARTE B
   * salía vacía y sin gráficos.
   */
  const generarBorrador = async () => {
    if (!consejoId || !user?.area_id) return
    await guardar()

    const antes = JSON.stringify(informe?.contenido_json ?? null)
    setGenerando(true); setError(''); setMsg('Generando el análisis del interciclo con IA…')
    try {
      await api.post('/informes/generar-borrador', {
        consejo_id: Number(consejoId), area_id: user.area_id, tipo_informe: 3,
      })

      // Corre en segundo plano: hay que esperar a que el contenido cambie, o la
      // pantalla se quedaría mostrando el informe anterior.
      for (let i = 0; i < 40; i++) {          // 40 × 5s ≈ 3 minutos
        await new Promise((r) => setTimeout(r, 5000))
        const inf = await releerInforme()
        if (inf && JSON.stringify(inf.contenido_json) !== antes) {
          setMsg('Análisis e gráficos generados por la IA.')
          return
        }
      }
      setError('La IA está tardando más de lo normal. Vuelve a entrar en unos minutos.')
    } catch {
      setError('No se pudo generar el análisis.')
    } finally {
      setGenerando(false)
    }
  }

  const generarDocx = async () => {
    if (!informe) return
    setGenerando(true)
    try {
      await api.post(`/informes/${informe.id}/generar-docx`)
      const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: consejoId } })
      setInforme(data.data.find((i) => i.tipo_informe === 3) ?? null)
      setMsg('.docx generado.')
    } catch { setError('Error.') } finally { setGenerando(false) }
  }

  const analisis = informe?.contenido_json?.calificaciones_interciclo as unknown[] | undefined

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Informe 3 — Visitas Áulicas + Interciclo</h1>
      <p className="text-sm text-gray-500 mb-5">Parte A: checklist de visita | Parte B: análisis calificaciones interciclo</p>

      <div className="mb-5 flex items-center gap-3 flex-wrap">
        <select value={consejoId} onChange={(e) => seleccionar(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
          <option value="">Seleccionar Consejo</option>
          {consejos.map((c) => (
            <option key={c.id} value={c.id}>{nombreP(c.periodo_id)} — {c.fecha_consejo}</option>
          ))}
        </select>
        {consejoId && (
          <Link to="/jefe/correos"
            className="flex items-center gap-2 border border-ups-blue text-ups-blue px-4 py-2 rounded-lg text-sm font-medium hover:bg-ups-blue hover:text-white transition">
            <Mail size={15} /> Enviar correos a estudiantes
          </Link>
        )}
      </div>

      {/* PARTE A */}
      {misAsignaciones.length > 0 && (
        <div className="mb-8">
          <h2 className="font-semibold text-gray-700 mb-3">Parte A — Checklist de Visita Áulica</h2>
          {misAsignaciones.map((asig) => {
            const k = clave(asig.asignatura_id, asig.grupo)
            return (
            <div key={k} className="bg-white rounded-xl border mb-3 overflow-hidden">
              <div className="bg-gray-50 border-b px-4 py-2 text-sm font-medium text-gray-700">
                {nombreA(asig.asignatura_id)} — {nombreU(asig.usuario_id)} — Grupo {asig.grupo}
              </div>
              <div className="p-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-3">
                  {PARAMS_VISITA.map(({ campo, label }) => (
                    <label key={campo} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                      <input type="checkbox" checked={!!visitas[k]?.[campo]}
                        onChange={() => toggle(k, campo)} className="w-4 h-4 accent-ups-blue" />
                      {label}
                    </label>
                  ))}
                </div>
                {[
                  { campo: 'observaciones_estudiantes', label: 'Observaciones de estudiantes' },
                  { campo: 'observaciones_docente', label: 'Observaciones del docente' },
                  { campo: 'acciones_docente', label: 'Acciones de mejora del jefe de área al docente' },
                ].map(({ campo, label }) => (
                  <div key={campo} className="mb-2">
                    <label className="block text-xs text-gray-500 mb-0.5">{label}</label>
                    <textarea value={(visitas[k]?.[campo] as string) ?? ''}
                      onChange={(e) => texto(k, campo, e.target.value)}
                      rows={2} className="w-full border rounded px-2 py-1 text-sm focus:ring-1 focus:ring-ups-blue focus:outline-none resize-none" />
                  </div>
                ))}
              </div>
            </div>
            )
          })}
        </div>
      )}

      {/* PARTE B — Análisis IA */}
      {analisis && analisis.length > 0 && (
        <div className="mb-6">
          <h2 className="font-semibold text-gray-700 mb-3">Parte B — Análisis Calificaciones Interciclo</h2>
          {(analisis as Record<string, unknown>[]).map((c, i) => (
            <div key={i} className="bg-white rounded-xl border mb-3 p-4">
              <p className="font-medium text-gray-800 mb-2">{String(c.asignatura)} — Grupo {String(c.grupo)}</p>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs text-center mb-3">
                {[
                  ['Estudiantes', c.total_estudiantes],
                  ['Máx /50', c.maximo],
                  ['Mín /50', c.minimo],
                  ['Promedio', c.promedio],
                  ['Alto ≥40', c.rango_alto],
                  ['Bajo <30', c.rango_bajo],
                ].map(([label, val]) => (
                  <div key={String(label)} className="bg-gray-50 rounded p-2">
                    <div className="text-gray-500">{String(label)}</div>
                    <div className="font-bold text-gray-800">{String(val ?? '—')}</div>
                  </div>
                ))}
              </div>
              {/* Distribución por rango de desempeño */}
              {informe && Boolean(c.grafico_ruta) && (
                <div className="mb-3">
                  <GraficoInforme
                    informeId={informe.id}
                    nombre={String(c.grafico_ruta)}
                    alt={`Distribución por rango — ${String(c.asignatura)} grupo ${String(c.grupo)}`}
                  />
                </div>
              )}
              <p className="text-sm text-gray-600">{String(c.analisis_narrativo ?? '')}</p>
            </div>
          ))}
        </div>
      )}

      {consejoId && (
        <div className="flex gap-3">
          {msg && <span className="text-green-600 text-sm self-center">{msg}</span>}
          {error && <span className="text-red-600 text-sm self-center">{error}</span>}
          <button onClick={guardar} disabled={guardando}
            className="bg-ups-blue text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
            {guardando ? 'Guardando...' : 'Guardar visitas'}
          </button>
          <GenerarConIA
            existe={!!analisis?.length}
            generando={generando || guardando}
            onGenerar={generarBorrador}
            nota="Tus visitas áulicas y tus observaciones se conservan: se guardan aparte y se vuelven a leer."
          />
          {informe && (
            <button onClick={generarDocx} disabled={generando}
              className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60">
              {generando ? 'Generando...' : 'Regenerar .docx'}
            </button>
          )}
          {informe?.ruta_docx && (
            <button type="button" onClick={() => descargarInforme(informe.id)}
              className="border border-ups-blue text-ups-blue px-5 py-2 rounded-lg text-sm font-medium hover:bg-ups-blue hover:text-white transition">
              Descargar .docx
            </button>
          )}
        </div>
      )}
    </div>
  )
}
