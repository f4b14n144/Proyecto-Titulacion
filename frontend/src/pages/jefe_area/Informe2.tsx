import { useState, useEffect } from 'react'
import api from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import { descargarInforme } from '../../services/informes.service'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string; activo: boolean }
interface Asignacion { id: number; usuario_id: number; asignatura_id: number; periodo_id: number; grupo: string }
interface Usuario { id: number; nombre_completo: string }
interface Asignatura { id: number; nombre: string; area_id: number }
interface Informe { id: number; tipo_informe: number; contenido_json: Record<string, unknown>; estado: string; ruta_docx: string | null }

const PARAMS_BOOL = [
  { campo: 'silabo_cargado', label: 'Sílabo cargado' },
  { campo: 'registro_avance', label: 'Registro de avance del sílabo' },
  { campo: 'guia_practicas', label: 'Guía de componente práctico' },
  { campo: 'consejeria_academica', label: 'Enlace consejería académica' },
  { campo: 'recursos_derechos_autor', label: 'Recursos con derechos de autor' },
  { campo: 'libros_digitales', label: 'Libros digitales biblioteca' },
  { campo: 'seccion_practicas', label: 'Sección PRÁCTICAS' },
  { campo: 'guias_componente', label: 'Guías de cada componente práctico' },
  { campo: 'actividades_con_rubrica', label: 'Actividades calificadas con rúbrica' },
  { campo: 'seccion_investigativas', label: 'Sección INVESTIGATIVAS' },
  { campo: 'actividad_investigacion', label: 'Actividad para fomentar investigación' },
  { campo: 'proyecto_integrador', label: 'Proyecto integrador de materias' },
]

type ChecklistRow = Record<string, boolean | string>

