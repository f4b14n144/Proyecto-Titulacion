import { useState, useEffect } from 'react'
import { periodosService } from '../../services/periodos.service'
import { formatFecha } from '../../utils/formatters'
import type { PeriodoAcademico } from '../../types'

type FormData = { nombre: string; fecha_inicio: string; fecha_fin: string; activo: boolean }

const formVacio: FormData = { nombre: '', fecha_inicio: '', fecha_fin: '', activo: true }

export default function Periodos() {
  const [periodos, setPeriodos] = useState<PeriodoAcademico[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState<PeriodoAcademico | null>(null)
  const [form, setForm] = useState<FormData>(formVacio)
  const [guardando, setGuardando] = useState(false)
  const [errorForm, setErrorForm] = useState('')

  const cargar = async () => {
    setCargando(true)
    setError('')
    try {
      const datos = await periodosService.listar()
      setPeriodos(datos)
    } catch {
      setError('No se pudieron cargar los períodos.')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => { cargar() }, [])

  const abrirCrear = () => {
    setEditando(null)
    setForm(formVacio)
    setErrorForm('')
    setModalAbierto(true)
  }

  const abrirEditar = (p: PeriodoAcademico) => {
    setEditando(p)
    setForm({
      nombre: p.nombre,
      fecha_inicio: p.fecha_inicio,
      fecha_fin: p.fecha_fin,
      activo: p.activo,
    })
    setErrorForm('')
    setModalAbierto(true)
  }

  const cerrarModal = () => {
    setModalAbierto(false)
    setEditando(null)
  }

  const guardar = async () => {
    if (!form.nombre || !form.fecha_inicio || !form.fecha_fin) {
      setErrorForm('Todos los campos son obligatorios.')
      return
    }
    if (form.fecha_fin <= form.fecha_inicio) {
      setErrorForm('La fecha de fin debe ser posterior a la de inicio.')
      return
    }
    setGuardando(true)
    setErrorForm('')
    try {
      if (editando) {
        await periodosService.actualizar(editando.id, form)
      } else {
        await periodosService.crear(form)
      }
      await cargar()
      cerrarModal()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorForm(msg ?? 'Error al guardar el período.')
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async (p: PeriodoAcademico) => {
    if (!confirm(`¿Eliminar el período "${p.nombre}"? Esta acción no se puede deshacer.`)) return
    try {
      await periodosService.eliminar(p.id)
      await cargar()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(msg ?? 'No se pudo eliminar el período.')
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Períodos Académicos</h1>
          <p className="text-sm text-gray-500 mt-0.5">Gestiona los períodos del sistema</p>
        </div>
        <button
          onClick={abrirCrear}
          className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition"
        >
          + Nuevo período
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>
      )}

      {cargando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : periodos.length === 0 ? (
        <div className="bg-white rounded-xl border p-10 text-center text-gray-400 text-sm">
          No hay períodos registrados. Crea el primero.
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Nombre</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Inicio</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fin</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {periodos.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{p.nombre}</td>
                  <td className="px-4 py-3 text-gray-600">{formatFecha(p.fecha_inicio)}</td>
                  <td className="px-4 py-3 text-gray-600">{formatFecha(p.fecha_fin)}</td>
                  <td className="px-4 py-3">
                    {p.activo ? (
                      <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-medium">
                        Activo
                      </span>
                    ) : (
                      <span className="bg-gray-100 text-gray-500 px-2 py-0.5 rounded text-xs">
                        Inactivo
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => abrirEditar(p)}
                      className="text-ups-blue hover:underline text-xs mr-3"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => eliminar(p)}
                      className="text-red-500 hover:underline text-xs"
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal crear/editar */}
      {modalAbierto && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4">
              {editando ? 'Editar período' : 'Nuevo período académico'}
            </h2>

            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
                <input
                  type="text"
                  value={form.nombre}
                  onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  placeholder="Ej: 2026-1"
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Fecha inicio</label>
                  <input
                    type="date"
                    value={form.fecha_inicio}
                    onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Fecha fin</label>
                  <input
                    type="date"
                    value={form.fecha_fin}
                    onChange={(e) => setForm({ ...form, fecha_fin: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.activo}
                  onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                  className="w-4 h-4 accent-ups-blue"
                />
                Marcar como período activo
                <span className="text-xs text-gray-400">(desactiva el actual)</span>
              </label>

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
                {guardando ? 'Guardando...' : editando ? 'Guardar cambios' : 'Crear período'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
