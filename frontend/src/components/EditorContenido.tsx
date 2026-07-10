import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

type Json = string | number | boolean | null | Json[] | { [k: string]: Json }

interface Props {
  valor: Json
  onChange: (nuevo: Json) => void
  /** Ruta de claves hasta este nodo; se usa para las etiquetas y las keys de React */
  ruta?: string[]
}

/** Etiquetas legibles para las claves técnicas del contenido_json. */
const ETIQUETAS: Record<string, string> = {
  agenda: 'Agenda tratada en la reunión',
  designaciones: 'Designaciones de Jefes de Área',
  observaciones_curriculares: 'Observaciones curriculares de docentes',
  resultados_encuestas: 'Resultados de encuestas estudiantiles',
  resoluciones: 'Resoluciones y compromisos',
  observaciones_adicionales: 'Observaciones adicionales',
  secciones: 'Aporte del área',
  secciones_direccion: 'Contenido de la Dirección',
  periodo_nombre: 'Período',
  periodo_numero: 'Número de período',
  carreras_texto: 'Texto de carreras (carátula)',
  area_nombre: 'Área',
  jefe_nombre: 'Nombre del Jefe de Área',
  jefe_titulo: 'Título del Jefe de Área',
  nombre_director: 'Nombre del/la Director/a',
  fecha_consejo: 'Fecha del Consejo',
  fecha_informe: 'Fecha del informe',
  visitas: 'Visitas áulicas',
  checklists: 'Checklist AVAC',
  calificaciones_interciclo: 'Calificaciones — Interciclo',
  calificaciones_finales: 'Calificaciones — Finales',
  analisis_consolidado_area: 'Análisis consolidado del área',
  acciones_generales_area: 'Acciones generales del área',
  analisis_area: 'Análisis de cumplimiento del área',
  asignatura: 'Asignatura',
  docente: 'Docente',
  grupo: 'Grupo',
  observaciones_materia: 'Observaciones del docente a la materia',
  acciones_mejora_docente: 'Acciones de mejora propuestas por el docente',
  acciones_docente: 'Acciones de mejora del jefe de área al docente',
  acciones_mejora: 'Acciones de mejora',
  analisis_narrativo: 'Análisis narrativo',
}

const etiqueta = (clave: string) =>
  ETIQUETAS[clave] ??
  clave.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())

/** Los textos largos van en textarea; los cortos en input. */
const ES_TEXTO_LARGO = (clave: string, valor: string) =>
  valor.length > 80 ||
  /analisis|acciones|observacion|conclusion|agenda|resolucion|designacion|narrativ|patron|comparacion|distribucion|outlier|uso_|relacion/i.test(
    clave,
  )

export default function EditorContenido({ valor, onChange, ruta = [] }: Props) {
  // Valores primitivos
  if (valor === null) return null

  if (typeof valor === 'boolean') {
    return (
      <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
        <input
          type="checkbox"
          checked={valor}
          onChange={(e) => onChange(e.target.checked)}
          className="w-4 h-4 accent-ups-blue"
        />
        {valor ? 'Sí' : 'No'}
      </label>
    )
  }

  if (typeof valor === 'number') {
    return (
      <input
        type="number"
        value={valor}
        onChange={(e) => onChange(e.target.value === '' ? 0 : Number(e.target.value))}
        className="w-40 border rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ups-blue"
      />
    )
  }

  if (typeof valor === 'string') {
    const clave = ruta[ruta.length - 1] ?? ''
    return ES_TEXTO_LARGO(clave, valor) ? (
      <textarea
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ups-blue resize-y"
      />
    ) : (
      <input
        type="text"
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ups-blue"
      />
    )
  }

  // Listas: cada elemento en su propia tarjeta
  if (Array.isArray(valor)) {
    if (valor.length === 0) {
      return <p className="text-xs text-gray-400 italic">Sin elementos.</p>
    }
    return (
      <div className="space-y-3">
        {valor.map((item, i) => (
          <div key={i} className="border rounded-lg bg-gray-50/60">
            <div className="px-3 py-1.5 border-b bg-gray-50 text-xs font-medium text-gray-500">
              {resumenItem(item, i)}
            </div>
            <div className="p-3">
              <EditorContenido
                valor={item}
                ruta={[...ruta, String(i)]}
                onChange={(nuevo) => {
                  const copia = [...valor]
                  copia[i] = nuevo
                  onChange(copia)
                }}
              />
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Objetos: una sección plegable por clave compuesta
  return (
    <div className="space-y-3">
      {Object.entries(valor).map(([clave, sub]) => (
        <Campo
          key={clave}
          clave={clave}
          valor={sub}
          ruta={[...ruta, clave]}
          onChange={(nuevo) => onChange({ ...valor, [clave]: nuevo })}
        />
      ))}
    </div>
  )
}

/** Título corto para identificar un elemento de una lista. */
function resumenItem(item: Json, i: number): string {
  if (item && typeof item === 'object' && !Array.isArray(item)) {
    const o = item as Record<string, Json>
    const partes = [o.asignatura, o.grupo, o.docente].filter(Boolean)
    if (partes.length) return partes.join(' — ')
  }
  return `Elemento ${i + 1}`
}

function esCompuesto(v: Json): boolean {
  return v !== null && typeof v === 'object'
}

function Campo({
  clave, valor, onChange, ruta,
}: { clave: string; valor: Json; onChange: (n: Json) => void; ruta: string[] }) {
  const [abierto, setAbierto] = useState(true)

  if (valor === null) return null

  // Los compuestos (objetos/listas) van en un bloque plegable
  if (esCompuesto(valor)) {
    const vacio = Array.isArray(valor) && valor.length === 0
    return (
      <div className="border rounded-xl overflow-hidden bg-white">
        <button
          type="button"
          onClick={() => setAbierto(!abierto)}
          className="w-full flex items-center gap-2 px-4 py-2.5 bg-gray-50 border-b hover:bg-gray-100 transition text-left"
        >
          {abierto ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
          <span className="text-sm font-semibold text-gray-700">{etiqueta(clave)}</span>
          {Array.isArray(valor) && (
            <span className="ml-auto text-xs text-gray-400">{valor.length} elemento(s)</span>
          )}
        </button>
        {abierto && !vacio && (
          <div className="p-4">
            <EditorContenido valor={valor} ruta={ruta} onChange={onChange} />
          </div>
        )}
        {abierto && vacio && (
          <p className="px-4 py-3 text-xs text-gray-400">Sin elementos.</p>
        )}
      </div>
    )
  }

  // Primitivos: etiqueta + control
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{etiqueta(clave)}</label>
      <EditorContenido valor={valor} ruta={ruta} onChange={onChange} />
    </div>
  )
}
