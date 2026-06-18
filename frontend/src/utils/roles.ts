// Utilidades de roles/navegación (separado de App.tsx para no romper React Fast Refresh)

/** Ruta del panel inicial según el rol del usuario. */
export function destinoPorRol(rol?: string): string {
  if (rol === 'DIRECTOR_CARRERA') return '/director'
  if (rol === 'JEFE_AREA') return '/jefe'
  return '/docente'
}
