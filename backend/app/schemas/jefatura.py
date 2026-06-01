from pydantic import BaseModel, ConfigDict


class JefaturaCreate(BaseModel):
    usuario_id: int
    area_id: int
    periodo_id: int


class JefaturaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    area_id: int
    periodo_id: int
