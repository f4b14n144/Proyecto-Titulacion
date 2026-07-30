import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  LayoutDashboard, Users, Calendar, Gavel, Layers, BookOpen,
  ClipboardList, Upload, FileText, Files, ClipboardCheck,
  FileBarChart, MessageSquare, Lightbulb, GraduationCap, Mail,
  PanelLeftClose, PanelLeftOpen, type LucideIcon,
} from 'lucide-react'

type Item = { to: string; label: string; icon: LucideIcon; exact?: boolean }
type Grupo = { titulo: string | null; items: Item[] }

const directorGroups: Grupo[] = [
  { titulo: null, items: [
    { to: '/director', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  ]},
  { titulo: 'Administración', items: [
    { to: '/director/usuarios', label: 'Usuarios', icon: Users },
    { to: '/director/periodos', label: 'Períodos', icon: Calendar },
    { to: '/director/consejos', label: 'Consejos de Carrera', icon: Gavel },
    { to: '/director/areas', label: 'Áreas', icon: Layers },
  ]},
  { titulo: 'Académico', items: [
    { to: '/director/asignaturas', label: 'Asignaturas', icon: BookOpen },
    { to: '/director/asignaciones', label: 'Asignaciones docente', icon: ClipboardList },
    { to: '/director/calificaciones', label: 'Subir Calificaciones', icon: Upload },
    { to: '/director/estudiantes', label: 'Estudiantes del período', icon: GraduationCap },
  ]},
  { titulo: 'Informes', items: [
    { to: '/director/informe1', label: 'Informe 1', icon: FileText },
    { to: '/director/informes', label: 'Ver Informes', icon: Files },
  ]},
  { titulo: 'Comunicación', items: [
    { to: '/director/correos', label: 'Enviar correos', icon: Mail },
  ]},
]

const jefeGroups: Grupo[] = [
  { titulo: null, items: [
    { to: '/jefe', label: 'Dashboard', icon: LayoutDashboard, exact: true },
    { to: '/jefe/calificaciones', label: 'Subir Calificaciones', icon: Upload },
  ]},
  { titulo: 'Informes', items: [
    { to: '/jefe/informe1', label: 'Informe 1 — Centro Docente', icon: FileText },
    { to: '/jefe/informe2', label: 'Informe 2 — AVAC', icon: ClipboardCheck },
    { to: '/jefe/informe3', label: 'Informe 3 — Visitas', icon: ClipboardList },
    { to: '/jefe/informe4', label: 'Informe 4 — Final', icon: FileBarChart },
    { to: '/jefe/informes', label: 'Ver y editar informes', icon: Files },
  ]},
  { titulo: 'Comunicación', items: [
    { to: '/jefe/correos', label: 'Enviar correos', icon: Mail },
  ]},
]

// El docente no sube notas: consulta sus materias y registra aportes por materia
const docenteGroups: Grupo[] = [
  { titulo: null, items: [
    { to: '/docente', label: 'Mis materias', icon: LayoutDashboard, exact: true },
    { to: '/docente/acciones-mejora', label: 'Acciones de mejora', icon: Lightbulb },
    { to: '/docente/observaciones', label: 'Observaciones', icon: MessageSquare },
  ]},
]

// El menú va expandido por defecto (así se ve en móvil); solo se contrae en
// computadora (prefijo `md:`) cuando el usuario lo colapsa.
const linkClass = (colapsado: boolean) => ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2.5 py-2 rounded-lg text-sm transition px-3 ${
    colapsado ? 'md:px-2.5 md:justify-center' : ''
  } ${
    isActive
      ? 'bg-ups-blue text-white font-medium shadow-sm'
      : 'text-gray-700 hover:bg-gray-100'
  }`

const CLAVE_COLAPSADO = 'sidebar_colapsado'

interface SidebarProps {
  /** En móvil: ¿el panel deslizante está abierto? (en desktop se ignora) */
  abiertoMovil?: boolean
  /** Cerrar el panel móvil (al tocar el fondo o navegar) */
  onCerrar?: () => void
}

export default function Sidebar({ abiertoMovil = false, onCerrar }: SidebarProps) {
  const { user } = useAuth()
  // Colapsable para recuperar ancho en monitores de baja resolución.
  // La preferencia se recuerda entre sesiones; si no hay ninguna guardada,
  // arranca colapsado en pantallas estrechas.
  const [colapsado, setColapsado] = useState(() => {
    const guardado = localStorage.getItem(CLAVE_COLAPSADO)
    if (guardado !== null) return guardado === '1'
    // En monitores de baja resolución (1366x768 y similares) el menú expandido
    // se come 240px que las tablas necesitan. Arranca colapsado; el usuario puede
    // expandirlo y su preferencia queda guardada.
    return window.innerWidth < 1440
  })

  useEffect(() => {
    localStorage.setItem(CLAVE_COLAPSADO, colapsado ? '1' : '0')
  }, [colapsado])

  const grupos =
    user?.rol === 'DIRECTOR_CARRERA' ? directorGroups
    : user?.rol === 'JEFE_AREA' ? jefeGroups
    : docenteGroups

  return (
    <>
      {/* Fondo oscuro en móvil cuando el menú está abierto (toca para cerrar) */}
      {abiertoMovil && (
        <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={onCerrar} />
      )}

      <aside
        className={`bg-white border-r py-4 overflow-y-auto overflow-x-hidden z-40
                    fixed inset-y-0 left-0 w-60 transition-transform duration-200
                    md:static md:h-full md:flex-shrink-0 md:z-auto md:translate-x-0 md:transition-[width]
                    ${abiertoMovil ? 'translate-x-0' : '-translate-x-full'}
                    ${colapsado ? 'md:w-16' : 'md:w-60'}`}
      >
        {/* Botón para contraer: solo en computadora (en móvil el menú es deslizante) */}
        <div className={`px-3 mb-2 hidden md:flex ${colapsado ? 'justify-center' : 'justify-end'}`}>
          <button
            type="button"
            onClick={() => setColapsado(!colapsado)}
            title={colapsado ? 'Expandir menú' : 'Contraer menú'}
            aria-label={colapsado ? 'Expandir menú' : 'Contraer menú'}
            className="text-gray-400 hover:text-ups-blue hover:bg-gray-100 rounded-lg p-1.5 transition"
          >
            {colapsado ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

      <nav className="flex flex-col gap-1 px-3">
        {grupos.map((grupo, i) => (
          <div key={i} className={grupo.titulo ? 'mt-4' : ''}>
            {grupo.titulo && (
              <p className={`px-3 mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400 ${colapsado ? 'md:hidden' : ''}`}>
                {grupo.titulo}
              </p>
            )}
            {grupo.titulo && colapsado && <div className="hidden md:block border-t my-3 mx-1" />}
            <div className="flex flex-col gap-0.5">
              {grupo.items.map((it) => {
                const Icon = it.icon
                return (
                  <NavLink
                    key={it.to}
                    to={it.to}
                    end={it.exact}
                    onClick={onCerrar}
                    className={linkClass(colapsado)}
                    title={colapsado ? it.label : undefined}
                  >
                    <Icon size={18} strokeWidth={1.9} className="flex-shrink-0" />
                    <span className={`whitespace-nowrap ${colapsado ? 'md:hidden' : ''}`}>{it.label}</span>
                  </NavLink>
                )
              })}
            </div>
          </div>
        ))}
      </nav>
      </aside>
    </>
  )
}
