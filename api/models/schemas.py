from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Literal
from pydantic import BaseModel, EmailStr, Field

# ==========================================
# ESQUEMAS DE SEGURIDAD
# ==========================================
class Token(BaseModel):
    token_acceso: str
    tipo_token: str

class DatosToken(BaseModel):
    correo: Optional[str] = None
    rol: Optional[str] = None

class SolicitudInicioSesion(BaseModel):
    correo: EmailStr
    contrasena: str


# ==========================================
# ESQUEMAS DE USUARIOS
# ==========================================
class UsuarioBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    correo: EmailStr
    rol: Literal['Administrador', 'Mesero', 'Cajero', 'Cocinero']

class UsuarioCrear(UsuarioBase):
    contrasena: str = Field(..., min_length=6, max_length=100)

class UsuarioActualizar(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    correo: Optional[EmailStr] = None
    rol: Optional[Literal['Administrador', 'Mesero', 'Cajero', 'Cocinero']] = None
    activo: Optional[bool] = None
    contrasena: Optional[str] = Field(None, min_length=6, max_length=100)

class UsuarioRespuesta(UsuarioBase):
    id: int
    activo: bool

    class Config:
        from_attributes = True


# ==========================================
# ESQUEMAS DE MESAS
# ==========================================
class MesaBase(BaseModel):
    capacidad: int = Field(..., gt=0)

class MesaCrear(MesaBase):
    pass

class MesaActualizar(BaseModel):
    capacidad: Optional[int] = Field(None, gt=0)
    estado: Optional[Literal['Libre', 'Ocupada']] = None

class MesaRespuesta(MesaBase):
    id: int
    estado: str

    class Config:
        from_attributes = True


# ==========================================
# ESQUEMAS DE PRODUCTOS
# ==========================================
class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio: Decimal = Field(..., gt=0, decimal_places=2)

class ProductoCrear(ProductoBase):
    pass

class ProductoActualizar(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    disponible: Optional[bool] = None

class ProductoRespuesta(ProductoBase):
    id: int
    disponible: bool

    class Config:
        from_attributes = True

class ProductoDisponibilidad(BaseModel):
    disponible: bool


# ==========================================
# ESQUEMAS DE DETALLE DE PEDIDOS
# ==========================================
class DetallePedidoCrear(BaseModel):
    id_producto: int
    cantidad: int = Field(..., gt=0)
    nota_preparacion: Optional[str] = Field(None, max_length=255)

class DetallePedidoRespuesta(BaseModel):
    id: int
    id_pedido: int
    id_producto: int
    cantidad: int
    precio_unitario: Decimal
    nota_preparacion: Optional[str]

    class Config:
        from_attributes = True


# ==========================================
# ESQUEMAS DE PEDIDOS
# ==========================================
class PedidoCrear(BaseModel):
    id_mesa: int
    detalles: List[DetallePedidoCrear]

class PedidoRespuesta(BaseModel):
    id: int
    id_mesa: int
    id_usuario: int
    total: Decimal
    estado: str
    fecha_hora: datetime
    detalles: List[DetallePedidoRespuesta]

    class Config:
        from_attributes = True

class PedidoEstadoActualizar(BaseModel):
    estado: Literal['Pendiente', 'En Preparación', 'Listo', 'Pagado']


# ==========================================
# ESQUEMAS DE MOVIMIENTOS DE CAJA
# ==========================================
class MovimientoCajaCrear(BaseModel):
    tipo_pago: Literal['Efectivo', 'Tarjeta']

class MovimientoCajaRespuesta(BaseModel):
    id: int
    id_pedido: Optional[int]
    monto: Decimal
    tipo_pago: str
    fecha_hora: datetime

    class Config:
        from_attributes = True


# ==========================================
# ESQUEMAS DE REPORTES
# ==========================================
class RespuestaKPIs(BaseModel):
    ventas_totales: Decimal
    ordenes_totales: int
