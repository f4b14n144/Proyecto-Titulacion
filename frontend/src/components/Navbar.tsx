import { useAuth } from '../hooks/useAuth'
import { useNavigate } from 'react-router-dom'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="bg-ups-blue text-white h-14 flex items-center justify-between px-6 shadow">
      <div className="flex items-center gap-3">
        <span className="font-bold text-lg tracking-wide">Sistema Informes UPS</span>
        <span className="text-xs bg-white/20 px-2 py-0.5 rounded">Carrera de Computación</span>
      </div>
      <div className="flex items-center gap-4 text-sm">
        <span>{user?.nombre_completo}</span>
        <span className="bg-white/20 px-2 py-0.5 rounded text-xs">{user?.rol?.replace('_', ' ')}</span>
        <button
          onClick={handleLogout}
          className="bg-white/10 hover:bg-white/20 px-3 py-1 rounded transition"
        >
          Salir
        </button>
      </div>
    </header>
  )
}
