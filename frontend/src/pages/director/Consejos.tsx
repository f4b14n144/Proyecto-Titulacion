import { useState, useEffect } from 'react'
import { consejosService, type Consejo, type ConsejoCreate } from '../../services/consejos.service'
import { periodosService } from '../../services/periodos.service'
import FechasEntrega from '../../components/FechasEntrega'
import { formatFecha, formatEstado } from '../../utils/formatters'
import type { PeriodoAcademico } from '../../types'

type FormData = {
  periodo_id: string
  fecha_consejo: string
  fecha_limite_informe: string
  fecha_activacion: string
}

const formVacio: FormData = {
  periodo_id: '',
  fecha_consejo: '',
  fecha_limite_informe: '',
  fecha_activacion: '',
}

/** Resta días a una fecha 'YYYY-MM-DD' y devuelve otra 'YYYY-MM-DD'. */
function restarDias(fecha: string, dias: number): string {
  if (!fecha) return ''
  const d = new Date(fecha + 'T00:00:00')
  d.setDate(d.getDate() - dias)
  return d.toISOString().slice(0, 10)
}

const ESTADOS_COLOR: Record<string, string> = {
  PENDIENTE: 'bg-yellow-100 text-yellow-700',
  PROCESANDO: 'bg-blue-100 text-blue-700',
  COMPLETADO: 'bg-green-100 text-green-700',
  ERROR: 'bg-red-100 text-red-700',
}

