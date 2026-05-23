export function formatFecha(iso: string): string {
  return new Date(iso).toLocaleDateString('es-EC', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export function formatEstado(estado: string): string {
  const mapa: Record<string, string> = {
    BORRADOR: 'Borrador',
    REVISANDO: 'En revisión',
    APROBADO: 'Aprobado',
    PENDIENTE: 'Pendiente',
    PROCESANDO: 'Procesando',
    COMPLETADO: 'Completado',
    ERROR: 'Error',
  }
  return mapa[estado] ?? estado
}
