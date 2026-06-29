from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import ForeignKey, String, Integer, Numeric, Boolean, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.data.db import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    correo: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(50), nullable=False)  # 'Administrador', 'Mesero', 'Cajero', 'Cocinero'
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class Mesa(Base):
    __tablename__ = "mesas"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    capacidad: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(50), default="Libre", nullable=False)  # 'Libre', 'Ocupada'

class Producto(Base):
    __tablename__ = "productos"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class Pedido(Base):
    __tablename__ = "pedidos"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_mesa: Mapped[int] = mapped_column(Integer, ForeignKey("mesas.id"), nullable=False)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    estado: Mapped[str] = mapped_column(String(50), default="Pendiente", nullable=False)  # 'Pendiente', 'En Preparación', 'Listo', 'Pagado'
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relaciones
    mesa: Mapped["Mesa"] = relationship("Mesa")
    usuario: Mapped["Usuario"] = relationship("Usuario")
    detalles: Mapped[List["DetallePedido"]] = relationship(
        "DetallePedido", 
        back_populates="pedido", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )

class DetallePedido(Base):
    __tablename__ = "detalle_pedidos"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_pedido: Mapped[int] = mapped_column(Integer, ForeignKey("pedidos.id"), nullable=False)
    id_producto: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    nota_preparacion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relaciones
    pedido: Mapped["Pedido"] = relationship("Pedido", back_populates="detalles")
    producto: Mapped["Producto"] = relationship("Producto", lazy="selectin")

class MovimientoCaja(Base):
    __tablename__ = "movimientos_caja"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_pedido: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("pedidos.id"), nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tipo_pago: Mapped[str] = mapped_column(String(50), nullable=False)  # 'Efectivo', 'Tarjeta'
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relaciones
    pedido: Mapped[Optional["Pedido"]] = relationship("Pedido")
