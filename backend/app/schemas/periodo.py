from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator


class PeriodoCreate(BaseModel):
    nombre: str
    fecha_inicio: date
    fecha_fin: date
    activo: bool = True

    @model_validator(mode="after")
    def validar_fechas(self):
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
        return self


class PeriodoUpdate(BaseModel):
    nombre: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    activo: Optional[bool] = None


class PeriodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    fecha_inicio: date
    fecha_fin: date
    activo: bool
