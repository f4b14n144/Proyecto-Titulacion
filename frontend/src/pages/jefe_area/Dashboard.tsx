import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../../services/api'
import { descargarInforme } from '../../services/informes.service'
import { formatEstado } from '../../utils/formatters'
import { useAuth } from '../../hooks/useAuth'
import type { ApiResponse } from '../../types'

interface Informe {
  id: number
  consejo_id: number
  area_id: number
  tipo_informe: number
  estado: string
  ruta_docx: string | null
  generado_en: string | null
  enviado_en: string | null
  version: number
}

interface Consejo { id: number; periodo_id: number; fecha_consejo: string; fecha_limite_informe: string; flujo_estado: string }
interface Periodo { id: number; nombre: string; activo: boolean }

const TIPO_LABEL: Record<number, string> = {
  1: 'Informe 1 — Centro Docente',
  2: 'Informe 2 — Revisión AVAC',
  3: 'Informe 3 — Visitas Áulicas',
  4: 'Informe 4 — Análisis Final',
}

const TIPO_RUTA: Record<number, string> = {
  2: '/jefe/informe2',
  3: '/jefe/informe3',
  4: '/jefe/informe4',
}

const ESTADO_COLOR: Record<string, string> = {
  BORRADOR:  'bg-yellow-100 text-yellow-700',
  REVISANDO: 'bg-blue-100 text-blue-700',
  APROBADO:  'bg-green-100 text-green-700',
}

export default function JefeDashboard() {
  const { user } = useAuth()
  const [informes, setInformes] = useState<Informe[]>([])
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    const init = async () => {
      try {
        const [iRes, cRes, pRes] = await Promise.all([
          api.get<ApiResponse<Informe[]>>('/informes/'),
          api.get<ApiResponse<Consejo[]>>('/consejos/'),
          api.get<ApiResponse<Periodo[]>>('/periodos/'),
        ])
        let listaInformes = iRes.data.data
        const listaConsejos = cRes.data.data
        setConsejos(listaConsejos)
        setPeriodos(pRes.data.data)

        // El Informe 1 (Centro Docente) siempre debe existir para el jefe: hereda
        // el contenido de la Dirección. Antes se creaba solo al entrar a su
        // pantalla, así que en el dashboard aparecía "no hay informes". Aquí se
        // asegura para el consejo más reciente, para que aparezca siempre.
        if (user?.area_id && listaConsejos.length > 0) {
          const consejoActual = listaConsejos[0]  // el backend los ordena por fecha desc
          const tieneInforme1 = listaInformes.some(
            (i) => i.tipo_informe === 1 && i.consejo_id === consejoActual.id,
          )
          if (!tieneInforme1) {
            await api.post('/informes/generar-borrador', {
              consejo_id: consejoActual.id, area_id: user.area_id, tipo_informe: 1,
            })
            // El Informe 1 no usa IA: se genera casi al instante. Se recarga la lista.
            await new Promise((r) => setTimeout(r, 1500))
            const iRes2 = await api.get<ApiResponse<Informe[]>>('/informes/')
            listaInformes = iRes2.data.data
          }
        }
        setInformes(listaInformes)
      } catch {
        /* si algo falla, se muestra el dashboard vacío igualmente */
      } finally {
        setCargando(false)
      }
    }
    init()
  }, [user])

  const nombrePeriodo = (consejo_id: number) => {
    const consejo = consejos.find((c) => c.id === consejo_id)
    if (!consejo) return '—'
    return periodos.find((p) => p.id === consejo.periodo_id)?.nombre ?? '—'
  }

  const descargar = (informe: Informe) => {
    if (informe.ruta_docx) {
      descargarInforme(informe.id).catch(() => {})
    }
  }

  if (cargando) {
    return (
      <div className="flex justify-center py-16">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
      </div>
    )
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">
        Bienvenido, {user?.nombre_completo}
      </h1>
      <p className="text-gray-500 text-sm mb-6">Panel del Jefe de Área</p>

      {/* Mis informes — el Informe 1 siempre aparece (se asegura al cargar) */}
      <h2 className="font-semibold text-gray-700 mb-3">Mis informes</h2>
      {informes.length === 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-xl px-5 py-4 mb-8 text-sm text-gray-500">
          Aún no hay informes para tu área. Usa los formularios de abajo o el menú lateral
          para empezar.
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden mb-8">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Informe</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Período</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Versión</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {informes.map((inf) => (
                <tr key={inf.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">
                    {TIPO_LABEL[inf.tipo_informe] ?? `Informe ${inf.tipo_informe}`}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{nombrePeriodo(inf.consejo_id)}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${ESTADO_COLOR[inf.estado] ?? 'bg-gray-100 text-gray-500'}`}>
                      {formatEstado(inf.estado)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">v{inf.version}</td>
                  <td className="px-4 py-3 text-right space-x-3">
                    <Link
                      to={inf.tipo_informe === 1 ? '/jefe/informe1' : (TIPO_RUTA[inf.tipo_informe] ?? '#')}
                      className="text-ups-blue hover:underline text-xs"
                    >
                      {inf.tipo_informe === 1 ? 'Abrir' : 'Editar'}
                    </Link>
                    {inf.ruta_docx && (
                      <button onClick={() => descargar(inf)} className="text-green-600 hover:underline text-xs">
                        Descargar .docx
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Formularios para completar (2, 3, 4) — siempre disponibles */}
      <h2 className="font-semibold text-gray-700 mb-3">Formularios disponibles</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[2, 3, 4].map((tipo) => (
          <Link
            key={tipo}
            to={TIPO_RUTA[tipo]}
            className="bg-white rounded-xl border p-5 hover:border-ups-blue hover:shadow-sm transition flex flex-col gap-2"
          >
            <div className="flex items-center gap-3">
              <span className="bg-ups-blue text-white text-sm font-bold w-8 h-8 rounded-full flex items-center justify-center">
                {tipo}
              </span>
              <span className="font-medium text-gray-800 text-sm">{TIPO_LABEL[tipo]}</span>
            </div>
            <span className="text-xs text-ups-blue hover:underline">Ir al formulario →</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
