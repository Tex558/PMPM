from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.data.db import obtener_db
from api.data.models import Usuario
from api.security.auth import verificar_contrasena, crear_token_acceso
from api.models.schemas import Token

router = APIRouter(prefix="/autenticacion", tags=["Autenticación"])

@router.post("/iniciar-sesion", response_model=Token)
async def iniciar_sesion(
    datos_formulario: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(obtener_db)
):
    """
    Autentica las credenciales de un usuario (correo y contraseña) y genera un token de acceso JWT.
    Recibe los datos del formulario que contiene 'username' (correo) y 'password' (contraseña).
    """
    # Buscar usuario por correo electrónico
    consulta = select(Usuario).where(Usuario.correo == datos_formulario.username)
    resultado = await db.execute(consulta)
    usuario = resultado.scalar_one_or_none()
    
    if not usuario or not verificar_contrasena(datos_formulario.password, usuario.contrasena_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacte a un administrador."
        )
        
    # Generar el token de acceso con correo y rol
    token_acceso = crear_token_acceso(
        datos={"sub": usuario.correo, "rol": usuario.rol}
    )
    return {"token_acceso": token_acceso, "tipo_token": "bearer"}
