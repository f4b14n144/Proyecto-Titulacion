import AportesPorMateria from './AportesPorMateria'

export default function DocenteObservaciones() {
  return (
    <AportesPorMateria
      tipo="OBSERVACION"
      titulo="Observaciones por materia"
      subtitulo="Aspectos relevantes identificados durante el desarrollo de cada asignatura"
      etiquetaCampo="Nueva observación"
      placeholder="Ej. La asistencia disminuyó tras el primer parcial; el laboratorio 3 requiere más tiempo de práctica..."
    />
  )
}
