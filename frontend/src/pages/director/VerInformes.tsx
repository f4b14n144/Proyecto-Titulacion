import { useState, useEffect } from 'react'
import api from '../../services/api'
import { formatEstado } from '../../utils/formatters'
import type { Area, ApiResponse } from '../../types'

interface Informe {
  id: number
  consejo_id: number
  area_id: number
  tipo_informe: number
  estado: string
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
  const [msg, setMsg] = useState('')

  // Form generar borrador
  const [consejoId, setConsejoId] = useState('')
  const [areaId, setAreaId] = useState('')
  const [tipo, setTipo] = useState('3')
  const [generando, setGenerando] = useState(false)

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

  const generar = async () => {
    if (!consejoId || !areaId || !tipo) {
      setError('Selecciona consejo, área y tipo de informe.')
      return
    }
    setGenerando(true); setError(''); setMsg('')
    try {
      await api.post('/informes/generar-borrador', {
        consejo_id: Number(consejoId),
        area_id: Number(areaId),
        tipo_informe: Number(tipo),
      })
      setMsg('Generación iniciada. Los informes con IA (3 y 4) pueden tardar 1-2 min. Recarga para ver el resultado.')
    } catch (e: unknown) {
      const m = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(m ?? 'Error al generar el borrador.')
    } finally {
      setGenerando(false)
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Ver Informes</h1>
          <p className="text-sm text-gray-500 mt-0.5">Informes de todas las áreas</p>
        </div>
        <button onClick={cargar} className="text-sm text-ups-blue hover:underline">↻ Actualizar</button>
      </div>

      {/* Generar borrador */}
      <div className="bg-white rounded-xl border p-5 mb-6">
        <h2 className="font-semibold text-gray-700 mb-3">Generar borrador de informe</h2>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Consejo</label>
            <select value={consejoId} onChange={(e) => setConsejoId(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
              <option value="">Seleccionar</option>
              {consejos.map((c) => (
                <option key={c.id} value={c.id}>{periodoDeConsejo(c.id)} — {c.fecha_consejo}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Área</label>
            <select value={areaId} onChange={(e) => setAreaId(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
              <option value="">Seleccionar</option>
              {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Tipo</label>
            <select value={tipo} onChange={(e) => setTipo(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
              <option value="1">Informe 1 — Centro Docente</option>
              <option value="2">Informe 2 — AVAC</option>
              <option value="3">Informe 3 — Visitas + Interciclo</option>
              <option value="4">Informe 4 — Análisis Final</option>
            </select>
          </div>
          <button onClick={generar} disabled={generando}
            className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
            {generando ? 'Generando...' : 'Generar borrador'}
          </button>
        </div>
        {msg && <p className="text-green-600 text-sm bg-green-50 px-3 py-2 rounded mt-3">{msg}</p>}
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      {/* Lista de informes */}
      {cargando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : informes.length === 0 ? (
        <div className="bg-white rounded-xl border p-10 text-center text-gray-400 text-sm">
          No hay informes generados todavía. Genera el primero arriba.
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
                    {inf.ruta_docx ? (
                      <a href={`/api/v1/informes/${inf.id}/descargar`}
                        className="text-green-600 hover:underline text-xs">Descargar .docx</a>
                    ) : (
                      <span className="text-gray-300 text-xs">Sin documento</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
