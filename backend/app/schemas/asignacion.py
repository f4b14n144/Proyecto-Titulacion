from pydantic import BaseModel, ConfigDict


class AsignacionCreate(BaseModel):
    usuario_id: int
    asignatura_id: int
    periodo_id: int
    grupo: str


class AsignacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    asignatura_id: int
    periodo_id: int
    grupo: str
