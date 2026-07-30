import { useAuth } from '../hooks/useAuth'
import { useNavigate } from 'react-router-dom'
import { LogOut, Menu } from 'lucide-react'
import Avatar from './Avatar'

interface NavbarProps {
  /** Abre el menú lateral en móvil (en computadora el menú está siempre visible) */
  onAbrirMenu?: () => void
}

export default function Navbar({ onAbrirMenu }: NavbarProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="bg-ups-blue text-white h-14 flex items-center justify-between px-4 md:px-6 shadow">
      <div className="flex items-center gap-2 md:gap-3 min-w-0">
        {/* Botón de menú: solo en móvil (en computadora el menú está fijo a la izquierda) */}
        <button
          onClick={onAbrirMenu}
          className="md:hidden p-1.5 -ml-1 hover:bg-white/10 rounded-lg shrink-0"
          aria-label="Abrir menú"
        >
          <Menu size={22} />
        </button>
        <img src="/logo_ups.png" alt="UPS"
          className="w-9 h-9 object-contain bg-white rounded-full p-0.5 shrink-0" />
        <span className="font-bold text-base md:text-lg tracking-wide truncate">Sistema Informes UPS</span>
        <span className="hidden lg:inline text-xs bg-white/20 px-2 py-0.5 rounded whitespace-nowrap">
          Carrera de Computación
        </span>
      </div>

      <div className="flex items-center gap-2 md:gap-3 text-sm shrink-0">
        {/* Avatar + nombre = acceso a la cuenta. El nombre se oculta en móvil, queda el avatar. */}
        <button
          onClick={() => navigate('/mi-cuenta')}
          title="Editar mi cuenta"
          className="flex items-center gap-2 md:gap-3 hover:bg-white/10 pl-1 md:pl-2 pr-1 md:pr-3 py-1 rounded-lg transition"
        >
          {user && <Avatar nombre={user.nombre_completo} foto={user.foto} tamano={32} />}
          <span className="hidden sm:flex flex-col items-start leading-tight">
            <span className="whitespace-nowrap">{user?.nombre_completo}</span>
            <span className="text-xs text-white/70">{user?.rol?.replace('_', ' ')}</span>
          </span>
        </button>

        <button
          onClick={handleLogout}
          className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 px-2 md:px-3 py-1.5 rounded-lg transition"
        >
          <LogOut size={15} /> <span className="hidden sm:inline">Salir</span>
        </button>
      </div>
    </header>
  )
}
