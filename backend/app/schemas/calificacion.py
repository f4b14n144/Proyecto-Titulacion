from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class EstudianteCalificacion(BaseModel):
    parcial1: Optional[float] = None
    parcial2: Optional[float] = None
    recuperacion: Optional[float] = None
    nota_final: Optional[float] = None
    estado: str = "DESCONOCIDO"
    solo_nota_final: bool = False


class ResultadoAsignatura(BaseModel):
    asignatura_id: int
    asignatura_nombre: str = ""
    grupo: str
    estudiantes: list[EstudianteCalificacion]
    total_estudiantes: int
    columnas_detectadas: list[str]
    advertencias: list[str]
    # El profesor tal como viene en el Excel (columna "Profesor"). Se usa para
    # crear la asignación que falte.
    profesor_excel: str = ""
    # True si esta materia+grupo NO estaba asignada en el sistema y se creará al
    # confirmar (usando el profesor del Excel).
    asignacion_faltante: bool = False


class PreviewCalificaciones(BaseModel):
    """Respuesta del preview antes de confirmar la subida."""
    tipo: str
    consejo_id: int
    resultados: list[ResultadoAsignatura]
    total_asignaturas: int
    advertencias_globales: list[str]


class CalificacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asignatura_id: int
    consejo_id: int
    grupo: Optional[str] = None
    tipo: str
    datos_json: Any
