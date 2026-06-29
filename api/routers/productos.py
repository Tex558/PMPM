from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.data.db import obtener_db
from api.data.models import Producto
from api.security.auth import VerificadorRol, obtener_usuario_actual
from api.models.schemas import ProductoRespuesta, ProductoCrear, ProductoActualizar, ProductoDisponibilidad

router = APIRouter(prefix="/productos", tags=["Productos"])

@router.get("/", response_model=List[ProductoRespuesta])
async def listar_productos(
    db: AsyncSession = Depends(obtener_db),
    usuario_actual = Depends(obtener_usuario_actual)
):
    """Obtener el catálogo completo de productos (accesible por cualquier usuario autenticado)."""
    consulta = select(Producto).order_by(Producto.id)
    resultado = await db.execute(consulta)
    return resultado.scalars().all()

@router.get("/{id}", response_model=ProductoRespuesta)
async def obtener_producto(
    id: int,
    db: AsyncSession = Depends(obtener_db),
    usuario_actual = Depends(obtener_usuario_actual)
):
    """Obtener detalles de un producto específico por ID."""
    consulta = select(Producto).where(Producto.id == id)
    resultado = await db.execute(consulta)
    producto_db = resultado.scalar_one_or_none()
    if not producto_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )
    return producto_db

@router.post("/", response_model=ProductoRespuesta, status_code=status.HTTP_201_CREATED)
async def crear_producto(
    datos_producto: ProductoCrear,
    db: AsyncSession = Depends(obtener_db),
    usuario_admin = Depends(VerificadorRol(["Administrador"]))
):
    """Crear un nuevo producto en el catálogo (Admin únicamente)."""
    producto_db = Producto(
        nombre=datos_producto.nombre,
        descripcion=datos_producto.descripcion,
        precio=datos_producto.precio,
        disponible=True
    )
    db.add(producto_db)
    await db.flush()
    return producto_db

@router.put("/{id}", response_model=ProductoRespuesta)
async def actualizar_producto(
    id: int,
    datos_producto: ProductoActualizar,
    db: AsyncSession = Depends(obtener_db),
    usuario_admin = Depends(VerificadorRol(["Administrador"]))
):
    """Actualiza la información de un producto (Admin únicamente)."""
    consulta = select(Producto).where(Producto.id == id)
    resultado = await db.execute(consulta)
    producto_db = resultado.scalar_one_or_none()
    if not producto_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )
        
    if datos_producto.nombre is not None:
        producto_db.nombre = datos_producto.nombre
    if datos_producto.descripcion is not None:
        producto_db.descripcion = datos_producto.descripcion
    if datos_producto.precio is not None:
        producto_db.precio = datos_producto.precio
    if datos_producto.disponible is not None:
        producto_db.disponible = datos_producto.disponible
        
    return producto_db

@router.patch("/{id}/disponibilidad", response_model=ProductoRespuesta)
async def actualizar_disponibilidad(
    id: int,
    datos_disponibilidad: ProductoDisponibilidad,
    db: AsyncSession = Depends(obtener_db),
    usuario_autorizado = Depends(VerificadorRol(["Administrador", "Mesero", "Cocinero"]))
):
    """
    Actualización rápida de la disponibilidad de un producto.
    Accesible por Administradores, Meseros y Cocineros.
    """
    consulta = select(Producto).where(Producto.id == id)
    resultado = await db.execute(consulta)
    producto_db = resultado.scalar_one_or_none()
    if not producto_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )
        
    producto_db.disponible = datos_disponibilidad.disponible
    return producto_db

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_producto(
    id: int,
    db: AsyncSession = Depends(obtener_db),
    usuario_admin = Depends(VerificadorRol(["Administrador"]))
):
    """Eliminar un producto del catálogo (Admin únicamente)."""
    consulta = select(Producto).where(Producto.id == id)
    resultado = await db.execute(consulta)
    producto_db = resultado.scalar_one_or_none()
    if not producto_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )
        
    await db.delete(producto_db)
    return None
