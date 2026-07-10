import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../../services/api'
import EditorContenido from '../../components/EditorContenido'
import { descargarInforme } from '../../services/informes.service'
import { ArrowLeft } from 'lucide-react'
import type { ApiResponse } from '../../types'

interface Informe {
  id: number
  tipo_informe: number
  area_id: number
  estado: string
  version: number
  ruta_docx: string | null
  contenido_json: Record<string, unknown> | null
  area_nombre?: string | null
}

const TIPO_LABEL: Record<number, string> = {
  1: 'Informe 1 — Centro Docente',
  2: 'Informe 2 — Revisión AVAC',
  3: 'Informe 3 — Visitas Áulicas e Interciclo',
  4: 'Informe 4 — Análisis Final de Calificaciones',
}

/**
 * Editor completo de un informe: TODO el contenido es editable, incluidos los
 * nombres de los docentes, el área, el período y el texto de la carátula.
 */
export default function EditarInforme() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [informe, setInforme] = useState<Informe | null>(null)
  const [contenido, setContenido] = useState<Record<string, unknown>>({})
  const [sucio, setSucio] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [generando, setGenerando] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const cargar = async () => {
    setCargando(true); setError('')
    try {
      const { data } = await api.get<ApiResponse<Informe>>(`/informes/${id}`)
      setInforme(data.data)
      setContenido((data.data.contenido_json ?? {}) as Record<string, unknown>)
      setSucio(false)
    } catch {
      setError('No se pudo cargar el informe.')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => { cargar() }, [id])

  const guardar = async () => {
    setGuardando(true); setError(''); setMsg('')
    try {
      await api.put(`/informes/${id}/contenido`, { contenido_json: contenido })
      setSucio(false)
      setMsg('Cambios guardados.')
    } catch (e: unknown) {
      const detalle = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detalle ?? 'No se pudieron guardar los cambios.')
    } finally {
      setGuardando(false)
    }
  }

  const guardarYRegenerar = async () => {
    setGenerando(true); setError(''); setMsg('')
    try {
      await api.put(`/informes/${id}/contenido`, { contenido_json: contenido })
      await api.post(`/informes/${id}/generar-docx`)
      await cargar()
      setMsg('Documento .docx regenerado con los cambios.')
    } catch (e: unknown) {
      const detalle = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detalle ?? 'No se pudo regenerar el documento.')
    } finally {
      setGenerando(false)
    }
  }

  if (cargando) {
    return (
      <div className="flex justify-center py-16">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
      </div>
    )
  }

  if (!informe) {
    return <div className="p-6 text-sm text-red-600">{error || 'Informe no encontrado.'}</div>
  }

  return (
    <div className="p-6 max-w-4xl">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-ups-blue mb-3">
        <ArrowLeft size={15} /> Volver
      </button>

      <h1 className="text-2xl font-bold text-gray-800 mb-1">
        {TIPO_LABEL[informe.tipo_informe] ?? `Informe ${informe.tipo_informe}`}
      </h1>
      <p className="text-sm text-gray-500 mb-4">
        {informe.area_nombre ?? `Área ${informe.area_id}`} · v{informe.version} · {informe.estado}
      </p>

      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-5 text-sm text-blue-900">
        Puedes editar <strong>cualquier campo</strong> del informe, incluidos los nombres de los
        docentes, el área, el período y el texto de la carátula. Al regenerar el .docx se crea una
        versión nueva con los cambios.
      </div>

      {msg && <p className="text-green-600 text-sm bg-green-50 px-3 py-2 rounded mb-4">{msg}</p>}
      {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded mb-4">{error}</p>}

      <EditorContenido
        valor={contenido as never}
        onChange={(nuevo) => { setContenido(nuevo as Record<string, unknown>); setSucio(true) }}
      />

      {/* Barra de acciones fija para no perderla al bajar por un informe largo */}
      <div className="sticky bottom-0 mt-6 -mx-6 px-6 py-3 bg-white border-t flex gap-3 flex-wrap items-center">
        <button onClick={guardar} disabled={guardando || !sucio}
          className="bg-ups-blue text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-40">
          {guardando ? 'Guardando...' : 'Guardar cambios'}
        </button>
        <button onClick={guardarYRegenerar} disabled={generando}
          className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60">
          {generando ? 'Regenerando...' : 'Guardar y regenerar .docx'}
        </button>
        {informe.ruta_docx && (
          <button type="button" onClick={() => descargarInforme(informe.id)}
            className="border border-ups-blue text-ups-blue px-5 py-2 rounded-lg text-sm font-medium hover:bg-ups-blue hover:text-white transition">
            Descargar .docx
          </button>
        )}
        {sucio && <span className="text-xs text-amber-600">Tienes cambios sin guardar</span>}
      </div>
    </div>
  )
}
