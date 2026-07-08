// Renderiza el contenido de un informe (contenido_json) de forma legible para preview.
type Dict = Record<string, unknown>

const SUB_ANALISIS_LABEL: Record<string, string> = {
  analisis_general: 'Análisis general',
  distribucion_aprobacion: 'Distribución aprobación/reprobación',
  comportamiento_notas_finales: 'Comportamiento notas finales',
  analisis_parcial1: 'Análisis Parcial 1',
  analisis_parcial2: 'Análisis Parcial 2',
  comparacion_parciales: 'Comparación entre parciales',
  uso_recuperacion: 'Uso de recuperación',
  relacion_parciales_nota_final: 'Relación parciales–nota final',
  outliers: 'Outliers',
  patrones_generales: 'Patrones generales',
  acciones_mejora: 'Acciones de mejora',
  observaciones_materia: 'Observaciones de la materia (docente)',
}

const SECCION_LABEL: Record<string, string> = {
  agenda: '1. Agenda tratada',
  designaciones: '2. Designaciones de Jefes de Área',
  observaciones_curriculares: '3. Observaciones curriculares',
  resultados_encuestas: '4. Resultados de encuestas',
  resoluciones: '5. Resoluciones y compromisos',
  observaciones_adicionales: '6. Observaciones adicionales',
}

function Texto({ children }: { children: unknown }) {
  const t = String(children ?? '').trim()
  if (!t) return <p className="text-gray-400 italic text-sm">— sin contenido —</p>
  return <p className="text-sm text-gray-700 whitespace-pre-line">{t}</p>
}

export default function PreviewInforme({ tipo, contenido }: { tipo: number; contenido: Dict }) {
  const secciones = (contenido.secciones as Dict) ?? {}
  const interciclo = (contenido.calificaciones_interciclo as Dict[]) ?? []
  const finales = (contenido.calificaciones_finales as Dict[]) ?? []

  return (
    <div className="space-y-5">
      {/* Metadatos */}
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm bg-gray-50 rounded-lg px-4 py-3">
        {contenido.periodo_nombre ? <span><b>Período:</b> {String(contenido.periodo_nombre)}</span> : null}
        {contenido.area_nombre ? <span><b>Área:</b> {String(contenido.area_nombre)}</span> : null}
        {contenido.fecha_consejo ? <span><b>Consejo:</b> {String(contenido.fecha_consejo)}</span> : null}
      </div>

      {/* Informe 1: secciones del formulario */}
      {tipo === 1 && (
        <div className="space-y-3">
          {Object.entries(SECCION_LABEL).map(([k, label]) => (
            <div key={k}>
              <h4 className="font-semibold text-gray-800 text-sm mb-1">{label}</h4>
              <Texto>{secciones[k]}</Texto>
            </div>
          ))}
          {contenido.nombre_director ? (
            <p className="text-sm text-gray-600 pt-2">Director/a: <b>{String(contenido.nombre_director)}</b></p>
          ) : null}
        </div>
      )}

      {/* Informe 3: calificaciones interciclo */}
      {interciclo.length > 0 && (
        <div className="space-y-4">
          <h3 className="font-bold text-gray-800">Análisis Interciclo</h3>
          {interciclo.map((c, i) => (
            <div key={i} className="border rounded-lg p-3">
              <p className="font-semibold text-ups-blue">{String(c.asignatura)} — Grupo {String(c.grupo)}</p>
              <div className="flex flex-wrap gap-x-4 text-xs text-gray-500 my-1">
                <span>Estudiantes: {String(c.total_estudiantes ?? '—')}</span>
                <span>Promedio: {String(c.promedio ?? '—')}/50</span>
                <span>Alto: {String(c.rango_alto ?? '—')}</span>
                <span>Medio: {String(c.rango_medio ?? '—')}</span>
                <span>Bajo: {String(c.rango_bajo ?? '—')}</span>
              </div>
              <Texto>{c.analisis_narrativo}</Texto>
            </div>
          ))}
        </div>
      )}

      {/* Informe 4: calificaciones finales */}
      {finales.length > 0 && (
        <div className="space-y-4">
          <h3 className="font-bold text-gray-800">Análisis Final</h3>
          {finales.map((c, i) => (
            <div key={i} className="border rounded-lg p-3 space-y-2">
              <p className="font-semibold text-ups-blue">{String(c.asignatura)} — Grupo {String(c.grupo)} — {String(c.docente)}</p>
              {Object.entries(SUB_ANALISIS_LABEL).map(([k, label]) =>
                c[k] ? (
                  <div key={k}>
                    <h5 className="text-xs font-semibold text-gray-600">{label}</h5>
                    <Texto>{c[k]}</Texto>
                  </div>
                ) : null
              )}
            </div>
          ))}
          {contenido.analisis_consolidado_area ? (
            <div className="border-t pt-3">
              <h3 className="font-bold text-gray-800 mb-1">Consolidado del Área</h3>
              <Texto>{contenido.analisis_consolidado_area}</Texto>
              {contenido.acciones_generales_area ? (
                <div className="mt-2">
                  <h5 className="text-xs font-semibold text-gray-600">Acciones generales</h5>
                  <Texto>{contenido.acciones_generales_area}</Texto>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      {/* Informe 2 u otros: análisis del área si existe */}
      {contenido.analisis_area ? (
        <div>
          <h3 className="font-bold text-gray-800 mb-1">Análisis del área (AVAC)</h3>
          <Texto>{contenido.analisis_area}</Texto>
        </div>
      ) : null}
    </div>
  )
}
