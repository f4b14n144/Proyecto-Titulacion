/**
 * Avatar del usuario: su foto, o sus iniciales si no ha subido ninguna.
 *
 * La foto llega como data URI dentro de /auth/me, así que se puede poner
 * directamente en el `src` — no hace falta descargarla aparte con el token.
 */
interface Props {
  nombre: string
  foto?: string | null
  /** Lado del avatar en píxeles */
  tamano?: number
  className?: string
}

/** "Marcelo Esteban Flores Vazquez" → "MF" */
function iniciales(nombre: string): string {
  const palabras = nombre.trim().split(/\s+/).filter(Boolean)
  if (palabras.length === 0) return '?'
  if (palabras.length === 1) return palabras[0].slice(0, 2).toUpperCase()
  return (palabras[0][0] + palabras[palabras.length - 1][0]).toUpperCase()
}

export default function Avatar({ nombre, foto, tamano = 36, className = '' }: Props) {
  const estilo = { width: tamano, height: tamano }

  if (foto) {
    return (
      <img
        src={foto}
        alt={nombre}
        style={estilo}
        className={`rounded-full object-cover border-2 border-white/40 ${className}`}
      />
    )
  }

  return (
    <div
      style={{ ...estilo, fontSize: tamano * 0.38 }}
      className={`rounded-full bg-white/25 border-2 border-white/40 flex items-center justify-center
                  font-bold text-white select-none ${className}`}
      title={nombre}
    >
      {iniciales(nombre)}
    </div>
  )
}
