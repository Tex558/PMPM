from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.data.db import obtener_db
from api.data.models import Usuario
from api.security.auth import VerificadorRol, obtener_usuario_actual, obtener_hash_contrasena
from api.models.schemas import UsuarioCrear, UsuarioActualizar, UsuarioRespuesta

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    dependencies=[Depends(VerificadorRol(["Administrador"]))]
)

@router.get("/", response_model=List[UsuarioRespuesta])
async def listar_usuarios(db: AsyncSession = Depends(obtener_db)):
    """Listar todos los usuarios en el sistema."""
    consulta = select(Usuario).order_by(Usuario.id)
    resultado = await db.execute(consulta)
    return resultado.scalars().all()

@router.get("/{id}", response_model=UsuarioRespuesta)
async def obtener_usuario(id: int, db: AsyncSession = Depends(obtener_db)):
    """Obtener los detalles de un usuario específico por su ID."""
    consulta = select(Usuario).where(Usuario.id == id)
    resultado = await db.execute(consulta)
    usuario = resultado.scalar_one_or_none()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )
    return usuario

@router.post("/", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
async def crear_usuario(datos_usuario: UsuarioCrear, db: AsyncSession = Depends(obtener_db)):
    """Crear un nuevo usuario. La contraseña se encripta automáticamente."""
    # Verificar si el correo ya existe
    consulta = select(Usuario).where(Usuario.correo == datos_usuario.correo)
    resultado = await db.execute(consulta)
    if resultado.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado."
        )
        
    usuario_db = Usuario(
        nombre=datos_usuario.nombre,
        correo=datos_usuario.correo,
        contrasena_hash=obtener_hash_contrasena(datos_usuario.contrasena),
        rol=datos_usuario.rol,
        activo=True
    )
    db.add(usuario_db)
    await db.flush()  # Para poblar el id
    return usuario_db

@router.put("/{id}", response_model=UsuarioRespuesta)
async def actualizar_usuario(
    id: int, 
    datos_usuario: UsuarioActualizar, 
    db: AsyncSession = Depends(obtener_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual)
):
    """
    Actualizar detalles de un usuario.
    Previene la desactivación o el cambio de rol del administrador actual.
    """
    consulta = select(Usuario).where(Usuario.id == id)
    resultado = await db.execute(consulta)
    usuario_db = resultado.scalar_one_or_none()
    if not usuario_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )
        
    # Previene que el administrador actual se desactive o cambie su rol a sí mismo
    if usuario_db.id == usuario_actual.id:
        if datos_usuario.activo is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes desactivar tu propia cuenta."
            )
        if datos_usuario.rol is not None and datos_usuario.rol != usuario_actual.rol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes cambiar tu propio rol."
            )
            
    if datos_usuario.correo is not None and datos_usuario.correo != usuario_db.correo:
        # Verificar que el nuevo correo no esté en uso
        consulta_correo = select(Usuario).where(Usuario.correo == datos_usuario.correo)
        resultado_correo = await db.execute(consulta_correo)
        if resultado_correo.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está en uso."
            )
        usuario_db.correo = datos_usuario.correo
        
    if datos_usuario.nombre is not None:
        usuario_db.nombre = datos_usuario.nombre
    if datos_usuario.rol is not None:
        usuario_db.rol = datos_usuario.rol
    if datos_usuario.activo is not None:
        usuario_db.activo = datos_usuario.activo
    if datos_usuario.contrasena is not None:
        usuario_db.contrasena_hash = obtener_hash_contrasena(datos_usuario.contrasena)
        
    return usuario_db

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(
    id: int, 
    db: AsyncSession = Depends(obtener_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual)
):
    """
    Eliminar un usuario del sistema físicamente.
    Previene que el administrador actual se elimine a sí mismo.
    """
    consulta = select(Usuario).where(Usuario.id == id)
    resultado = await db.execute(consulta)
    usuario_db = resultado.scalar_one_or_none()
    if not usuario_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )
        
    if usuario_db.id == usuario_actual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta de administrador."
        )
        
    await db.delete(usuario_db)
    return None
