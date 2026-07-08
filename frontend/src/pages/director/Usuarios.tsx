import { useState, useEffect } from 'react'
import api from '../../services/api'
import type { ApiResponse, Rol } from '../../types'

interface UsuarioRow {
  id: number
  nombre_completo: string
  email_institucional: string
  rol_id: number
  activo: boolean
  rol_efectivo?: string | null
}

type FormData = {
  nombre_completo: string
  email_institucional: string
  password: string
  rol_id: string
}

const formVacio: FormData = {
  nombre_completo: '',
  email_institucional: '',
  password: '',
  rol_id: '',
}

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState<UsuarioRow[]>([])
  const [roles, setRoles] = useState<Rol[]>([])
  const [filtroRol, setFiltroRol] = useState('')
  const [filtroActivo, setFiltroActivo] = useState('')
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState<UsuarioRow | null>(null)
  const [form, setForm] = useState<FormData>(formVacio)
  const [guardando, setGuardando] = useState(false)
  const [errorForm, setErrorForm] = useState('')

  const cargar = async () => {
    setCargando(true)
    setError('')
    try {
      const params: Record<string, string> = {}
      if (filtroRol) params.rol = filtroRol  // filtra por rol EFECTIVO
      if (filtroActivo !== '') params.activo = filtroActivo
      const [uRes, rRes] = await Promise.all([
        api.get<ApiResponse<UsuarioRow[]>>('/usuarios/', { params }),
        api.get<ApiResponse<Rol[]>>('/usuarios/roles/lista'),
      ])
      setUsuarios(uRes.data.data)
      setRoles(rRes.data.data)
    } catch {
      setError('No se pudieron cargar los usuarios.')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => { cargar() }, [filtroRol, filtroActivo])

  const abrirCrear = () => {
    setEditando(null)
    setForm(formVacio)
    setErrorForm('')
    setModalAbierto(true)
  }

  const abrirEditar = (u: UsuarioRow) => {
    setEditando(u)
    setForm({
      nombre_completo: u.nombre_completo,
      email_institucional: u.email_institucional,
      password: '',
      rol_id: u.rol_id.toString(),
    })
    setErrorForm('')
    setModalAbierto(true)
  }

  const cerrarModal = () => { setModalAbierto(false); setEditando(null) }

  const guardar = async () => {
    if (!form.nombre_completo.trim() || !form.email_institucional.trim() || !form.rol_id) {
      setErrorForm('Nombre, email y rol son obligatorios.')
      return
    }
    if (!editando && !form.password.trim()) {
      setErrorForm('La contraseña es obligatoria al crear un usuario.')
      return
    }
    setGuardando(true)
    setErrorForm('')
    try {
      if (editando) {
        const payload: Record<string, unknown> = {
          nombre_completo: form.nombre_completo,
          email_institucional: form.email_institucional,
          rol_id: Number(form.rol_id),
        }
        if (form.password.trim()) payload.password = form.password
        await api.put(`/usuarios/${editando.id}`, payload)
      } else {
        await api.post('/usuarios/', {
          nombre_completo: form.nombre_completo,
          email_institucional: form.email_institucional,
          password: form.password,
          rol_id: Number(form.rol_id),
        })
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

  const toggleActivo = async (u: UsuarioRow) => {
    const accion = u.activo ? 'desactivar' : 'reactivar'
    if (!confirm(`¿${accion.charAt(0).toUpperCase() + accion.slice(1)} a ${u.nombre_completo}?`)) return
    try {
      if (u.activo) {
        await api.delete(`/usuarios/${u.id}`)
      } else {
        await api.put(`/usuarios/${u.id}`, { activo: true })
      }
      await cargar()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(msg ?? 'No se pudo realizar la acción.')
    }
  }

  const nombreRol = (id: number) => {
    const r = roles.find((r) => r.id === id)
    return r ? r.nombre.replace('_', ' ') : `#${id}`
  }

  // Rol a mostrar: el efectivo (jefe si tiene jefatura activa) si viene del backend,
  // si no, el rol base por rol_id.
  const rolMostrado = (u: UsuarioRow): string =>
    u.rol_efectivo ?? roles.find((r) => r.id === u.rol_id)?.nombre ?? ''

  const ROL_COLOR: Record<string, string> = {
    DIRECTOR_CARRERA: 'bg-ups-blue text-white',
    JEFE_AREA: 'bg-purple-100 text-purple-700',
    DOCENTE: 'bg-gray-100 text-gray-600',
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Usuarios</h1>
          <p className="text-sm text-gray-500 mt-0.5">Gestión de usuarios del sistema</p>
        </div>
        <button
          onClick={abrirCrear}
          className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition"
        >
          + Nuevo usuario
        </button>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 mb-5">
        <select
          value={filtroRol}
          onChange={(e) => setFiltroRol(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
        >
          <option value="">Todos los roles</option>
          {roles.map((r) => (
            <option key={r.id} value={r.nombre}>{r.nombre.replace('_', ' ')}</option>
          ))}
        </select>
        <select
          value={filtroActivo}
          onChange={(e) => setFiltroActivo(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
        >
          <option value="">Todos</option>
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
        </select>
        <span className="text-sm text-gray-400 self-center">{usuarios.length} resultado(s)</span>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      {cargando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          {usuarios.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-10">No hay usuarios que coincidan.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Nombre</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Rol</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {usuarios.map((u) => (
                  <tr key={u.id} className={`hover:bg-gray-50 ${!u.activo ? 'opacity-50' : ''}`}>
                    <td className="px-4 py-3 font-medium text-gray-800">{u.nombre_completo}</td>
                    <td className="px-4 py-3 text-gray-500">{u.email_institucional}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${ROL_COLOR[rolMostrado(u)] ?? 'bg-gray-100 text-gray-600'}`}>
                        {rolMostrado(u).replace('_', ' ') || nombreRol(u.rol_id)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {u.activo
                        ? <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs">Activo</span>
                        : <span className="bg-gray-100 text-gray-400 px-2 py-0.5 rounded text-xs">Inactivo</span>
                      }
                    </td>
                    <td className="px-4 py-3 text-right space-x-3">
                      <button onClick={() => abrirEditar(u)} className="text-ups-blue hover:underline text-xs">
                        Editar
                      </button>
                      <button
                        onClick={() => toggleActivo(u)}
                        className={`text-xs hover:underline ${u.activo ? 'text-red-500' : 'text-green-600'}`}
                      >
                        {u.activo ? 'Desactivar' : 'Reactivar'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Modal */}
      {modalAbierto && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4">
              {editando ? 'Editar usuario' : 'Nuevo usuario'}
            </h2>
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre completo</label>
                <input
                  type="text"
                  value={form.nombre_completo}
                  onChange={(e) => setForm({ ...form, nombre_completo: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email institucional</label>
                <input
                  type="email"
                  value={form.email_institucional}
                  onChange={(e) => setForm({ ...form, email_institucional: e.target.value })}
                  placeholder="usuario@ups.edu.ec"
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Contraseña {editando && <span className="text-gray-400 font-normal">(dejar vacío para no cambiar)</span>}
                </label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Rol</label>
                <select
                  value={form.rol_id}
                  onChange={(e) => setForm({ ...form, rol_id: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
                >
                  <option value="">Seleccionar rol</option>
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>{r.nombre.replace('_', ' ')}</option>
                  ))}
                </select>
              </div>
              {errorForm && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{errorForm}</p>}
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={cerrarModal} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Cancelar
              </button>
              <button
                onClick={guardar}
                disabled={guardando}
                className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60"
              >
                {guardando ? 'Guardando...' : editando ? 'Guardar cambios' : 'Crear usuario'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
