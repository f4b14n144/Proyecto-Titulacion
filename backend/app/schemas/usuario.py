from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class UsuarioCreate(BaseModel):
    nombre_completo: str
    email_institucional: EmailStr
    password: str
    rol_id: int


class UsuarioUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    email_institucional: Optional[EmailStr] = None
    password: Optional[str] = None
    rol_id: Optional[int] = None
    activo: Optional[bool] = None


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_completo: str
    email_institucional: str
    rol_id: int
    activo: bool
    # Rol con el que opera realmente (DIRECTOR/JEFE_AREA por jefatura activa/DOCENTE)
    rol_efectivo: Optional[str] = None


class RolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
