from typing import List, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.data.db import obtener_db
from api.data.models import Mesa
from api.security.auth import VerificadorRol, obtener_usuario_actual
from api.models.schemas import MesaRespuesta, MesaCrear

router = APIRouter(prefix="/mesas", tags=["Mesas"])

class ActualizacionEstadoMesa(BaseModel):
    estado: Literal['Libre', 'Ocupada'] = Field(..., description="Estado de la mesa")

@router.get("/", response_model=List[MesaRespuesta])
async def listar_mesas(
    db: AsyncSession = Depends(obtener_db),
    usuario_actual = Depends(obtener_usuario_actual)
):
    """Obtener el mapa/lista actual de mesas (accesible por cualquier usuario autenticado)."""
    consulta = select(Mesa).order_by(Mesa.id)
    resultado = await db.execute(consulta)
    return resultado.scalars().all()

@router.post("/", response_model=MesaRespuesta, status_code=status.HTTP_201_CREATED)
async def crear_mesa(
    datos_mesa: MesaCrear,
    db: AsyncSession = Depends(obtener_db),
    usuario_admin = Depends(VerificadorRol(["Administrador"]))
):
    """Crear una nueva mesa (Admin únicamente)."""
    mesa_db = Mesa(capacidad=datos_mesa.capacidad, estado="Libre")
    db.add(mesa_db)
    await db.flush()
    return mesa_db

@router.put("/{id}/estado", response_model=MesaRespuesta)
async def actualizar_estado_mesa(
    id: int,
    datos_estado: ActualizacionEstadoMesa,
    db: AsyncSession = Depends(obtener_db),
    usuario_autorizado = Depends(VerificadorRol(["Administrador", "Mesero", "Cajero"]))
):
    """Actualiza el estado de disponibilidad de una mesa (Libre / Ocupada)."""
    consulta = select(Mesa).where(Mesa.id == id)
    resultado = await db.execute(consulta)
    mesa_db = resultado.scalar_one_or_none()
    
    if not mesa_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada."
        )
        
    mesa_db.estado = datos_estado.estado
    return mesa_db

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_mesa(
    id: int,
    db: AsyncSession = Depends(obtener_db),
    usuario_admin = Depends(VerificadorRol(["Administrador"]))
):
    """Eliminar una mesa del sistema (Admin únicamente)."""
    consulta = select(Mesa).where(Mesa.id == id)
    resultado = await db.execute(consulta)
    mesa_db = resultado.scalar_one_or_none()
    
    if not mesa_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada."
        )
        
    await db.delete(mesa_db)
    return None
