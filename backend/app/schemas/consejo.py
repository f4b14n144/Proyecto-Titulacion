from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator


class ConsejoCreate(BaseModel):
    periodo_id: int
    fecha_consejo: date
    fecha_limite_informe: date
    fecha_activacion: Optional[date] = None

    @model_validator(mode="after")
    def validar_fechas(self):
        if self.fecha_limite_informe < self.fecha_consejo:
            raise ValueError("fecha_limite_informe no puede ser anterior a fecha_consejo")
        if self.fecha_activacion and self.fecha_activacion > self.fecha_limite_informe:
            raise ValueError("fecha_activacion no puede ser posterior a fecha_limite_informe")
        return self


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