export default function Consejos() {
  const [consejos, setConsejos] = useState<Consejo[]>([])
  const [periodos, setPeriodos] = useState<PeriodoAcademico[]>([])
  const [filtroPeriodo, setFiltroPeriodo] = useState<string>('')
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState<Consejo | null>(null)
  const [form, setForm] = useState<FormData>(formVacio)
  const [guardando, setGuardando] = useState(false)
  const [errorForm, setErrorForm] = useState('')
  // Consejo cuyas fechas de entrega se están editando
  const [fechasDe, setFechasDe] = useState<Consejo | null>(null)

  const cargar = async () => {
    setCargando(true)
    setError('')
    try {
      const [c, p] = await Promise.all([
        consejosService.listar(filtroPeriodo ? Number(filtroPeriodo) : undefined),
        periodosService.listar(),
      ])
      setConsejos(c)
      setPeriodos(p)
    } catch {
      setError('No se pudieron cargar los consejos.')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => { cargar() }, [filtroPeriodo])

  const abrirCrear = () => {
    setEditando(null)
    setForm({ ...formVacio, periodo_id: filtroPeriodo || (periodos[0]?.id.toString() ?? '') })
    setErrorForm('')
    setModalAbierto(true)
  }

  const abrirEditar = (c: Consejo) => {
    setEditando(c)
    setForm({
      periodo_id: c.periodo_id.toString(),
      fecha_consejo: c.fecha_consejo,
      fecha_limite_informe: c.fecha_limite_informe,
      fecha_activacion: c.fecha_activacion ?? '',
    })
    setErrorForm('')
    setModalAbierto(true)
  }

  const cerrarModal = () => { setModalAbierto(false); setEditando(null) }

  const guardar = async () => {
    if (!form.periodo_id || !form.fecha_consejo || !form.fecha_limite_informe) {
      setErrorForm('Período, fecha del consejo y fecha límite son obligatorios.')
      return
    }
    setGuardando(true)
    setErrorForm('')
    try {
      const payload: ConsejoCreate = {
        periodo_id: Number(form.periodo_id),
        fecha_consejo: form.fecha_consejo,
        fecha_limite_informe: form.fecha_limite_informe,
        fecha_activacion: form.fecha_activacion || null,
      }
      if (editando) {
        await consejosService.actualizar(editando.id, payload)
      } else {
        await consejosService.crear(payload)
      }
      await cargar()
      cerrarModal()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorForm(msg ?? 'Error al guardar el consejo.')
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async (c: Consejo) => {
    if (!confirm(`¿Eliminar el Consejo del ${formatFecha(c.fecha_consejo)}?`)) return
    try {
      await consejosService.eliminar(c.id)
      await cargar()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(msg ?? 'No se pudo eliminar el consejo.')
    }
  }

  const nombrePeriodo = (id: number) =>
    periodos.find((p) => p.id === id)?.nombre ?? `Período ${id}`

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Consejos de Carrera</h1>
          <p className="text-sm text-gray-500 mt-0.5">Fechas de reunión y límites de informe</p>
        </div>
        <button
          onClick={abrirCrear}
          className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition"
        >
          + Nuevo consejo
        </button>
      </div>

      {/* Filtro por período */}
      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm text-gray-600">Filtrar por período:</label>
        <select
          value={filtroPeriodo}
          onChange={(e) => setFiltroPeriodo(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
        >
          <option value="">Todos</option>
          {periodos.map((p) => (
            <option key={p.id} value={p.id}>{p.nombre}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>
      )}

      {cargando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : consejos.length === 0 ? (
        <div className="bg-white rounded-xl border p-10 text-center text-gray-400 text-sm">
          No hay consejos registrados.
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Período</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fecha consejo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fecha límite</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Activación</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {consejos.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{nombrePeriodo(c.periodo_id)}</td>
                  <td className="px-4 py-3 text-gray-600">{formatFecha(c.fecha_consejo)}</td>
                  <td className="px-4 py-3 text-gray-600">{formatFecha(c.fecha_limite_informe)}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {c.fecha_activacion ? formatFecha(c.fecha_activacion) : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${ESTADOS_COLOR[c.flujo_estado] ?? 'bg-gray-100 text-gray-500'}`}>
                      {formatEstado(c.flujo_estado)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setFechasDe(c)}
                      className="text-ups-blue hover:underline text-xs mr-3"
                      title="Fijar la fecha de entrega de cada informe"
                    >
                      Fechas de entrega
                    </button>
                    {c.flujo_estado === 'PENDIENTE' && (
                      <>
                        <button
                          onClick={() => abrirEditar(c)}
                          className="text-ups-blue hover:underline text-xs mr-3"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => eliminar(c)}
                          className="text-red-500 hover:underline text-xs"
                        >
                          Eliminar
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal */}
      {modalAbierto && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4">
              {editando ? 'Editar consejo' : 'Nuevo Consejo de Carrera'}
            </h2>

            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Período académico</label>
                <select
                  value={form.periodo_id}
                  onChange={(e) => setForm({ ...form, periodo_id: e.target.value })}
                  disabled={!!editando}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue disabled:bg-gray-50"
                >
                  <option value="">Seleccionar período</option>
                  {periodos.map((p) => (
                    <option key={p.id} value={p.id}>{p.nombre}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fecha del consejo</label>
                <input
                  type="date"
                  value={form.fecha_consejo}
                  onChange={(e) => {
                    // Al elegir la fecha del consejo, la fecha límite se rellena
                    // sola 2 días antes (se puede cambiar después).
                    const fc = e.target.value
                    setForm({ ...form, fecha_consejo: fc, fecha_limite_informe: restarDias(fc, 2) })
                  }}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fecha límite del informe{' '}
                  <span className="text-gray-400 font-normal">(2 días antes del consejo, automática — editable)</span>
                </label>
                <input
                  type="date"
                  value={form.fecha_limite_informe}
                  onChange={(e) => setForm({ ...form, fecha_limite_informe: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fecha de activación del flujo{' '}
                  <span className="text-gray-400 font-normal">(opcional — 2 días antes del límite por defecto)</span>
                </label>
                <input
                  type="date"
                  value={form.fecha_activacion}
                  onChange={(e) => setForm({ ...form, fecha_activacion: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                />
              </div>

              {errorForm && (
                <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{errorForm}</p>
              )}
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={cerrarModal}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition"
              >
                Cancelar
              </button>
              <button
                onClick={guardar}
                disabled={guardando}
                className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition disabled:opacity-60"
              >
                {guardando ? 'Guardando...' : editando ? 'Guardar cambios' : 'Crear consejo'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fechas de entrega de los 4 informes (y sus recordatorios automáticos) */}
      {fechasDe && (
        <FechasEntrega
          consejoId={fechasDe.id}
          etiqueta={`${nombrePeriodo(fechasDe.periodo_id)} — Consejo del ${formatFecha(fechasDe.fecha_consejo)}`}
          onCerrar={() => setFechasDe(null)}
        />
      )}
    </div>
  )
}
