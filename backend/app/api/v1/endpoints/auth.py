from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token, verify_token,
)
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, MeResponse

router = APIRouter()


class CambiarPasswordIn(BaseModel):
    password_actual: str
    password_nueva: str


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(
        Usuario.email_institucional == payload.email,
        Usuario.activo == True,
    ).first()
    if not usuario or not verify_password(payload.password, usuario.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    data = {"sub": str(usuario.id)}
    return TokenResponse(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token(data),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_data = verify_token(payload.refresh_token)
    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")

    usuario = db.query(Usuario).filter(
        Usuario.id == int(token_data["sub"]),
        Usuario.activo == True,
    ).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

    data = {"sub": str(usuario.id)}
    return TokenResponse(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token(data),
    )


@router.get("/me", response_model=MeResponse)
def me(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Área que dirige (si tiene jefatura); el panel del jefe la necesita para
    # generar los informes de su área.
    from app.models.area import Area
    from app.models.jefatura import JefaturaArea

    area_id = None
    area_nombre = None
    jefatura = (
        db.query(JefaturaArea)
        .filter(JefaturaArea.usuario_id == current_user.id)
        .first()
    )
    if jefatura:
        area = db.query(Area).filter(Area.id == jefatura.area_id).first()
        area_id = jefatura.area_id
        area_nombre = area.nombre if area else None

    return MeResponse(
        id=current_user.id,
        nombre_completo=current_user.nombre_completo,
        email_institucional=current_user.email_institucional,
        rol=getattr(current_user, "rol_efectivo", current_user.rol.nombre),
        activo=current_user.activo,
        titulo=current_user.titulo,
        area_id=area_id,
        area_nombre=area_nombre,
    )


@router.post("/cambiar-password", response_model=dict)
def cambiar_password(
    payload: CambiarPasswordIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Permite a cualquier usuario autenticado cambiar su propia contraseña."""
    if not verify_password(payload.password_actual, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
    if len(payload.password_nueva) < 6:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres")
    if payload.password_nueva == payload.password_actual:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser diferente a la actual")

    current_user.hashed_password = hash_password(payload.password_nueva)
    db.commit()
    return {"data": None, "message": "Contraseña actualizada correctamente", "success": True}
