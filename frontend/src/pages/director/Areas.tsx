import { useState, useEffect } from 'react'
import api from '../../services/api'
import type { Area, ApiResponse } from '../../types'

export default function Areas() {
  const [areas, setAreas] = useState<Area[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState<Area | null>(null)
  const [nombre, setNombre] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [errorForm, setErrorForm] = useState('')

  const cargar = async () => {
    setCargando(true)
    setError('')
    try {
      const { data } = await api.get<ApiResponse<Area[]>>('/areas/')
      setAreas(data.data)
    } catch {
      setError('No se pudieron cargar las áreas.')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => { cargar() }, [])

  const abrirCrear = () => {
    setEditando(null)
    setNombre('')
    setErrorForm('')
    setModalAbierto(true)
  }

  const abrirEditar = (a: Area) => {
    setEditando(a)
    setNombre(a.nombre)
    setErrorForm('')
    setModalAbierto(true)
  }

  const cerrarModal = () => { setModalAbierto(false); setEditando(null) }

  const guardar = async () => {
    if (!nombre.trim()) { setErrorForm('El nombre es obligatorio.'); return }
    setGuardando(true)
    setErrorForm('')
    try {
      if (editando) {
        await api.put(`/areas/${editando.id}`, { nombre })
      } else {
        await api.post('/areas/', { nombre })
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

  const eliminar = async (a: Area) => {
    if (!confirm(`¿Eliminar el área "${a.nombre}"?`)) return
    try {
      await api.delete(`/areas/${a.id}`)
      await cargar()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(msg ?? 'No se pudo eliminar.')
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Áreas Curriculares</h1>
          <p className="text-sm text-gray-500 mt-0.5">Áreas de la Carrera de Computación</p>
        </div>
        <button
          onClick={abrirCrear}
          className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition"
        >
          + Nueva área
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      {cargando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {areas.length === 0 ? (
            <div className="col-span-3 bg-white rounded-xl border p-10 text-center text-gray-400 text-sm">
              No hay áreas registradas.
            </div>
          ) : areas.map((a) => (
            <div key={a.id} className="bg-white rounded-xl border p-4 flex items-center justify-between">
              <span className="font-medium text-gray-800">{a.nombre}</span>
              <div className="flex gap-2">
                <button onClick={() => abrirEditar(a)} className="text-ups-blue hover:underline text-xs">Editar</button>
                <button onClick={() => eliminar(a)} className="text-red-500 hover:underline text-xs">Eliminar</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {modalAbierto && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4">
              {editando ? 'Editar área' : 'Nueva área curricular'}
            </h2>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Nombre del área"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
            />
            {errorForm && <p className="text-sm text-red-600 mt-2">{errorForm}</p>}
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
