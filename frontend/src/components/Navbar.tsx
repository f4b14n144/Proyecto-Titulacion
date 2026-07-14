import { useAuth } from '../hooks/useAuth'
import { useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import Avatar from './Avatar'

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
        <img src="/logo_ups.png" alt="UPS"
          className="w-9 h-9 object-contain bg-white rounded-full p-0.5" />
        <span className="font-bold text-lg tracking-wide">Sistema Informes UPS</span>
        <span className="text-xs bg-white/20 px-2 py-0.5 rounded">Carrera de Computación</span>
      </div>

      <div className="flex items-center gap-3 text-sm">
        {/* El avatar y el nombre son el acceso a la cuenta: donde antes estaba
            "Cambiar contraseña", que ahora es una sección más dentro de la página. */}
        <button
          onClick={() => navigate('/mi-cuenta')}
          title="Editar mi cuenta"
          className="flex items-center gap-3 hover:bg-white/10 pl-2 pr-3 py-1 rounded-lg transition"
        >
          {user && <Avatar nombre={user.nombre_completo} foto={user.foto} tamano={32} />}
          <span className="flex flex-col items-start leading-tight">
            <span className="whitespace-nowrap">{user?.nombre_completo}</span>
            <span className="text-xs text-white/70">{user?.rol?.replace('_', ' ')}</span>
          </span>
        </button>

        <button
          onClick={handleLogout}
          className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition"
        >
          <LogOut size={15} /> Salir
        </button>
      </div>
    </header>
  )
}
