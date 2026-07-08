import { useState, useEffect, useRef } from 'react'
import api from '../../services/api'
import type { ApiResponse } from '../../types'

interface Consejo { id: number; periodo_id: number; fecha_consejo: string; flujo_estado: string }
interface Periodo { id: number; nombre: string; activo: boolean }

interface EstudiantePreview {
  parcial1: number | null
  parcial2: number | null
  recuperacion: number | null
  nota_final: number | null
  estado: string
  solo_nota_final?: boolean
}

interface ResultadoPreview {
  asignatura_id: number
  grupo: string
  estudiantes: EstudiantePreview[]
  total_estudiantes: number
  columnas_detectadas: string[]
  advertencias: string[]
}

interface Preview {
  tipo: string
  consejo_id: number
  resultados: ResultadoPreview[]
  total_asignaturas: number
  advertencias_globales: string[]
}

type Paso = 'formulario' | 'preview' | 'confirmado'

export default function SubirCalificaciones() {
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [consejoId, setConsejoId] = useState('')
  const [tipo, setTipo] = useState<'INTERCICLO' | 'FINAL'>('INTERCICLO')
  const [archivo, setArchivo] = useState<File | null>(null)
  const [paso, setPaso] = useState<Paso>('formulario')
  const [preview, setPreview] = useState<Preview | null>(null)
  const [cargandoPrev, setCargandoPrev] = useState(false)
  const [cargandoConf, setCargandoConf] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    Promise.all([
      api.get<ApiResponse<Periodo[]>>('/periodos/'),
      api.get<ApiResponse<Consejo[]>>('/consejos/'),
    ]).then(([pRes, cRes]) => {
      setPeriodos(pRes.data.data)
      setConsejos(cRes.data.data)
      // Auto-seleccionar el último consejo (el más reciente viene primero)
      if (cRes.data.data.length > 0) setConsejoId(String(cRes.data.data[0].id))
    }).catch(() => setError('Error al cargar datos iniciales.'))
  }, [])

  const nombrePeriodo = (id: number) => periodos.find((p) => p.id === id)?.nombre ?? `#${id}`

  const generarPreview = async () => {
    if (!archivo || !consejoId || !tipo) {
      setError('Selecciona el consejo, tipo y archivo antes de continuar.')
      return
    }
    setError('')
    setCargandoPrev(true)
    const form = new FormData()
    form.append('archivo', archivo)
    form.append('tipo', tipo)
    form.append('consejo_id', consejoId)
    try {
      const { data } = await api.post<ApiResponse<Preview>>('/calificaciones/preview', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setPreview(data.data)
      setPaso('preview')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Error al procesar el archivo.')
    } finally {
      setCargandoPrev(false)
    }
  }

  const confirmar = async () => {
    if (!archivo) return
    setCargandoConf(true)
    setError('')
    const form = new FormData()
    form.append('archivo', archivo)
    form.append('tipo', tipo)
    form.append('consejo_id', consejoId)
    try {
      await api.post('/calificaciones/confirmar', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setPaso('confirmado')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Error al guardar las calificaciones.')
    } finally {
      setCargandoConf(false)
    }
  }

  const reiniciar = () => {
    setPaso('formulario')
    setPreview(null)
    setArchivo(null)
    setError('')
    if (inputRef.current) inputRef.current.value = ''
  }

  const estadoColor = (e: string) => {
    if (e === 'APROBADO' || e === 'ALTO') return 'text-green-600'
    if (e === 'REPROBADO' || e === 'BAJO') return 'text-red-600'
    if (e === 'MEDIO') return 'text-yellow-600'
    return 'text-gray-500'
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Subir Calificaciones</h1>
      <p className="text-sm text-gray-500 mb-6">Procesa el Excel del sistema UPS y carga las calificaciones al sistema</p>

      {/* Pasos */}
      <div className="flex items-center gap-2 mb-6 text-sm">
        {(['formulario', 'preview', 'confirmado'] as Paso[]).map((p, i) => (
          <div key={p} className="flex items-center gap-2">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
              ${paso === p ? 'bg-ups-blue text-white' : paso > p || (i === 2 && paso === 'confirmado') ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'}`}>
              {i + 1}
            </div>
            <span className={paso === p ? 'font-medium text-gray-800' : 'text-gray-400'}>
              {p === 'formulario' ? 'Configurar' : p === 'preview' ? 'Revisar preview' : 'Confirmado'}
            </span>
            {i < 2 && <span className="text-gray-300">→</span>}
          </div>
        ))}
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      {/* PASO 1: Formulario */}
      {paso === 'formulario' && (
        <div className="bg-white rounded-xl border p-6 max-w-lg">
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Consejo de Carrera</label>
              <select
                value={consejoId}
                onChange={(e) => setConsejoId(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
              >
                <option value="">Seleccionar consejo</option>
                {consejos.map((c) => (
                  <option key={c.id} value={c.id}>
                    {nombrePeriodo(c.periodo_id)} — {c.fecha_consejo}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de calificaciones</label>
              <div className="flex gap-3">
                {(['INTERCICLO', 'FINAL'] as const).map((t) => (
                  <label key={t} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      value={t}
                      checked={tipo === t}
                      onChange={() => setTipo(t)}
                      className="accent-ups-blue"
                    />
                    <span className="text-sm">{t === 'INTERCICLO' ? 'Interciclo (Parcial 1)' : 'Final (P1 + P2 + Rec + NF)'}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Archivo Excel (.xlsx / .xls)</label>
              <input
                ref={inputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
                className="w-full text-sm text-gray-600 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-ups-blue file:text-white file:text-sm file:cursor-pointer hover:file:bg-blue-800"
              />
              {archivo && (
                <p className="text-xs text-gray-500 mt-1">
                  {archivo.name} — {(archivo.size / 1024).toFixed(1)} KB
                </p>
              )}
            </div>

            <button
              onClick={generarPreview}
              disabled={cargandoPrev || !archivo || !consejoId}
              className="bg-ups-blue text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition disabled:opacity-60"
            >
              {cargandoPrev ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin border-2 border-white border-t-transparent rounded-full w-4 h-4" />
                  Procesando Excel...
                </span>
              ) : 'Generar preview'}
            </button>
          </div>
        </div>
      )}

      {/* PASO 2: Preview */}
      {paso === 'preview' && preview && (
        <div>
          {/* Resumen */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4 mb-5 flex flex-wrap gap-6 text-sm">
            <div><span className="text-gray-500">Tipo:</span> <strong>{preview.tipo}</strong></div>
            <div><span className="text-gray-500">Asignaturas detectadas:</span> <strong>{preview.total_asignaturas}</strong></div>
            <div>
              <span className="text-gray-500">Total estudiantes:</span>{' '}
              <strong>{preview.resultados.reduce((s, r) => s + r.total_estudiantes, 0)}</strong>
            </div>
          </div>

          {/* Advertencias globales */}
          {preview.advertencias_globales.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl px-5 py-3 mb-5">
              <p className="text-sm font-medium text-yellow-800 mb-1">Advertencias</p>
              <ul className="list-disc list-inside text-sm text-yellow-700 space-y-0.5">
                {preview.advertencias_globales.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </div>
          )}

          {/* Resultados por asignatura */}
          <div className="space-y-4 mb-6">
            {preview.resultados.map((r) => (
              <div key={`${r.asignatura_id}-${r.grupo}`} className="bg-white rounded-xl border overflow-hidden">
                <div className="bg-gray-50 border-b px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="bg-ups-blue text-white text-xs font-bold px-2 py-0.5 rounded">
                      Asig. #{r.asignatura_id}
                    </span>
                    <span className="font-medium text-gray-700">Grupo: {r.grupo}</span>
                    <span className="text-gray-400 text-xs">{r.total_estudiantes} estudiantes</span>
                  </div>
                  <span className="text-xs text-gray-400">Cols: {r.columnas_detectadas.join(', ')}</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        {preview.tipo === 'INTERCICLO' ? (
                          <>
                            <th className="text-left px-3 py-2 text-gray-500">#</th>
                            <th className="text-right px-3 py-2 text-gray-500">Parcial 1 /50</th>
                            <th className="text-left px-3 py-2 text-gray-500">Rango</th>
                          </>
                        ) : (
                          <>
                            <th className="text-left px-3 py-2 text-gray-500">#</th>
                            <th className="text-right px-3 py-2 text-gray-500">P1</th>
                            <th className="text-right px-3 py-2 text-gray-500">P2</th>
                            <th className="text-right px-3 py-2 text-gray-500">Rec</th>
                            <th className="text-right px-3 py-2 text-gray-500">NF</th>
                            <th className="text-left px-3 py-2 text-gray-500">Estado</th>
                          </>
                        )}
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {r.estudiantes.slice(0, 8).map((e, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          {preview.tipo === 'INTERCICLO' ? (
                            <>
                              <td className="px-3 py-1.5 text-gray-400">{i + 1}</td>
                              <td className="px-3 py-1.5 text-right font-mono">{e.parcial1 ?? '—'}</td>
                              <td className={`px-3 py-1.5 font-medium ${estadoColor(e.estado)}`}>{e.estado}</td>
                            </>
                          ) : (
                            <>
                              <td className="px-3 py-1.5 text-gray-400">{i + 1}</td>
                              <td className="px-3 py-1.5 text-right font-mono">{e.parcial1 ?? '—'}</td>
                              <td className="px-3 py-1.5 text-right font-mono">{e.parcial2 ?? '—'}</td>
                              <td className="px-3 py-1.5 text-right font-mono">{e.recuperacion ?? '—'}</td>
                              <td className="px-3 py-1.5 text-right font-mono">{e.nota_final ?? '—'}</td>
                              <td className={`px-3 py-1.5 font-medium ${estadoColor(e.estado)}`}>{e.estado}</td>
                            </>
                          )}
                        </tr>
                      ))}
                      {r.estudiantes.length > 8 && (
                        <tr>
                          <td colSpan={preview.tipo === 'INTERCICLO' ? 3 : 6} className="px-3 py-2 text-center text-gray-400">
                            … y {r.estudiantes.length - 8} más
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>

          {/* Acciones */}
          <div className="flex gap-3">
            <button onClick={reiniciar} className="px-5 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg border">
              ← Volver
            </button>
            <button
              onClick={confirmar}
              disabled={cargandoConf}
              className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60"
            >
              {cargandoConf ? 'Guardando...' : `Confirmar y guardar ${preview.total_asignaturas} asignatura(s)`}
            </button>
          </div>
        </div>
      )}

      {/* PASO 3: Confirmado */}
      {paso === 'confirmado' && (
        <div className="bg-white rounded-xl border p-10 text-center max-w-md">
          <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-green-600 text-2xl">✓</span>
          </div>
          <h2 className="text-lg font-bold text-gray-800 mb-2">¡Calificaciones guardadas!</h2>
          <p className="text-sm text-gray-500 mb-5">
            Los datos han sido procesados y almacenados correctamente en el sistema.
          </p>
          <button onClick={reiniciar} className="bg-ups-blue text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800">
            Subir otro archivo
          </button>
        </div>
      )}
    </div>
  )
}
