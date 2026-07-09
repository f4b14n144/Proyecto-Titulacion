import AportesPorMateria from './AportesPorMateria'

export default function DocenteAccionesMejora() {
  return (
    <AportesPorMateria
      tipo="ACCION_MEJORA"
      titulo="Acciones de mejora por materia"
      subtitulo="Recomendaciones orientadas al fortalecimiento del proceso de enseñanza-aprendizaje"
      etiquetaCampo="Nueva acción de mejora"
      placeholder="Ej. Incorporar tutorías de refuerzo antes del segundo parcial; añadir rúbrica al proyecto final..."
    />
  )
}
