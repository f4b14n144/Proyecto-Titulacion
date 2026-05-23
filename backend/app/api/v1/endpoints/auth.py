from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.core.security import verify_password, create_access_token, create_refresh_token, verify_token
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, MeResponse

router = APIRouter()


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
def me(current_user: Usuario = Depends(get_current_user)):
    return MeResponse(
        id=current_user.id,
        nombre_completo=current_user.nombre_completo,
        email_institucional=current_user.email_institucional,
        rol=current_user.rol.nombre,
        activo=current_user.activo,
    )
