import base64
import io
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token, verify_token,
)
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, MeResponse

router = APIRouter()

# La foto se recorta a un cuadrado de este lado y se recomprime. Con 256px basta
# para el avatar de la barra y para la pantalla de la cuenta, y el JPEG resultante
# pesa ~20 KB, que es lo que acaba viajando en /auth/me.
LADO_FOTO = 256
PESO_MAXIMO_FOTO = 5 * 1024 * 1024   # 5 MB de subida


class CambiarPasswordIn(BaseModel):
    password_actual: str
    password_nueva: str


class PerfilIn(BaseModel):
    nombre_completo: str
    titulo: Optional[str] = None

    @field_validator("nombre_completo")
    @classmethod
    def _nombre_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()

    @field_validator("titulo")
    @classmethod
    def _limpiar_titulo(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v and v.strip() else None


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
        foto=current_user.foto,
        area_id=area_id,
        area_nombre=area_nombre,
    )


@router.put("/perfil", response_model=dict)
def actualizar_perfil(
    payload: PerfilIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    El usuario edita SU propio nombre y título.

    El correo institucional no se toca: lo asigna la universidad y además es la
    credencial con la que se entra. El rol tampoco: depende de las jefaturas y lo
    administra la dirección.
    """
    current_user.nombre_completo = payload.nombre_completo
    current_user.titulo = payload.titulo
    db.commit()
    return {
        "data": {"nombre_completo": current_user.nombre_completo, "titulo": current_user.titulo},
        "message": "Perfil actualizado",
        "success": True,
    }


def _procesar_foto(datos: bytes) -> str:
    """
    Recorta la imagen a un cuadrado centrado, la reduce y la devuelve como data URI.

    Se **reescribe** la imagen con Pillow en lugar de guardar el archivo que sube el
    usuario: así lo que se almacena es un JPEG generado por nosotros, y cualquier
    cosa rara que viniera incrustada en el original no sobrevive al reencodeado.
    """
    from PIL import Image, UnidentifiedImageError

    try:
        imagen = Image.open(io.BytesIO(datos))
        imagen.load()   # fuerza la decodificación aquí, no más tarde
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida")

    imagen = imagen.convert("RGB")

    # Recorte cuadrado centrado, para que el avatar no salga deformado
    ancho, alto = imagen.size
    lado = min(ancho, alto)
    izq = (ancho - lado) // 2
    arr = (alto - lado) // 2
    imagen = imagen.crop((izq, arr, izq + lado, arr + lado))
    imagen = imagen.resize((LADO_FOTO, LADO_FOTO), Image.LANCZOS)

    buffer = io.BytesIO()
    imagen.save(buffer, format="JPEG", quality=85, optimize=True)
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


@router.post("/foto", response_model=dict)
async def subir_foto(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Sube la foto de perfil del propio usuario."""
    datos = await archivo.read()
    if not datos:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(datos) > PESO_MAXIMO_FOTO:
        raise HTTPException(status_code=400, detail="La imagen no puede pesar más de 5 MB")

    current_user.foto = _procesar_foto(datos)
    db.commit()
    return {"data": {"foto": current_user.foto}, "message": "Foto actualizada", "success": True}


@router.delete("/foto", response_model=dict)
def quitar_foto(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Quita la foto: el avatar vuelve a las iniciales."""
    current_user.foto = None
    db.commit()
    return {"data": None, "message": "Foto eliminada", "success": True}


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
