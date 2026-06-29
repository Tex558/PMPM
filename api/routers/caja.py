from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.data.db import obtener_db
from api.data.models import Pedido, Mesa, MovimientoCaja, Usuario
from api.security.auth import VerificadorRol
from api.models.schemas import MovimientoCajaRespuesta, MovimientoCajaCrear

router = APIRouter(prefix="/caja", tags=["Caja"])

@router.post("/{id_pedido}/pagar", response_model=MovimientoCajaRespuesta, status_code=status.HTTP_200_OK)
async def registrar_pago(
    id_pedido: int,
    datos_pago: MovimientoCajaCrear,
    db: AsyncSession = Depends(obtener_db),
    usuario_actual: Usuario = Depends(VerificadorRol(["Administrador", "Cajero"]))
):
    """
    Registrar el pago de un pedido en una sola transacción atómica:
    1. Verifica que el pedido exista y no haya sido pagado anteriormente.
    2. Cambia el estado del pedido a 'Pagado'.
    3. Libera la mesa asociada (cambia el estado a 'Libre').
    4. Registra el ingreso en 'movimientos_caja' con los detalles del pago.
    """
    # 1. Obtener el pedido
    consulta_pedido = select(Pedido).where(Pedido.id == id_pedido)
    resultado_pedido = await db.execute(consulta_pedido)
    pedido_db = resultado_pedido.scalar_one_or_none()
    
    if not pedido_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El pedido con ID {id_pedido} no existe."
        )
        
    if pedido_db.estado == "Pagado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido ya ha sido pagado y cerrado."
        )
        
    # 2. Cambiar estado a 'Pagado'
    pedido_db.estado = "Pagado"
    
    # 3. Obtener y liberar la mesa asociada
    consulta_mesa = select(Mesa).where(Mesa.id == pedido_db.id_mesa)
    resultado_mesa = await db.execute(consulta_mesa)
    mesa_db = resultado_mesa.scalar_one_or_none()
    
    if mesa_db:
        mesa_db.estado = "Libre"
        
    # 4. Registrar movimiento de caja
    movimiento_db = MovimientoCaja(
        id_pedido=pedido_db.id,
        monto=pedido_db.total,
        tipo_pago=datos_pago.tipo_pago
    )
    
    db.add(movimiento_db)
    await db.flush()  # Genera el ID y las marcas de tiempo
    
    return movimiento_db
