import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Configuración de la URL de la base de datos (por defecto apunta al servicio 'db' de Docker)
URL_BASE_DATOS = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@db:5432/cafe_db"
)

# Crear motor asíncrono
motor = create_async_engine(
    URL_BASE_DATOS,
    echo=True,  # Habilitado para depuración de consultas SQL
    future=True
)

# Fábrica de sesiones
sesion_asincrona = async_sessionmaker(
    bind=motor,
    class_=AsyncSession,
    expire_on_commit=False
)

# Clase base declarativa
class Base(DeclarativeBase):
    pass

# Dependencia para obtener la sesión de base de datos
async def obtener_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia para gestionar sesiones de base de datos por petición HTTP.
    Retorna una sesión asíncrona y garantiza el commit al finalizar
    o el rollback en caso de error.
    """
    async with sesion_asincrona() as sesion:
        try:
            yield sesion
            await sesion.commit()
        except Exception:
            await sesion.rollback()
            raise
