import { useState, useEffect } from 'react'
import api from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import { descargarInforme } from '../../services/informes.service'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string; activo: boolean }
interface Asignacion { id: number; usuario_id: number; asignatura_id: number; periodo_id: number; grupo: string }
interface Usuario { id: number; nombre_completo: string }
interface Asignatura { id: number; nombre: string }
interface Informe { id: number; tipo_informe: number; contenido_json: Record<string, unknown>; estado: string; ruta_docx: string | null }

const PARAMS_VISITA = [
  { campo: 'visita_realizada', label: 'Visita realizada' },
  { campo: 'puntualidad_docente', label: 'Puntualidad del docente' },
  { campo: 'cumplimiento_silabo', label: 'Cumplimiento del sílabo' },
  { campo: 'cumplimiento_practicas', label: 'Cumplimiento de prácticas' },
  { campo: 'actividades_con_rubrica', label: 'Actividades con rúbrica' },
  { campo: 'actividad_investigacion', label: 'Actividad de investigación' },
]

type VisitaRow = Record<string, boolean | string>

export default function Informe3() {
  const { user } = useAuth()
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [asignaturas, setAsignaturas] = useState<Asignatura[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [informe, setInforme] = useState<Informe | null>(null)
  const [visitas, setVisitas] = useState<Record<number, VisitaRow>>({})
  const [guardando, setGuardando] = useState(false)
  const [generando, setGenerando] = useState(false)
  const [notificando, setNotificando] = useState(false)
  const [msgNotif, setMsgNotif] = useState('')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const notificarEstudiantes = async () => {
    if (!consejoId) return
    setNotificando(true); setMsgNotif('')
    try {
      const { data } = await api.post('/flujo/notificar-estudiantes', { consejo_id: Number(consejoId) })
      setMsgNotif(data.message ?? 'Estudiantes notificados.')
    } catch (e: unknown) {
      const m = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setMsgNotif(m ?? 'No se pudo notificar a los estudiantes.')
    } finally {
      setNotificando(false)
    }
  }

  const enviarReporteMejoras = async () => {
    if (!consejoId) return
    setNotificando(true); setMsgNotif('')
    try {
      const { data } = await api.post('/flujo/reporte-mejoras-estudiantes', { consejo_id: Number(consejoId) })
      setMsgNotif(data.message ?? 'Reporte de mejoras enviado.')
    } catch (e: unknown) {
      const m = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setMsgNotif(m ?? 'No se pudo enviar el reporte de mejoras.')
    } finally {
      setNotificando(false)
    }
  }

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
    setConsejoId(cId); setInforme(null); setVisitas({}); setMsg('')
    if (!cId) return
    const consejo = consejos.find((c) => c.id === Number(cId))
    if (!consejo) return
    const asigRes = await api.get<ApiResponse<Asignacion[]>>('/asignaciones/', { params: { periodo_id: consejo.periodo_id } })
    setAsignaciones(asigRes.data.data)
    const init: Record<number, VisitaRow> = {}
    asigRes.data.data.forEach((a) => {
      init[a.id] = PARAMS_VISITA.reduce((acc, p) => ({ ...acc, [p.campo]: false }), {
        observaciones_estudiantes: '', observaciones_docente: '', acciones_docente: '',
      })
    })
    setVisitas(init)
    try {
      const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: cId } })
      setInforme(data.data.find((i) => i.tipo_informe === 3) ?? null)
    } catch { /* sin informe */ }
  }

  const toggle = (id: number, campo: string) =>
    setVisitas((prev) => ({ ...prev, [id]: { ...prev[id], [campo]: !prev[id][campo] } }))

  const texto = (id: number, campo: string, val: string) =>
    setVisitas((prev) => ({ ...prev, [id]: { ...prev[id], [campo]: val } }))

  const nombreU = (id: number) => usuarios.find((u) => u.id === id)?.nombre_completo ?? `#${id}`
  const nombreA = (id: number) => asignaturas.find((a) => a.id === id)?.nombre ?? `#${id}`
  const nombreP = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`

  const guardar = async () => {
    setGuardando(true); setError(''); setMsg('')
    try {
      let inf = informe
      if (!inf) {
        await api.post('/informes/generar-borrador', { consejo_id: Number(consejoId), area_id: user?.area_id, tipo_informe: 3 })
        await new Promise((r) => setTimeout(r, 1500))
        const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: consejoId } })
        inf = data.data.find((i) => i.tipo_informe === 3) ?? null
        if (inf) setInforme(inf)
      }
      if (inf) {
        await api.put(`/informes/${inf.id}/secciones`, { secciones: { visitas_json: JSON.stringify(visitas) } })
        setMsg('Visitas guardadas.')
      }
    } catch { setError('Error al guardar.') } finally { setGuardando(false) }
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
          <>
            <button onClick={notificarEstudiantes} disabled={notificando}
              className="bg-ups-red text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 transition disabled:opacity-60">
              {notificando ? 'Enviando...' : '✉ Notificar a estudiantes'}
            </button>
            <button onClick={enviarReporteMejoras} disabled={notificando}
              className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition disabled:opacity-60">
              {notificando ? 'Enviando...' : '📄 Enviar reporte de mejoras'}
            </button>
          </>
        )}
      </div>

      {msgNotif && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg mb-4 text-sm">
          {msgNotif}
          <p className="text-xs text-blue-600 mt-1">
            Se invita a los estudiantes de las materias del área a acercarse al Jefe de Área
            si tienen quejas u observaciones.
          </p>
        </div>
      )}

      {/* PARTE A */}
      {asignaciones.length > 0 && (
        <div className="mb-8">
          <h2 className="font-semibold text-gray-700 mb-3">Parte A — Checklist de Visita Áulica</h2>
          {asignaciones.map((asig) => (
            <div key={asig.id} className="bg-white rounded-xl border mb-3 overflow-hidden">
              <div className="bg-gray-50 border-b px-4 py-2 text-sm font-medium text-gray-700">
                {nombreA(asig.asignatura_id)} — {nombreU(asig.usuario_id)} — Grupo {asig.grupo}
              </div>
              <div className="p-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-3">
                  {PARAMS_VISITA.map(({ campo, label }) => (
                    <label key={campo} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                      <input type="checkbox" checked={!!visitas[asig.id]?.[campo]}
                        onChange={() => toggle(asig.id, campo)} className="w-4 h-4 accent-ups-blue" />
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
                    <textarea value={(visitas[asig.id]?.[campo] as string) ?? ''}
                      onChange={(e) => texto(asig.id, campo, e.target.value)}
                      rows={2} className="w-full border rounded px-2 py-1 text-sm focus:ring-1 focus:ring-ups-blue focus:outline-none resize-none" />
                  </div>
                ))}
              </div>
            </div>
          ))}
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
              <p className="text-sm text-gray-600 italic">{String(c.analisis_narrativo ?? '')}</p>
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
          {informe && (
            <button onClick={generarDocx} disabled={generando}
              className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60">
              {generando ? 'Generando IA + .docx...' : 'Generar Informe 3'}
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
