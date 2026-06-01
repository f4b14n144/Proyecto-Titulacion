import { useState, useEffect } from 'react'
import api from '../../services/api'
import type { Area, ApiResponse } from '../../types'

interface Asignatura { id: number; area_id: number; nombre: string; codigo: string }
type FormData = { area_id: string; nombre: string; codigo: string }

export default function Asignaturas() {
  const [asignaturas, setAsignaturas] = useState<Asignatura[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [filtroArea, setFiltroArea] = useState('')
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState<Asignatura | null>(null)
  const [form, setForm] = useState<FormData>({ area_id: '', nombre: '', codigo: '' })
  const [guardando, setGuardando] = useState(false)
  const [errorForm, setErrorForm] = useState('')

  const cargar = async () => {
    setCargando(true)
    setError('')
    try {
      const params = filtroArea ? { area_id: filtroArea } : {}
      const [asigRes, areaRes] = await Promise.all([
        api.get<ApiResponse<Asignatura[]>>('/asignaturas/', { params }),
        api.get<ApiResponse<Area[]>>('/areas/'),
      ])
      setAsignaturas(asigRes.data.data)
      setAreas(areaRes.data.data)
    } catch {
      setError('No se pudieron cargar los datos.')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => { cargar() }, [filtroArea])

  const abrirCrear = () => {
    setEditando(null)
    setForm({ area_id: filtroArea || (areas[0]?.id.toString() ?? ''), nombre: '', codigo: '' })
    setErrorForm('')
    setModalAbierto(true)
  }

  const abrirEditar = (a: Asignatura) => {
    setEditando(a)
    setForm({ area_id: a.area_id.toString(), nombre: a.nombre, codigo: a.codigo })
    setErrorForm('')
    setModalAbierto(true)
  }

  const cerrarModal = () => { setModalAbierto(false); setEditando(null) }

  const guardar = async () => {
    if (!form.area_id || !form.nombre.trim() || !form.codigo.trim()) {
      setErrorForm('Todos los campos son obligatorios.')
      return
    }
    setGuardando(true)
    setErrorForm('')
    try {
      const payload = { area_id: Number(form.area_id), nombre: form.nombre, codigo: form.codigo }
      if (editando) {
        await api.put(`/asignaturas/${editando.id}`, payload)
      } else {
        await api.post('/asignaturas/', payload)
      }
      await cargar()
      cerrarModal()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorForm(msg ?? 'Error al guardar.')
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async (a: Asignatura) => {
    if (!confirm(`¿Eliminar "${a.nombre}" (${a.codigo})?`)) return
    try {
      await api.delete(`/asignaturas/${a.id}`)
      await cargar()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(msg ?? 'No se pudo eliminar.')
    }
  }

  const nombreArea = (id: number) => areas.find((a) => a.id === id)?.nombre ?? `Área ${id}`

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Asignaturas</h1>
          <p className="text-sm text-gray-500 mt-0.5">Asignaturas por área curricular</p>
        </div>
        <button onClick={abrirCrear} className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition">
          + Nueva asignatura
        </button>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm text-gray-600">Filtrar por área:</label>
        <select
          value={filtroArea}
          onChange={(e) => setFiltroArea(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
        >
          <option value="">Todas</option>
          {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
        </select>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      {cargando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          {asignaturas.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-10">No hay asignaturas registradas.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Código</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Nombre</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Área</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {asignaturas.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-gray-600">{a.codigo}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{a.nombre}</td>
                    <td className="px-4 py-3 text-gray-500">{nombreArea(a.area_id)}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => abrirEditar(a)} className="text-ups-blue hover:underline text-xs mr-3">Editar</button>
                      <button onClick={() => eliminar(a)} className="text-red-500 hover:underline text-xs">Eliminar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {modalAbierto && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4">
              {editando ? 'Editar asignatura' : 'Nueva asignatura'}
            </h2>
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Área</label>
                <select
                  value={form.area_id}
                  onChange={(e) => setForm({ ...form, area_id: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                >
                  <option value="">Seleccionar área</option>
                  {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
                <input
                  type="text"
                  value={form.nombre}
                  onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  placeholder="Ej: Programación Orientada a Objetos"
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Código</label>
                <input
                  type="text"
                  value={form.codigo}
                  onChange={(e) => setForm({ ...form, codigo: e.target.value.toUpperCase() })}
                  placeholder="Ej: INF-301"
                  className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ups-blue"
                />
              </div>
              {errorForm && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{errorForm}</p>}
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={cerrarModal} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancelar</button>
              <button
                onClick={guardar}
                disabled={guardando}
                className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60"
              >
                {guardando ? 'Guardando...' : editando ? 'Guardar' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
