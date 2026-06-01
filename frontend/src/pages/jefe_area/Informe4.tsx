import { useState, useEffect } from 'react'
import api from '../../services/api'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string; activo: boolean }
interface Informe { id: number; contenido_json: Record<string, unknown>; estado: string; ruta_docx: string | null }

const SUB_ANALISIS = [
  { campo: 'analisis_general', label: '1. Análisis general' },
  { campo: 'distribucion_aprobacion', label: '2. Distribución aprobación/reprobación' },
  { campo: 'comportamiento_notas_finales', label: '3. Comportamiento notas finales' },
  { campo: 'analisis_parcial1', label: '4. Análisis Parcial 1' },
  { campo: 'analisis_parcial2', label: '5. Análisis Parcial 2' },
  { campo: 'comparacion_parciales', label: '6. Comparación entre parciales' },
  { campo: 'uso_recuperacion', label: '7. Uso de recuperación' },
  { campo: 'relacion_parciales_nota_final', label: '8. Relación parciales-nota final' },
  { campo: 'outliers', label: '9. Identificación de outliers' },
  { campo: 'patrones_generales', label: '10. Patrones generales' },
  { campo: 'acciones_mejora', label: 'Acciones de mejora' },
]

export default function Informe4() {
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [informe, setInforme] = useState<Informe | null>(null)
  const [editando, setEditando] = useState<Record<number, Record<string, string>>>({})
  const [generando, setGenerando] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get<ApiResponse<Consejo[]>>('/consejos/'),
      api.get<ApiResponse<Periodo[]>>('/periodos/'),
    ]).then(([c, p]) => { setConsejos(c.data.data); setPeriodos(p.data.data) })
  }, [])

  const seleccionar = async (cId: string) => {
    setConsejoId(cId); setInforme(null); setEditando({}); setMsg('')
    if (!cId) return
    try {
      const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: cId } })
      const inf = data.data.find((i) => i.tipo_informe === 4) ?? null
      setInforme(inf)
      if (inf) {
        const cals = (inf.contenido_json?.calificaciones_finales as Record<string, string>[]) ?? []
        const init: Record<number, Record<string, string>> = {}
        cals.forEach((c, i) => {
          init[i] = SUB_ANALISIS.reduce((acc, s) => ({ ...acc, [s.campo]: String(c[s.campo] ?? '') }), {})
        })
        setEditando(init)
      }
    } catch { /* sin informe */ }
  }

  const generarBorrador = async () => {
    setGenerando(true); setMsg(''); setError('')
    try {
      await api.post('/informes/generar-borrador', { consejo_id: Number(consejoId), area_id: 0, tipo_informe: 4 })
      setMsg('Generando con IA… puede tardar 1-2 minutos. Recarga en unos momentos.')
    } catch { setError('Error al iniciar la generación.') } finally { setGenerando(false) }
  }

  const guardar = async () => {
    if (!informe) return
    setGuardando(true); setError('')
    try {
      const cals = (informe.contenido_json?.calificaciones_finales as Record<string, unknown>[]) ?? []
      const actualizadas = cals.map((c, i) => ({ ...c, ...editando[i] }))
      await api.put(`/informes/${informe.id}/secciones`, {
        secciones: { calificaciones_finales_editadas: JSON.stringify(actualizadas) }
      })
      setMsg('Cambios guardados.')
    } catch { setError('Error al guardar.') } finally { setGuardando(false) }
  }

  const generarDocx = async () => {
    if (!informe) return
    setGenerando(true)
    try {
      await api.post(`/informes/${informe.id}/generar-docx`)
      await seleccionar(consejoId)
      setMsg('.docx regenerado.')
    } catch { setError('Error.') } finally { setGenerando(false) }
  }

  const nombreP = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`
  const calificaciones = (informe?.contenido_json?.calificaciones_finales as Record<string, unknown>[]) ?? []

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Informe 4 — Análisis Final de Calificaciones</h1>
      <p className="text-sm text-gray-500 mb-5">Análisis completo con IA — 10 sub-análisis editables por asignatura</p>

      <div className="flex items-center gap-3 mb-6">
        <select value={consejoId} onChange={(e) => seleccionar(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
          <option value="">Seleccionar Consejo</option>
          {consejos.map((c) => (
            <option key={c.id} value={c.id}>{nombreP(c.periodo_id)} — {c.fecha_consejo}</option>
          ))}
        </select>
        {consejoId && !informe && (
          <button onClick={generarBorrador} disabled={generando}
            className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
            {generando ? 'Iniciando IA...' : 'Generar borrador con IA'}
          </button>
        )}
      </div>

      {msg && <p className="text-green-600 text-sm bg-green-50 px-3 py-2 rounded mb-4">{msg}</p>}
      {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded mb-4">{error}</p>}

      {informe && calificaciones.length === 0 && (
        <p className="text-gray-400 text-sm">No hay calificaciones finales cargadas para este consejo.</p>
      )}

      {calificaciones.map((cal, i) => (
        <div key={i} className="bg-white rounded-xl border mb-5 overflow-hidden">
          <div className="bg-gray-50 border-b px-4 py-3 flex items-center gap-3">
            <span className="font-semibold text-gray-800">{String(cal.asignatura)}</span>
            <span className="text-gray-500 text-sm">— Grupo {String(cal.grupo)} — {String(cal.docente)}</span>
            <span className="ml-auto text-xs text-gray-400">
              {String(cal.aprobados ?? '?')} aprobados / {String(cal.reprobados ?? '?')} reprobados
            </span>
          </div>

          {/* Estadísticos */}
          {cal.nota_final && (
            <div className="grid grid-cols-4 gap-2 text-xs text-center p-3 bg-gray-50 border-b">
              {[
                ['Promedio NF', (cal.nota_final as Record<string, unknown>)?.promedio],
                ['Máx NF', (cal.nota_final as Record<string, unknown>)?.max],
                ['Mín NF', (cal.nota_final as Record<string, unknown>)?.min],
                ['Aprobación', `${String(cal.pct_aprobacion ?? 0)}%`],
              ].map(([label, val]) => (
                <div key={String(label)} className="bg-white rounded border p-2">
                  <div className="text-gray-400">{String(label)}</div>
                  <div className="font-bold text-gray-800">{String(val ?? '—')}</div>
                </div>
              ))}
            </div>
          )}

          {/* Sub-análisis editables */}
          <div className="p-4 space-y-3">
            {SUB_ANALISIS.map(({ campo, label }) => (
              <div key={campo}>
                <label className="block text-xs font-semibold text-gray-600 mb-1">{label}</label>
                <textarea
                  value={editando[i]?.[campo] ?? String(cal[campo] ?? '')}
                  onChange={(e) => setEditando((prev) => ({
                    ...prev, [i]: { ...prev[i], [campo]: e.target.value }
                  }))}
                  rows={3}
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-ups-blue focus:outline-none resize-none"
                />
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Análisis consolidado área */}
      {informe?.contenido_json?.analisis_consolidado_area && (
        <div className="bg-white rounded-xl border p-5 mb-5">
          <h2 className="font-semibold text-gray-700 mb-3">Análisis Consolidado del Área</h2>
          <p className="text-sm text-gray-700 italic mb-3">
            {String(informe.contenido_json.analisis_consolidado_area)}
          </p>
          <h3 className="font-medium text-gray-600 mb-1 text-sm">Acciones Generales</h3>
          <p className="text-sm text-gray-700 italic">
            {String(informe.contenido_json.acciones_generales_area ?? '')}
          </p>
        </div>
      )}

      {informe && (
        <div className="flex gap-3 flex-wrap">
          <button onClick={guardar} disabled={guardando}
            className="bg-ups-blue text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
            {guardando ? 'Guardando...' : 'Guardar ediciones'}
          </button>
          <button onClick={generarDocx} disabled={generando}
            className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60">
            {generando ? 'Generando...' : 'Regenerar .docx'}
          </button>
          {informe.ruta_docx && (
            <a href={`/api/v1/informes/${informe.id}/descargar`}
              className="border border-ups-blue text-ups-blue px-5 py-2 rounded-lg text-sm font-medium hover:bg-ups-blue hover:text-white transition">
              Descargar .docx
            </a>
          )}
        </div>
      )}
    </div>
  )
}
