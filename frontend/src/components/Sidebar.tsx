import { NavLink } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const directorLinks = [
  { to: '/director', label: 'Dashboard', exact: true },
  { to: '/director/usuarios', label: 'Usuarios' },
  { to: '/director/periodos', label: 'Períodos' },
  { to: '/director/consejos', label: 'Consejos de Carrera' },
  { to: '/director/areas', label: 'Áreas' },
  { to: '/director/asignaturas', label: 'Asignaturas' },
  { to: '/director/asignaciones', label: 'Asignaciones docente' },
  { to: '/director/calificaciones', label: 'Subir Calificaciones' },
  { to: '/director/informe1', label: 'Informe 1' },
  { to: '/director/informes', label: 'Ver Informes' },
]

const jefeLinks = [
  { to: '/jefe', label: 'Dashboard', exact: true },
  { to: '/jefe/informe1', label: 'Informe 1 — Centro Docente' },
  { to: '/jefe/informe2', label: 'Informe 2 — AVAC' },
  { to: '/jefe/informe3', label: 'Informe 3 — Visitas' },
  { to: '/jefe/informe4', label: 'Informe 4 — Final' },
]

const docenteLinks = [
  { to: '/docente', label: 'Dashboard', exact: true },
]

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `block px-4 py-2 rounded text-sm transition ${
    isActive
      ? 'bg-ups-blue text-white font-medium'
      : 'text-gray-700 hover:bg-gray-100'
  }`

export default function Sidebar() {
  const { user } = useAuth()
  const links =
    user?.rol === 'DIRECTOR_CARRERA' ? directorLinks
    : user?.rol === 'JEFE_AREA' ? jefeLinks
    : docenteLinks

  return (
    <aside className="w-56 bg-white border-r h-full flex-shrink-0 py-4">
      <nav className="flex flex-col gap-1 px-2">
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.exact} className={linkClass}>
            {l.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
