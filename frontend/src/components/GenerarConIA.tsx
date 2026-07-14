import { useState } from 'react'
import { Sparkles, AlertTriangle } from 'lucide-react'

/**
 * Botón para generar (o regenerar) el contenido del informe con IA.
 *
 * Antes el botón desaparecía en cuanto el informe existía, así que si llegaba un
 * Excel de notas corregido no había forma de rehacer el análisis: el informe se
 * quedaba describiendo los datos viejos.
 *
 * Ahora sigue disponible, pero **regenerar pide confirmación**: el generador
 * reemplaza el `contenido_json` completo, así que se lleva por delante los textos
 * que el usuario haya editado a mano.
 */
interface Props {
  /** ¿Ya existe el informe? Cambia el texto y activa la confirmación. */
  existe: boolean
  generando: boolean
  onGenerar: () => void
  /** Qué se conserva al regenerar, si algo (informes 2 y 3). */
  nota?: string
}

export default function GenerarConIA({ existe, generando, onGenerar, nota }: Props) {
  const [confirmar, setConfirmar] = useState(false)

  const pulsar = () => {
    if (existe) setConfirmar(true)
    else onGenerar()
  }

  const aceptar = () => {
    setConfirmar(false)
    onGenerar()
  }

  return (
    <>
      <button
        onClick={pulsar}
        disabled={generando}
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                    disabled:opacity-60 ${existe
                      ? 'border border-ups-blue text-ups-blue hover:bg-ups-blue hover:text-white transition'
                      : 'bg-ups-blue text-white hover:bg-blue-800'}`}
      >
        <Sparkles size={16} />
        {generando
          ? 'Iniciando IA...'
          : existe ? 'Regenerar con IA' : 'Generar borrador con IA'}
      </button>

      {confirmar && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-start gap-3 mb-4">
              <div className="bg-amber-100 text-amber-600 rounded-full p-2 shrink-0">
                <AlertTriangle size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-800">Regenerar con IA</h2>
                <p className="text-sm text-gray-600 mt-1">
                  La IA volverá a escribir el análisis a partir de las calificaciones
                  que hay ahora mismo cargadas.
                </p>
              </div>
            </div>

            <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <strong>Se perderán los textos que hayas editado a mano</strong> en este informe.
            </p>
            {nota && <p className="text-xs text-gray-500 mt-2">{nota}</p>}

            <div className="flex justify-end gap-2 mt-5">
              <button
                onClick={() => setConfirmar(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancelar
              </button>
              <button
                onClick={aceptar}
                className="bg-ups-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800"
              >
                Sí, regenerar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
