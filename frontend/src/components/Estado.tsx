import { AlertTriangle, Inbox } from 'lucide-react'

/** Spinner de carga centrado. Mismo aspecto en todas las pantallas. */
export function Cargando({ texto = 'Cargando…' }: { texto?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12" role="status">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
      <p className="text-sm text-gray-500">{texto}</p>
    </div>
  )
}

/**
 * Mensaje de error. Si se pasa `onReintentar`, ofrece volver a intentarlo.
 * Se llama `MensajeError` y no `Error` para no chocar con el Error nativo de JS.
 */
export function MensajeError({ mensaje, onReintentar }: { mensaje: string; onReintentar?: () => void }) {
  return (
    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm
                    flex items-center gap-2" role="alert">
      <AlertTriangle size={16} className="flex-shrink-0" />
      <span className="flex-1">{mensaje}</span>
      {onReintentar && (
        <button onClick={onReintentar} className="font-medium underline hover:no-underline">
          Reintentar
        </button>
      )}
    </div>
  )
}

/** Estado vacío: no hubo error, simplemente no hay datos que mostrar. */
export function Vacio({ mensaje }: { mensaje: string }) {
  return (
    <div className="bg-white rounded-xl border p-10 text-center">
      <Inbox size={28} className="mx-auto text-gray-300 mb-2" />
      <p className="text-sm text-gray-400 max-w-md mx-auto">{mensaje}</p>
    </div>
  )
}
