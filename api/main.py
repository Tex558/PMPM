from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.future import select

from api.data.db import motor, Base, sesion_asincrona
from api.data.models import Usuario, Mesa, Producto
from api.security.auth import obtener_hash_contrasena

# Importación de routers
from api.routers import auth, usuarios, mesas, productos, pedidos, caja, reportes

@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    """
    Gestor de contexto del ciclo de vida para controlar la inicialización
    de tablas de base de datos y la semilla de datos de prueba.
    """
    # 1. Crear tablas si no existen
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
        
    # 2. Cargar registros semilla si la base de datos está vacía
    async with sesion_asincrona() as sesion:
        try:
            # Semilla del Administrador
            consulta_admin = select(Usuario).where(Usuario.correo == "admin@cafe.com")
            resultado_admin = await sesion.execute(consulta_admin)
            admin = resultado_admin.scalar_one_or_none()
            if not admin:
                sesion.add(Usuario(
                    nombre="Administrador Central",
                    correo="admin@cafe.com",
                    contrasena_hash=obtener_hash_contrasena("admin123"),
                    rol="Administrador",
                    activo=True
                ))
            
            # Semilla de otros roles para pruebas
            consulta_mesero = select(Usuario).where(Usuario.correo == "mesero@cafe.com")
            resultado_mesero = await sesion.execute(consulta_mesero)
            if not resultado_mesero.scalar_one_or_none():
                sesion.add(Usuario(
                    nombre="Mesero Uno",
                    correo="mesero@cafe.com",
                    contrasena_hash=obtener_hash_contrasena("mesero123"),
                    rol="Mesero",
                    activo=True
                ))

            consulta_cajero = select(Usuario).where(Usuario.correo == "cajero@cafe.com")
            resultado_cajero = await sesion.execute(consulta_cajero)
            if not resultado_cajero.scalar_one_or_none():
                sesion.add(Usuario(
                    nombre="Cajero Uno",
                    correo="cajero@cafe.com",
                    contrasena_hash=obtener_hash_contrasena("cajero123"),
                    rol="Cajero",
                    activo=True
                ))

            consulta_cocinero = select(Usuario).where(Usuario.correo == "cocinero@cafe.com")
            resultado_cocinero = await sesion.execute(consulta_cocinero)
            if not resultado_cocinero.scalar_one_or_none():
                sesion.add(Usuario(
                    nombre="Cocinero Uno",
                    correo="cocinero@cafe.com",
                    contrasena_hash=obtener_hash_contrasena("cocinero123"),
                    rol="Cocinero",
                    activo=True
                ))
                
            # Semilla de mesas
            consulta_mesas = select(Mesa)
            resultado_mesas = await sesion.execute(consulta_mesas)
            if not resultado_mesas.scalars().all():
                for i in range(1, 6):
                    sesion.add(Mesa(capacidad=4, estado="Libre"))
                    
            # Semilla de productos del menú
            consulta_productos = select(Producto)
            resultado_productos = await sesion.execute(consulta_productos)
            if not resultado_productos.scalars().all():
                sesion.add(Producto(
                    nombre="Café Americano", 
                    descripcion="Café negro de grano premium 100% Arábica", 
                    precio=2.50, 
                    disponible=True
                ))
                sesion.add(Producto(
                    nombre="Cappuccino", 
                    descripcion="Café expreso con espuma de leche y canela en polvo", 
                    precio=3.50, 
                    disponible=True
                ))
                sesion.add(Producto(
                    nombre="Muffin de Chocolate", 
                    descripcion="Delicioso muffin de vainilla relleno y decorado con chispas de chocolate", 
                    precio=2.00, 
                    disponible=True
                ))
                sesion.add(Producto(
                    nombre="Sándwich de Jamón y Queso", 
                    descripcion="Sándwich prensado caliente con queso fundido y jamón de pavo", 
                    precio=4.50, 
                    disponible=True
                ))
                
            await sesion.commit()
        except Exception:
            await sesion.rollback()
            raise

    yield
    # Limpieza al cerrar
    await motor.dispose()

# Inicialización de la aplicación FastAPI
app = FastAPI(
    title="Sistema de Gestión de Cafetería API",
    description="API modular y asíncrona para control de pedidos, facturación y reportes de la cafetería.",
    version="1.0.0",
    lifespan=ciclo_vida
)

# Configuración del middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redirección de la raíz a la documentación interactiva Swagger
@app.get("/", include_in_schema=False)
async def inicio():
    return RedirectResponse(url="/docs")

# Registro de routers
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(mesas.router)
app.include_router(productos.router)
app.include_router(pedidos.router)
app.include_router(caja.router)
app.include_router(reportes.router)
