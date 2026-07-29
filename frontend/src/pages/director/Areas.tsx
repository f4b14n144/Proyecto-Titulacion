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
  const [verInactivas, setVerInactivas] = useState(false)

  const cargar = async () => {
    setCargando(true)
    setError('')
    try {
      const { data } = await api.get<ApiResponse<Area[]>>('/areas/', {
        params: verInactivas ? { incluir_inactivas: true } : {},
      })
      setAreas(data.data)
    } catch {
      setError('No se pudieron cargar las áreas.')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => { cargar() }, [verInactivas])

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
    if (!confirm(
      `¿Eliminar el área "${a.nombre}"?\n\n` +
      'Si el área ya tiene materias, informes o jefaturas, no se borra: se ' +
      'desactiva (sale del catálogo pero se conserva en el histórico).'
    )) return
    try {
      const { data } = await api.delete<ApiResponse<null>>(`/areas/${a.id}`)
      await cargar()
      if (data.message) alert(data.message)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(msg ?? 'No se pudo eliminar.')
    }
  }

  const cambiarEstado = async (a: Area, activa: boolean) => {
    try {
      await api.put(`/areas/${a.id}/activa`, null, { params: { activa } })
      await cargar()
    } catch {
      alert('No se pudo cambiar el estado del área.')
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

      <label className="flex items-center gap-2 text-sm text-gray-600 mb-4 cursor-pointer w-fit">
        <input type="checkbox" checked={verInactivas} onChange={(e) => setVerInactivas(e.target.checked)} />
        Mostrar áreas desactivadas
      </label>

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
            <div key={a.id} className={`bg-white rounded-xl border p-4 flex items-center justify-between ${a.activa === false ? 'opacity-60' : ''}`}>
              <span className="font-medium text-gray-800 flex items-center gap-2">
                {a.nombre}
                {a.activa === false && (
                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">Desactivada</span>
                )}
              </span>
              <div className="flex gap-2">
                {a.activa === false ? (
                  <button onClick={() => cambiarEstado(a, true)} className="text-green-600 hover:underline text-xs">Reactivar</button>
                ) : (
                  <>
                    <button onClick={() => abrirEditar(a)} className="text-ups-blue hover:underline text-xs">Editar</button>
                    <button onClick={() => eliminar(a)} className="text-red-500 hover:underline text-xs">Eliminar</button>
                  </>
                )}
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
