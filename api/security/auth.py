import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.data.db import obtener_db
from api.data.models import Usuario
from api.models.schemas import DatosToken

# Configuración del token JWT
CLAVE_SECRETA = os.getenv("JWT_SECRET_KEY", "super_secret_cafe_system_key_1234567890")
ALGORITMO = "HS256"
MINUTOS_EXPIRACION_TOKEN = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "180"))

# Contexto de contraseñas para encriptar
contexto_contrasenas = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema OAuth2 (apunta al endpoint en español)
esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="autenticacion/iniciar-sesion")

def verificar_contrasena(contrasena_plana: str, contrasena_encriptada: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con la encriptada."""
    return contexto_contrasenas.verify(contrasena_plana, contrasena_encriptada)

def obtener_hash_contrasena(contrasena: str) -> str:
    """Genera el hash de una contraseña usando bcrypt."""
    return contexto_contrasenas.hash(contrasena)

def crear_token_acceso(datos: dict, expiracion_personalizada: Optional[timedelta] = None) -> str:
    """Crea un nuevo token de acceso JWT."""
    datos_a_codificar = datos.copy()
    if expiracion_personalizada:
        expiracion = datetime.utcnow() + expiracion_personalizada
    else:
        expiracion = datetime.utcnow() + timedelta(minutes=MINUTOS_EXPIRACION_TOKEN)
    
    datos_a_codificar.update({"exp": expiracion})
    token_jwt = jwt.encode(datos_a_codificar, CLAVE_SECRETA, algorithm=ALGORITMO)
    return token_jwt

async def obtener_usuario_actual(
    token: str = Depends(esquema_oauth2), 
    db: AsyncSession = Depends(obtener_db)
) -> Usuario:
    """
    Dependencia para obtener al usuario autenticado desde la base de datos.
    Valida la firma, la expiración del JWT y que el usuario esté activo.
    """
    excepcion_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales de autenticación no válidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        carga_datos = jwt.decode(token, CLAVE_SECRETA, algorithms=[ALGORITMO])
        correo: str = carga_datos.get("sub")
        rol: str = carga_datos.get("rol")
        if correo is None or rol is None:
            raise excepcion_credenciales
        datos_token = DatosToken(correo=correo, rol=rol)
    except JWTError:
        raise excepcion_credenciales
        
    # Consultar usuario por correo
    consulta = select(Usuario).where(Usuario.correo == datos_token.correo)
    resultado = await db.execute(consulta)
    usuario = resultado.scalar_one_or_none()
    
    if usuario is None:
        raise excepcion_credenciales
    
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo."
        )
        
    return usuario

class VerificadorRol:
    """
    Dependencia para verificar si el usuario autenticado tiene uno de los roles permitidos.
    Uso: Depends(VerificadorRol(["Administrador", "Cajero"]))
    """
    def __init__(self, roles_permitidos: List[str]):
        self.roles_permitidos = roles_permitidos
        
    def __call__(self, usuario_actual: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        if usuario_actual.rol not in self.roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene permisos para realizar esta acción. Roles permitidos: {', '.join(self.roles_permitidos)}."
            )
        return usuario_actual
