from app.db.declarative import Base  # noqa: F401 — re-export para Alembic

# Importar todos los modelos para que Alembic los detecte en autogenerate
from app.models.rol import Rol  # noqa: F401
from app.models.usuario import Usuario  # noqa: F401
from app.models.periodo import PeriodoAcademico  # noqa: F401
from app.models.consejo import ConsejoCarrera  # noqa: F401
from app.models.area import Area  # noqa: F401
from app.models.asignatura import Asignatura  # noqa: F401
from app.models.jefatura import JefaturaArea  # noqa: F401
from app.models.asignacion import AsignacionDocente  # noqa: F401
from app.models.calificacion import Calificacion  # noqa: F401
from app.models.informe import Informe  # noqa: F401
from app.models.checklist_avac import ChecklistAVAC  # noqa: F401
from app.models.checklist_visita import ChecklistVisitaAulica  # noqa: F401
from app.models.notificacion import Notificacion  # noqa: F401
from app.models.respuesta_docente import RespuestaDocente  # noqa: F401
from app.models.aporte_docente import AporteDocente  # noqa: F401
from app.models.contenido_consejo import ContenidoConsejo  # noqa: F401
from app.models.estudiante import Estudiante, EstudianteAsignatura  # noqa: F401
