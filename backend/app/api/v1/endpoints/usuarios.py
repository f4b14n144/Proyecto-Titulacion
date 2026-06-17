from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_role
from app.core.security import hash_password
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioOut, RolOut

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")  # lectura compartida (nombres docentes)


@router.get("/", response_model=dict)
def listar_usuarios(
    activo: Optional[bool] = Query(None),
    rol_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_director_o_jefe),
):
    q = db.query(Usuario)
    if activo is not None:
        q = q.filter(Usuario.activo == activo)
    if rol_id is not None:
        q = q.filter(Usuario.rol_id == rol_id)
    usuarios = q.all()
    return {"data": [UsuarioOut.model_validate(u) for u in usuarios], "message": "OK", "success": True}


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    if db.query(Usuario).filter(Usuario.email_institucional == payload.email_institucional).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    if not db.query(Rol).filter(Rol.id == payload.rol_id).first():
        raise HTTPException(status_code=400, detail="Rol no existe")

    nuevo = Usuario(
        nombre_completo=payload.nombre_completo,
        email_institucional=payload.email_institucional,
        hashed_password=hash_password(payload.password),
        rol_id=payload.rol_id,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {"data": UsuarioOut.model_validate(nuevo), "message": "Usuario creado", "success": True}


@router.get("/{usuario_id}", response_model=dict)
def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"data": UsuarioOut.model_validate(usuario), "message": "OK", "success": True}


@router.put("/{usuario_id}", response_model=dict)
def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if payload.nombre_completo is not None:
        usuario.nombre_completo = payload.nombre_completo
    if payload.email_institucional is not None:
        usuario.email_institucional = payload.email_institucional
    if payload.password is not None:
        usuario.hashed_password = hash_password(payload.password)
    if payload.rol_id is not None:
        if not db.query(Rol).filter(Rol.id == payload.rol_id).first():
            raise HTTPException(status_code=400, detail="Rol no existe")
        usuario.rol_id = payload.rol_id
    if payload.activo is not None:
        usuario.activo = payload.activo

    db.commit()
    db.refresh(usuario)
    return {"data": UsuarioOut.model_validate(usuario), "message": "Usuario actualizado", "success": True}


@router.delete("/{usuario_id}", response_model=dict)
def desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuario.activo = False
    db.commit()
    return {"data": None, "message": "Usuario desactivado", "success": True}


@router.get("/roles/lista", response_model=dict)
def listar_roles(
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    roles = db.query(Rol).all()
    return {"data": [RolOut.model_validate(r) for r in roles], "message": "OK", "success": True}
