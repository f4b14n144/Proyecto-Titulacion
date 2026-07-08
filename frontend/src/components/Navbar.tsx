import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [modal, setModal] = useState(false)
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [repite, setRepite] = useState('')
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const [guardando, setGuardando] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const abrir = () => {
    setActual(''); setNueva(''); setRepite(''); setError(''); setOk('')
    setModal(true)
  }

  const cambiar = async () => {
    setError(''); setOk('')
    if (!actual || !nueva) { setError('Completa todos los campos.'); return }
    if (nueva.length < 6) { setError('La nueva contraseña debe tener al menos 6 caracteres.'); return }
    if (nueva !== repite) { setError('La nueva contraseña y su confirmación no coinciden.'); return }
    setGuardando(true)
    try {
      await api.post('/auth/cambiar-password', { password_actual: actual, password_nueva: nueva })
      setOk('Contraseña actualizada correctamente.')
      setActual(''); setNueva(''); setRepite('')
    } catch (e: unknown) {
      const m = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(m ?? 'No se pudo cambiar la contraseña.')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <>
      <header className="bg-ups-blue text-white h-14 flex items-center justify-between px-6 shadow">
        <div className="flex items-center gap-3">
          <span className="font-bold text-lg tracking-wide">Sistema Informes UPS</span>
          <span className="text-xs bg-white/20 px-2 py-0.5 rounded">Carrera de Computación</span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span>{user?.nombre_completo}</span>
          <span className="bg-white/20 px-2 py-0.5 rounded text-xs">{user?.rol?.replace('_', ' ')}</span>
          <button onClick={abrir} className="bg-white/10 hover:bg-white/20 px-3 py-1 rounded transition">
            Cambiar contraseña
          </button>
          <button onClick={handleLogout} className="bg-white/10 hover:bg-white/20 px-3 py-1 rounded transition">
            Salir
          </button>
        </div>
      </header>

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 text-gray-800">
            <h2 className="text-lg font-bold mb-4">Cambiar contraseña</h2>
            <div className="flex flex-col gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña actual</label>
                <input type="password" value={actual} onChange={(e) => setActual(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nueva contraseña</label>
                <input type="password" value={nueva} onChange={(e) => setNueva(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar nueva contraseña</label>
                <input type="password" value={repite} onChange={(e) => setRepite(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue" />
              </div>
              {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
              {ok && <p className="text-sm text-green-700 bg-green-50 px-3 py-2 rounded">{ok}</p>}
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setModal(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Cerrar
              </button>
              <button onClick={cambiar} disabled={guardando}
                className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
                {guardando ? 'Guardando...' : 'Cambiar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
