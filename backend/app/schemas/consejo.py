from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ConsejoCreate(BaseModel):
    periodo_id: int
    fecha_consejo: date
    # Fecha límite para tener los informes listos. Va 2 días ANTES del consejo
    # (los informes deben estar antes de la reunión). Si no se envía, el backend
    # la calcula sola; se puede enviar otra para cambiarla.
    fecha_limite_informe: Optional[date] = None
    fecha_activacion: Optional[date] = None


class ConsejoUpdate(BaseModel):
    fecha_consejo: Optional[date] = None
    fecha_limite_informe: Optional[date] = None
    fecha_activacion: Optional[date] = None
    flujo_estado: Optional[str] = None


class ConsejoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    periodo_id: int
    fecha_consejo: date
    fecha_limite_informe: date
    fecha_activacion: Optional[date]
    flujo_estado: str
