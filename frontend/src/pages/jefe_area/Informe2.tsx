import { useState, useEffect } from 'react'
import { Sparkles } from 'lucide-react'
import api from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import { descargarInforme } from '../../services/informes.service'
import { Cargando, MensajeError } from '../../components/Estado'
import GenerarConIA from '../../components/GenerarConIA'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string; activo: boolean }
interface Asignacion { id: number; usuario_id: number; asignatura_id: number; periodo_id: number; grupo: string }
interface Usuario { id: number; nombre_completo: string }
interface Asignatura { id: number; nombre: string; area_id: number }
interface Informe {
  id: number
  tipo_informe: number
  contenido_json: Record<string, unknown>
  estado: string
  ruta_docx: string | null
}

/** Un ítem del checklist tal como viaja al backend. */
interface ItemChecklist {
  usuario_id: number
  asignatura_id: number
  grupo: string
  observaciones: string
  acciones_mejora: string
  [campo: string]: boolean | string | number
}

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

/** Clave estable de una asignación: la misma que usa el backend. */
const clave = (asignaturaId: number, grupo: string) => `${asignaturaId}|${grupo}`

const itemVacio = (a: Asignacion): ItemChecklist => ({
  usuario_id: a.usuario_id,
  asignatura_id: a.asignatura_id,
  grupo: a.grupo,
  observaciones: '',
  acciones_mejora: '',
  ...PARAMS_BOOL.reduce((acc, p) => ({ ...acc, [p.campo]: false }), {}),
})