export default function Informe2() {
  const { user } = useAuth()
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [asignaturas, setAsignaturas] = useState<Asignatura[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [informe, setInforme] = useState<Informe | null>(null)
  const [checklists, setChecklists] = useState<Record<number, ChecklistRow>>({})
  const [guardando, setGuardando] = useState(false)
  const [generando, setGenerando] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

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
    setConsejoId(cId)
    setInforme(null); setChecklists({}); setMsg('')
    if (!cId) return
    const consejo = consejos.find((c) => c.id === Number(cId))
    if (!consejo) return
    const asigRes = await api.get<ApiResponse<Asignacion[]>>('/asignaciones/', { params: { periodo_id: consejo.periodo_id } })
    setAsignaciones(asigRes.data.data)
    // Inicializar checklists vacíos
    const init: Record<number, ChecklistRow> = {}
    asigRes.data.data.forEach((a) => {
      init[a.id] = PARAMS_BOOL.reduce((acc, p) => ({ ...acc, [p.campo]: false }), { observaciones: '', acciones_mejora: '' })
    })
    setChecklists(init)
    try {
      const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: cId } })
      const inf = data.data.find((i) => i.tipo_informe === 2) ?? null
      setInforme(inf)
    } catch { /* sin informe aún */ }
  }

  const toggle = (asigId: number, campo: string) => {
    setChecklists((prev) => ({ ...prev, [asigId]: { ...prev[asigId], [campo]: !prev[asigId][campo] } }))
  }

  const texto = (asigId: number, campo: string, valor: string) => {
    setChecklists((prev) => ({ ...prev, [asigId]: { ...prev[asigId], [campo]: valor } }))
  }

  const nombreUsuario = (id: number) => usuarios.find((u) => u.id === id)?.nombre_completo ?? `#${id}`
  const nombreAsignatura = (id: number) => asignaturas.find((a) => a.id === id)?.nombre ?? `#${id}`
  const nombrePeriodo = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`

  const guardarYGenerar = async () => {
    if (!consejoId) return
    setGuardando(true); setError(''); setMsg('')
    try {
      // Enviar checklists al backend como secciones del informe
      const consejo = consejos.find((c) => c.id === Number(consejoId))
      if (!consejo) return

      let informeActual = informe
      if (!informeActual) {
        await api.post('/informes/generar-borrador', { consejo_id: Number(consejoId), area_id: user?.area_id, tipo_informe: 2 })
        await new Promise((r) => setTimeout(r, 1500))
        const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: consejoId } })
        informeActual = data.data.find((i) => i.tipo_informe === 2) ?? null
        if (informeActual) setInforme(informeActual)
      }

      if (informeActual) {
        const secciones: Record<string, string> = {
          checklists_json: JSON.stringify(checklists),
        }
        await api.put(`/informes/${informeActual.id}/secciones`, { secciones })
        setMsg('Checklist guardado.')
      }
    } catch { setError('Error al guardar.') } finally { setGuardando(false) }
  }

  const generarDocx = async () => {
    if (!informe) return
    setGenerando(true)
    try {
      await api.post(`/informes/${informe.id}/generar-docx`)
      const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: consejoId } })
      setInforme(data.data.find((i) => i.tipo_informe === 2) ?? null)
      setMsg('.docx generado.')
    } catch { setError('Error al generar .docx.') } finally { setGenerando(false) }
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Informe 2 — Revisión AVAC</h1>
      <p className="text-sm text-gray-500 mb-5">Checklist de parámetros del aula virtual por docente</p>

      <div className="mb-5">
        <select value={consejoId} onChange={(e) => seleccionar(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
          <option value="">Seleccionar Consejo de Carrera</option>
          {consejos.map((c) => (
            <option key={c.id} value={c.id}>{nombrePeriodo(c.periodo_id)} — {c.fecha_consejo}</option>
          ))}
        </select>
      </div>

      {consejoId && asignaciones.length === 0 && (
        <p className="text-gray-400 text-sm">No hay asignaciones para este período.</p>
      )}

      {asignaciones.map((asig) => (
        <div key={asig.id} className="bg-white rounded-xl border mb-4 overflow-hidden">
          <div className="bg-gray-50 border-b px-4 py-3 flex items-center gap-3">
            <span className="font-semibold text-gray-800">{nombreAsignatura(asig.asignatura_id)}</span>
            <span className="text-gray-500 text-sm">— {nombreUsuario(asig.usuario_id)} — Grupo {asig.grupo}</span>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-4">
              {PARAMS_BOOL.map(({ campo, label }) => (
                <label key={campo} className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
                  <input type="checkbox" checked={!!checklists[asig.id]?.[campo]}
                    onChange={() => toggle(asig.id, campo)} className="w-4 h-4 accent-ups-blue" />
                  {label}
                </label>
              ))}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Observaciones</label>
                <textarea value={(checklists[asig.id]?.observaciones as string) ?? ''}
                  onChange={(e) => texto(asig.id, 'observaciones', e.target.value)}
                  rows={2} className="w-full border rounded px-2 py-1 text-sm focus:ring-1 focus:ring-ups-blue focus:outline-none resize-none" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Acciones de mejora</label>
                <textarea value={(checklists[asig.id]?.acciones_mejora as string) ?? ''}
                  onChange={(e) => texto(asig.id, 'acciones_mejora', e.target.value)}
                  rows={2} className="w-full border rounded px-2 py-1 text-sm focus:ring-1 focus:ring-ups-blue focus:outline-none resize-none" />
              </div>
            </div>
          </div>
        </div>
      ))}

      {consejoId && asignaciones.length > 0 && (
        <div className="flex gap-3 mt-4">
          {msg && <span className="text-green-600 text-sm self-center">{msg}</span>}
          {error && <span className="text-red-600 text-sm self-center">{error}</span>}
          <button onClick={guardarYGenerar} disabled={guardando}
            className="bg-ups-blue text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
            {guardando ? 'Guardando...' : 'Guardar checklist'}
          </button>
          {informe && (
            <button onClick={generarDocx} disabled={generando}
              className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60">
              {generando ? 'Generando...' : 'Generar .docx'}
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
