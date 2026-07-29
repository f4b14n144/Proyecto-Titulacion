from typing import Optional
from pydantic import BaseModel, ConfigDict


class AsignaturaCreate(BaseModel):
    area_id: int
    nombre: str
    codigo: str


class AsignaturaUpdate(BaseModel):
    area_id: Optional[int] = None
    nombre: Optional[str] = None
    codigo: Optional[str] = None


class AsignaturaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    area_id: int
    nombre: str
    codigo: str
    activa: bool = True
