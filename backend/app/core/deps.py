from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.security import verify_token
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def calcular_rol_efectivo(db: Session, user: Usuario) -> str:
    """
    Rol con el que el usuario opera realmente:
    - DIRECTOR_CARRERA: siempre director.
    - Cualquier otro: es JEFE_AREA solo si tiene una jefatura en un período
      ACTIVO; si no, opera como DOCENTE.
    Así, un docente entra como docente y solo se vuelve jefe cuando se le
    asigna la jefatura del período vigente.
    """
    if user.rol.nombre == "DIRECTOR_CARRERA":
        return "DIRECTOR_CARRERA"

    from app.models.jefatura import JefaturaArea
    from app.models.periodo import PeriodoAcademico
    tiene_jefatura = (
        db.query(JefaturaArea)
        .join(PeriodoAcademico, JefaturaArea.periodo_id == PeriodoAcademico.id)
        .filter(JefaturaArea.usuario_id == user.id, PeriodoAcademico.activo == True)
        .first()
    )
    return "JEFE_AREA" if tiene_jefatura else "DOCENTE"


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> Usuario:
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user = db.query(Usuario).filter(Usuario.id == payload.get("sub")).first()
    if not user or not user.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")
    # Rol efectivo (depende de la jefatura activa), adjunto al objeto para reutilizar
    user.rol_efectivo = calcular_rol_efectivo(db, user)
    return user


def require_role(*roles: str):
    def checker(current_user: Usuario = Depends(get_current_user)):
        rol = getattr(current_user, "rol_efectivo", current_user.rol.nombre)
        if rol not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos para esta acción")
        return current_user
    return checker
