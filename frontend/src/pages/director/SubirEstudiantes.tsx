import { useState, useEffect } from 'react'
import api from '../../services/api'
import { Upload, CheckCircle2, AlertTriangle } from 'lucide-react'
import type { ApiResponse } from '../../types'

interface Periodo { id: number; nombre: string; activo: boolean }

interface MateriaPreview { asignatura_id: number | null; asignatura_nombre: string }
interface EstudiantePreview {
  nombre_completo: string
  correo: string
  materias: MateriaPreview[]
}
interface Preview {
  periodo_id: number
  columnas_detectadas: Record<string, string | null>
  estudiantes: EstudiantePreview[]
  total_estudiantes: number
  total_materias: number
  advertencias: string[]
}

const CAMPO_LABEL: Record<string, string> = {
  nombre: 'Nombre',
  apellido: 'Apellido',
  correo: 'Correo institucional',
  materias: 'Materias que cursa',
}

export default function SubirEstudiantes() {
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [periodoId, setPeriodoId] = useState('')
  const [archivo, setArchivo] = useState<File | null>(null)
  const [preview, setPreview] = useState<Preview | null>(null)
  const [procesando, setProcesando] = useState(false)
  const [confirmando, setConfirmando] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<ApiResponse<Periodo[]>>('/periodos/').then((r) => {
      setPeriodos(r.data.data)
      const activo = r.data.data.find((p) => p.activo)
      if (activo) setPeriodoId(String(activo.id))
    })
  }, [])

  const enviar = async (endpoint: 'preview' | 'confirmar') => {
    if (!archivo || !periodoId) { setError('Selecciona el período y el archivo.'); return }
    const form = new FormData()
    form.append('archivo', archivo)
    form.append('periodo_id', periodoId)
    const setBusy = endpoint === 'preview' ? setProcesando : setConfirmando
    setBusy(true); setError(''); setMsg('')
    try {
      const { data } = await api.post<ApiResponse<Preview & { estudiantes_creados?: number }>>(
        `/estudiantes/${endpoint}`, form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      if (endpoint === 'preview') {
        setPreview(data.data)
      } else {
        setMsg(`${data.data.estudiantes_creados} estudiante(s) guardado(s) para el período.`)
        setPreview(null)
        setArchivo(null)
      }
    } catch (e: unknown) {
      const detalle = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detalle ?? 'No se pudo procesar el archivo.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Estudiantes del período</h1>
      <p className="text-sm text-gray-500 mb-4">
        Carga el Excel institucional para poder enviar correos personalizados por materia
      </p>

      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-5 text-sm text-blue-900">
        El sistema reconoce automáticamente las columnas de <strong>nombre</strong>,{' '}
        <strong>correo institucional</strong> y <strong>materias</strong>, sin importar su orden
        ni cómo se llamen. Si no logra identificarlas, consulta a la IA.
      </div>

      <div className="bg-white rounded-xl border p-5 mb-5 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Período académico</label>
          <select value={periodoId} onChange={(e) => setPeriodoId(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue w-72">
            <option value="">Seleccionar período</option>
            {periodos.map((p) => (
              <option key={p.id} value={p.id}>{p.nombre}{p.activo ? ' (activo)' : ''}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Archivo Excel</label>
          <input type="file" accept=".xlsx,.xls"
            onChange={(e) => { setArchivo(e.target.files?.[0] ?? null); setPreview(null) }}
            className="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg
                       file:border-0 file:text-sm file:font-medium file:bg-ups-blue file:text-white
                       hover:file:bg-blue-800" />
        </div>

        <button onClick={() => enviar('preview')} disabled={procesando || !archivo || !periodoId}
          className="flex items-center gap-2 bg-ups-blue text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-40">
          <Upload size={16} /> {procesando ? 'Procesando...' : 'Previsualizar'}
        </button>
      </div>

      {msg && (
        <p className="flex items-center gap-2 text-green-700 text-sm bg-green-50 px-3 py-2 rounded mb-4">
          <CheckCircle2 size={16} /> {msg}
        </p>
      )}
      {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded mb-4">{error}</p>}

      {preview && (
        <div className="space-y-5">
          {/* Qué columnas reconoció */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold text-gray-700 mb-3">Columnas reconocidas</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(preview.columnas_detectadas).map(([campo, col]) => (
                <div key={campo} className="border rounded-lg p-3">
                  <div className="text-xs text-gray-400">{CAMPO_LABEL[campo] ?? campo}</div>
                  <div className={`text-sm font-medium ${col ? 'text-gray-800' : 'text-gray-300'}`}>
                    {col ?? 'no encontrada'}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-6 mt-4 text-sm text-gray-600">
              <span><strong>{preview.total_estudiantes}</strong> estudiantes</span>
              <span><strong>{preview.total_materias}</strong> materias registradas</span>
            </div>
          </div>

          {preview.advertencias.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <p className="flex items-center gap-2 font-medium text-amber-800 text-sm mb-2">
                <AlertTriangle size={15} /> Detalles del procesamiento
              </p>
              <ul className="list-disc list-inside text-sm text-amber-900 space-y-0.5">
                {preview.advertencias.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </div>
          )}

          {/* Muestra de estudiantes */}
          <div className="bg-white rounded-xl border overflow-hidden">
            <div className="bg-gray-50 border-b px-4 py-2 text-sm font-medium text-gray-600">
              Primeros {Math.min(10, preview.estudiantes.length)} estudiantes
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Nombre</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Correo</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Materias</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {preview.estudiantes.slice(0, 10).map((e) => (
                  <tr key={e.correo} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium text-gray-800">{e.nombre_completo}</td>
                    <td className="px-4 py-2 text-gray-500">{e.correo}</td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {e.materias.map((m) => (
                          <span key={m.asignatura_nombre}
                            className={`text-xs px-2 py-0.5 rounded ${
                              m.asignatura_id ? 'bg-blue-50 text-blue-700' : 'bg-gray-100 text-gray-500'
                            }`}
                            title={m.asignatura_id ? 'Coincide con el catálogo' : 'No está en el catálogo'}>
                            {m.asignatura_nombre}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center gap-3">
            <button onClick={() => enviar('confirmar')} disabled={confirmando}
              className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60">
              {confirmando ? 'Guardando...' : 'Confirmar y guardar'}
            </button>
            <span className="text-xs text-gray-500">
              Reemplaza por completo el padrón de estudiantes de este período.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
