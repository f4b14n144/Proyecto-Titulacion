from typing import Optional
from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_completo: str
    email_institucional: str
    rol: str
    activo: bool
    titulo: Optional[str] = None
    # Área que dirige, si es jefe de área. Los paneles del jefe la usan para
    # generar sus informes (antes mandaban area_id=0, que daba 403).
    area_id: Optional[int] = None
    area_nombre: Optional[str] = None
