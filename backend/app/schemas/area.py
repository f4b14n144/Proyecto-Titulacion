from pydantic import BaseModel, ConfigDict


class AreaCreate(BaseModel):
    nombre: str


class AreaUpdate(BaseModel):
    nombre: str


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
