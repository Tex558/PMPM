from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.data.db import obtener_db
from api.data.models import Pedido, DetallePedido, Mesa, Producto, Usuario
from api.security.auth import VerificadorRol, obtener_usuario_actual
from api.models.schemas import PedidoRespuesta, PedidoCrear, PedidoEstadoActualizar

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

@router.post("/", response_model=PedidoRespuesta, status_code=status.HTTP_201_CREATED)
async def crear_pedido(
    datos_pedido: PedidoCrear,
    db: AsyncSession = Depends(obtener_db),
    usuario_actual: Usuario = Depends(VerificadorRol(["Administrador", "Mesero"]))
):
    """
    Crea un nuevo pedido en una única transacción compuesta:
    1. Verifica que la mesa exista y esté 'Libre'.
    2. Consulta cada producto de la DB para comprobar su existencia, disponibilidad
       y obtener su precio actual (evitando manipulación de precios desde el cliente).
    3. Calcula el total acumulado del pedido.
    4. Registra el pedido y sus líneas de detalle correspondientes.
    5. Actualiza el estado de la mesa a 'Ocupada'.
    """
    # 1. Buscar la mesa y verificar disponibilidad
    consulta_mesa = select(Mesa).where(Mesa.id == datos_pedido.id_mesa)
    resultado_mesa = await db.execute(consulta_mesa)
    mesa = resultado_mesa.scalar_one_or_none()
    
    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La mesa con ID {datos_pedido.id_mesa} no existe."
        )
    if mesa.estado == "Ocupada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La mesa con ID {datos_pedido.id_mesa} ya está ocupada."
        )
        
    # 2. Validar que tenga detalles
    if not datos_pedido.detalles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido debe contener al menos un producto."
        )
        
    detalles_db = []
    total = Decimal("0.00")
    
    # Procesar cada línea del pedido
    for detalle in datos_pedido.detalles:
        consulta_producto = select(Producto).where(Producto.id == detalle.id_producto)
        resultado_producto = await db.execute(consulta_producto)
        producto = resultado_producto.scalar_one_or_none()
        
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El producto con ID {detalle.id_producto} no existe."
            )
        if not producto.disponible:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El producto '{producto.nombre}' no está disponible actualmente."
            )
            
        total_linea = producto.precio * detalle.cantidad
        total += total_linea
        
        detalle_db = DetallePedido(
            id_producto=producto.id,
            cantidad=detalle.cantidad,
            precio_unitario=producto.precio,
            nota_preparacion=detalle.nota_preparacion
        )
        detalles_db.append(detalle_db)
        
    # 3. Instanciar el pedido
    pedido_db = Pedido(
        id_mesa=mesa.id,
        id_usuario=usuario_actual.id,
        total=total,
        estado="Pendiente",
        detalles=detalles_db
    )
    
    # 4. Cambiar el estado de la mesa a 'Ocupada'
    mesa.estado = "Ocupada"
    
    # Añadir a la base de datos (el commit lo maneja obtener_db)
    db.add(pedido_db)
    await db.flush()
    
    return pedido_db

@router.get("/activos", response_model=List[PedidoRespuesta])
async def listar_pedidos_activos(
    db: AsyncSession = Depends(obtener_db),
    usuario_actual: Usuario = Depends(VerificadorRol(["Administrador", "Mesero", "Cocinero", "Cajero"]))
):
    """
    Listar todos los pedidos activos (que no tengan estado 'Pagado').
    Consumido por cocina y meseros para dar seguimiento a la preparación.
    """
    consulta = select(Pedido).where(Pedido.estado != "Pagado").order_by(Pedido.fecha_hora.asc())
    resultado = await db.execute(consulta)
    return resultado.scalars().all()

@router.patch("/{id}/estado", response_model=PedidoRespuesta)
async def actualizar_estado_pedido(
    id: int,
    datos_estado: PedidoEstadoActualizar,
    db: AsyncSession = Depends(obtener_db),
    usuario_actual: Usuario = Depends(VerificadorRol(["Administrador", "Mesero", "Cocinero"]))
):
    """
    Actualizar el estado de preparación de un pedido ('Pendiente', 'En Preparación', 'Listo').
    Accesible por Administradores, Meseros y Cocineros.
    """
    consulta = select(Pedido).where(Pedido.id == id)
    resultado = await db.execute(consulta)
    pedido_db = resultado.scalar_one_or_none()
    
    if not pedido_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado."
        )
        
    if pedido_db.estado == "Pagado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cambiar el estado de un pedido que ya está pagado."
        )
        
    pedido_db.estado = datos_estado.estado
    return pedido_db