export default function Informe2() {
  const { user } = useAuth()
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [asignaturas, setAsignaturas] = useState<Asignatura[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [informe, setInforme] = useState<Informe | null>(null)
  const [checklists, setChecklists] = useState<Record<string, ItemChecklist>>({})
  const [cargando, setCargando] = useState(false)
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

  useEffect(() => {
    if (consejos.length > 0 && !consejoId && user?.area_id) seleccionar(String(consejos[0].id))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consejos, user])

  const seleccionar = async (cId: string) => {
    setConsejoId(cId); setInforme(null); setChecklists({}); setMsg(''); setError('')
    if (!cId || !user?.area_id) return
    const consejo = consejos.find((c) => c.id === Number(cId))
    if (!consejo) return

    setCargando(true)
    try {
      // Asignaciones del área en el período del consejo
      const asigRes = await api.get<ApiResponse<Asignacion[]>>('/asignaciones/', {
        params: { periodo_id: consejo.periodo_id },
      })
      const asigs = asigRes.data.data
      setAsignaciones(asigs)

      // Partir de un checklist vacío…
      const estado: Record<string, ItemChecklist> = {}
      asigs.forEach((a) => { estado[clave(a.asignatura_id, a.grupo)] = itemVacio(a) })

      // …y rellenarlo con lo que ya se guardó antes (aquí estaba el bug: nunca se leía)
      const guardado = await api.get<ApiResponse<{ informe_id: number | null; items: ItemChecklist[] }>>(
        '/avac/checklist', { params: { consejo_id: cId, area_id: user.area_id } },
      )
      guardado.data.data.items.forEach((item) => {
        const k = clave(item.asignatura_id, item.grupo)
        if (estado[k]) estado[k] = { ...estado[k], ...item }
      })
      setChecklists(estado)

      const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: cId } })
      setInforme(data.data.find((i) => i.tipo_informe === 2) ?? null)
    } catch {
      setError('No se pudo cargar el checklist.')
    } finally {
      setCargando(false)
    }
  }

  const toggle = (k: string, campo: string) => {
    setChecklists((prev) => ({ ...prev, [k]: { ...prev[k], [campo]: !prev[k][campo] } }))
  }

  const texto = (k: string, campo: string, valor: string) => {
    setChecklists((prev) => ({ ...prev, [k]: { ...prev[k], [campo]: valor } }))
  }

  const guardar = async (): Promise<number | null> => {
    if (!consejoId || !user?.area_id) return null
    setGuardando(true); setError(''); setMsg('')
    try {
      const { data } = await api.put<ApiResponse<{ informe_id: number; guardados: number }>>(
        '/avac/checklist',
        { consejo_id: Number(consejoId), area_id: user.area_id, items: Object.values(checklists) },
      )
      setMsg(data.message)
      return data.data.informe_id
    } catch {
      setError('No se pudo guardar el checklist.')
      return null
    } finally {
      setGuardando(false)
    }
  }

  /** Guarda y pide a la IA las acciones de mejora sugeridas. */
  const generarConIA = async () => {
    const informeId = await guardar()
    if (!informeId || !user?.area_id) return

    setGenerando(true); setError(''); setMsg('Generando acciones con IA… puede tardar un minuto.')
    try {
      await api.post('/informes/generar-borrador', {
        consejo_id: Number(consejoId), area_id: user.area_id, tipo_informe: 2,
      })

      // El borrador se genera en segundo plano: esperar a que aparezcan las acciones
      for (let intento = 0; intento < 40; intento++) {
        await new Promise((r) => setTimeout(r, 3000))
        const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: consejoId } })
        const inf = data.data.find((i) => i.tipo_informe === 2) ?? null
        const items = (inf?.contenido_json?.checklists as Record<string, unknown>[]) ?? []
        if (items.length > 0 && items.some((it) => String(it.acciones_sugeridas ?? '').trim())) {
          setInforme(inf)
          setMsg('Acciones de mejora generadas por la IA.')
          return
        }
      }
      setError('La generación está tardando más de lo normal. Recarga en unos momentos.')
    } catch {
      setError('No se pudieron generar las acciones.')
    } finally {
      setGenerando(false)
    }
  }

  const generarDocx = async () => {
    if (!informe) return
    setGenerando(true); setError('')
    try {
      await api.post(`/informes/${informe.id}/generar-docx`)
      const { data } = await api.get<ApiResponse<Informe[]>>('/informes/', { params: { consejo_id: consejoId } })
      setInforme(data.data.find((i) => i.tipo_informe === 2) ?? null)
      setMsg('.docx generado.')
    } catch { setError('Error al generar el .docx.') } finally { setGenerando(false) }
  }

  const nombreUsuario = (id: number) => usuarios.find((u) => u.id === id)?.nombre_completo ?? `#${id}`
  const nombreAsignatura = (id: number) => asignaturas.find((a) => a.id === id)?.nombre ?? `#${id}`
  const nombrePeriodo = (pid: number) => periodos.find((p) => p.id === pid)?.nombre ?? `#${pid}`

  /** Acciones que sugirió la IA para una asignatura-grupo. */
  const accionesIA = (asignaturaId: number, grupo: string): string => {
    const items = (informe?.contenido_json?.checklists as Record<string, unknown>[]) ?? []
    const nombre = nombreAsignatura(asignaturaId)
    const it = items.find((x) => x.asignatura === nombre && x.grupo === grupo)
    return String(it?.acciones_sugeridas ?? '')
  }

  // Solo las asignaciones del área del jefe
  const misAsignaciones = asignaciones.filter((a) => {
    const asig = asignaturas.find((x) => x.id === a.asignatura_id)
    return asig?.area_id === user?.area_id
  })

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Informe 2 — Revisión AVAC</h1>
      <p className="text-sm text-gray-500 mb-4">
        Checklist de los 12 parámetros del aula virtual, por docente y asignatura
      </p>

      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-5 text-sm text-blue-900">
        Hay <strong>un solo Informe 2 por período y área</strong>. Lo que marques queda guardado:
        puedes salir y volver a entrar para seguir completándolo.
      </div>

      <div className="mb-5">
        <label className="block text-sm font-medium text-gray-700 mb-1">Consejo de Carrera</label>
        <select value={consejoId} onChange={(e) => seleccionar(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue w-80">
          <option value="">Seleccionar consejo</option>
          {consejos.map((c) => (
            <option key={c.id} value={c.id}>{nombrePeriodo(c.periodo_id)} — {c.fecha_consejo}</option>
          ))}
        </select>
      </div>

      {msg && <p className="text-green-700 text-sm bg-green-50 px-3 py-2 rounded mb-4">{msg}</p>}
      {error && <MensajeError mensaje={error} />}

      {cargando ? (
        <Cargando texto="Cargando checklist…" />
      ) : (
        <>
          {consejoId && misAsignaciones.length === 0 && (
            <p className="text-gray-400 text-sm">No hay asignaciones en tu área para este período.</p>
          )}

          {misAsignaciones.map((asig) => {
            const k = clave(asig.asignatura_id, asig.grupo)
            const item = checklists[k]
            if (!item) return null
            const sugeridas = accionesIA(asig.asignatura_id, asig.grupo)

            return (
              <div key={k} className="bg-white rounded-xl border mb-4 overflow-hidden">
                <div className="bg-gray-50 border-b px-4 py-3 flex items-center gap-3 flex-wrap">
                  <span className="font-semibold text-gray-800">{nombreAsignatura(asig.asignatura_id)}</span>
                  <span className="text-gray-500 text-sm">
                    — {nombreUsuario(asig.usuario_id)} — Grupo {asig.grupo}
                  </span>
                </div>

                <div className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-4">
                    {PARAMS_BOOL.map(({ campo, label }) => (
                      <label key={campo} className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
                        <input type="checkbox" checked={Boolean(item[campo])}
                          onChange={() => toggle(k, campo)} className="w-4 h-4 accent-ups-blue" />
                        {label}
                      </label>
                    ))}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Observaciones</label>
                      <textarea value={item.observaciones}
                        onChange={(e) => texto(k, 'observaciones', e.target.value)}
                        rows={2}
                        className="w-full border rounded px-2 py-1 text-sm focus:ring-1 focus:ring-ups-blue focus:outline-none resize-none" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Acciones de mejora del jefe de área
                      </label>
                      <textarea value={item.acciones_mejora}
                        onChange={(e) => texto(k, 'acciones_mejora', e.target.value)}
                        rows={2}
                        className="w-full border rounded px-2 py-1 text-sm focus:ring-1 focus:ring-ups-blue focus:outline-none resize-none" />
                    </div>
                  </div>

                  {sugeridas && (
                    <div className="mt-3 bg-violet-50 border border-violet-200 rounded-lg p-3">
                      <p className="flex items-center gap-1.5 text-xs font-semibold text-violet-800 mb-1">
                        <Sparkles size={13} /> Acciones de mejora sugeridas por la IA
                      </p>
                      <p className="text-sm text-violet-900 whitespace-pre-line">{sugeridas}</p>
                    </div>
                  )}
                </div>
              </div>
            )
          })}

          {consejoId && misAsignaciones.length > 0 && (
            <div className="sticky bottom-0 -mx-6 px-6 py-3 bg-white border-t flex gap-3 flex-wrap items-center">
              <button onClick={guardar} disabled={guardando || generando}
                className="bg-ups-blue text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-50">
                {guardando ? 'Guardando...' : 'Guardar checklist'}
              </button>
              <GenerarConIA
                existe={!!informe?.contenido_json?.checklists}
                generando={generando || guardando}
                onGenerar={generarConIA}
                nota="Tu checklist y tus observaciones se conservan: se guardan aparte y se vuelven a leer."
              />
              {informe && (
                <button onClick={generarDocx} disabled={guardando || generando}
                  className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50">
                  Generar .docx
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
        </>
      )}
    </div>
  )
}
