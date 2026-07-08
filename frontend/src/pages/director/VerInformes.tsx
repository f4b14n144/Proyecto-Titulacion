import { useState, useEffect, useRef } from 'react'
import { renderAsync } from 'docx-preview'
import api from '../../services/api'
import { descargarInforme, obtenerDocxBlob } from '../../services/informes.service'
import { formatEstado } from '../../utils/formatters'
import { Eye, Download, X } from 'lucide-react'
import type { Area, ApiResponse } from '../../types'

interface Informe {
  id: number
  consejo_id: number
  area_id: number
  tipo_informe: number
  estado: string
  contenido_json?: Record<string, unknown> | null
  ruta_docx: string | null
  version: number
}
interface Consejo { id: number; periodo_id: number; fecha_consejo: string }
interface Periodo { id: number; nombre: string }

const TIPO_LABEL: Record<number, string> = {
  1: 'Informe 1 — Centro Docente',
  2: 'Informe 2 — Revisión AVAC',
  3: 'Informe 3 — Visitas Áulicas',
  4: 'Informe 4 — Análisis Final',
}

const ESTADO_COLOR: Record<string, string> = {
  BORRADOR: 'bg-yellow-100 text-yellow-700',
  REVISANDO: 'bg-blue-100 text-blue-700',
  APROBADO: 'bg-green-100 text-green-700',
}

export default function VerInformes() {
  const [informes, setInformes] = useState<Informe[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [descargando, setDescargando] = useState<number | null>(null)
  const [preview, setPreview] = useState<Informe | null>(null)
  const [cargandoPreview, setCargandoPreview] = useState(false)
  const [previewError, setPreviewError] = useState('')
  const docxRef = useRef<HTMLDivElement>(null)

  const cargar = async () => {
    setCargando(true)
    setError('')
    try {
      const [iRes, aRes, cRes, pRes] = await Promise.all([
        api.get<ApiResponse<Informe[]>>('/informes/'),
        api.get<ApiResponse<Area[]>>('/areas/'),
        api.get<ApiResponse<Consejo[]>>('/consejos/'),
        api.get<ApiResponse<Periodo[]>>('/periodos/'),
      ])
      setInformes(iRes.data.data)
      setAreas(aRes.data.data)
      setConsejos(cRes.data.data)
      setPeriodos(pRes.data.data)
    } catch {
      setError('No se pudieron cargar los informes.')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => { cargar() }, [])

  const nombreArea = (id: number) => areas.find((a) => a.id === id)?.nombre ?? `Área ${id}`
  const periodoDeConsejo = (cid: number) => {
    const c = consejos.find((x) => x.id === cid)
    return c ? (periodos.find((p) => p.id === c.periodo_id)?.nombre ?? '—') : '—'
  }

  const descargar = async (inf: Informe) => {
    setDescargando(inf.id)
    setError('')
    try {
      await descargarInforme(inf.id)
    } catch {
      setError('No se pudo descargar el documento.')
    } finally {
      setDescargando(null)
    }
  }

  const verPreview = (inf: Informe) => {
    setPreviewError('')
    setPreview(inf)
  }

  // Cuando se abre el preview, renderiza el .docx real dentro del modal
  useEffect(() => {
    if (!preview) return
    let cancelado = false
    const render = async () => {
      if (!preview.ruta_docx) {
        setPreviewError('Este informe aún no tiene documento generado. Genéralo desde el panel del jefe de área.')
        return
      }
      setCargandoPreview(true)
      setPreviewError('')
      try {
        const blob = await obtenerDocxBlob(preview.id)
        // Esperar a que el contenedor exista en el DOM
        await new Promise((r) => setTimeout(r, 50))
        if (cancelado || !docxRef.current) return
        docxRef.current.innerHTML = ''
        await renderAsync(blob, docxRef.current, undefined, {
          className: 'docx', inWrapper: true, ignoreWidth: false, ignoreHeight: false,
        })
      } catch {
        if (!cancelado) setPreviewError('No se pudo renderizar el documento.')
      } finally {
        if (!cancelado) setCargandoPreview(false)
      }
    }
    render()
    return () => { cancelado = true }
  }, [preview])

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Ver Informes</h1>
          <p className="text-sm text-gray-500 mt-0.5">Informes generados de todas las áreas</p>
        </div>
        <button onClick={cargar} className="text-sm text-ups-blue hover:underline">↻ Actualizar</button>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      {cargando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : informes.length === 0 ? (
        <div className="bg-white rounded-xl border p-10 text-center text-gray-400 text-sm">
          No hay informes generados todavía. Los informes se generan desde el panel del
          jefe de área (Informes 2, 3 y 4) o al activarse el flujo del Consejo.
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Informe</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Área</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Período</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Versión</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {informes.map((inf) => (
                <tr key={inf.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{TIPO_LABEL[inf.tipo_informe] ?? `Informe ${inf.tipo_informe}`}</td>
                  <td className="px-4 py-3 text-gray-600">{nombreArea(inf.area_id)}</td>
                  <td className="px-4 py-3 text-gray-500">{periodoDeConsejo(inf.consejo_id)}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${ESTADO_COLOR[inf.estado] ?? 'bg-gray-100 text-gray-500'}`}>
                      {formatEstado(inf.estado)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">v{inf.version}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-3">
                      <button
                        onClick={() => verPreview(inf)}
                        className="flex items-center gap-1 text-ups-blue hover:underline text-xs"
                      >
                        <Eye size={14} /> Ver
                      </button>
                      {inf.ruta_docx ? (
                        <button
                          onClick={() => descargar(inf)}
                          disabled={descargando === inf.id}
                          className="flex items-center gap-1 text-green-600 hover:underline text-xs disabled:opacity-50"
                        >
                          <Download size={14} /> {descargando === inf.id ? 'Descargando...' : '.docx'}
                        </button>
                      ) : (
                        <span className="text-gray-300 text-xs">Sin documento</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal de vista previa */}
      {(preview || cargandoPreview) && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-3 border-b">
              <div>
                <h2 className="font-bold text-gray-800">
                  {preview ? (TIPO_LABEL[preview.tipo_informe] ?? 'Informe') : 'Cargando...'}
                </h2>
                {preview && (
                  <p className="text-xs text-gray-500">
                    {nombreArea(preview.area_id)} · {periodoDeConsejo(preview.consejo_id)} · v{preview.version}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {preview?.ruta_docx && (
                  <button onClick={() => descargar(preview)}
                    className="flex items-center gap-1 bg-green-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-green-700">
                    <Download size={14} /> Descargar
                  </button>
                )}
                <button onClick={() => setPreview(null)} className="text-gray-400 hover:text-gray-700">
                  <X size={20} />
                </button>
              </div>
            </div>
            <div className="overflow-y-auto p-5 bg-gray-100">
              {cargandoPreview && (
                <div className="flex flex-col items-center gap-3 py-10">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
                  <p className="text-sm text-gray-500">Cargando documento…</p>
                </div>
              )}
              {previewError && (
                <p className="text-red-600 text-sm bg-red-50 px-3 py-4 rounded text-center">{previewError}</p>
              )}
              {/* Aquí se renderiza el .docx real que se va a generar/descargar */}
              <div ref={docxRef} className="docx-preview-container" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
