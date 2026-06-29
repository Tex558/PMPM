import io
import datetime
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from api.data.db import obtener_db
from api.data.models import Pedido, Usuario
from api.security.auth import VerificadorRol
from api.models.schemas import RespuestaKPIs

# Librerías de ReportLab para la generación del PDF dinámico
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

router = APIRouter(prefix="/reportes", tags=["Reportes"])

def generar_pdf_reporte(ventas_totales: Decimal, ordenes_totales: int) -> io.BytesIO:
    """Genera un reporte PDF dinámico en memoria."""
    flujo_archivo = io.BytesIO()
    lienzo = canvas.Canvas(flujo_archivo, pagesize=letter)
    
    # Encabezado
    lienzo.setFillColor(colors.HexColor("#1A365D"))  # Azul marino elegante
    lienzo.rect(0, 750, 612, 50, fill=True, stroke=False)
    lienzo.setFillColor(colors.white)
    lienzo.setFont("Helvetica-Bold", 16)
    lienzo.drawString(30, 765, "REPORTE DE VENTAS - SISTEMA CAFE")
    
    # Datos de información
    lienzo.setFillColor(colors.black)
    lienzo.setFont("Helvetica-Bold", 12)
    lienzo.drawString(30, 700, f"Fecha de Generación: {datetime.date.today().strftime('%d/%m/%Y')}")
    
    lienzo.setFont("Helvetica", 11)
    lienzo.drawString(30, 670, "Resumen del desempeño diario de la cafetería:")
    
    # Dibujar cuadro de KPIs
    lienzo.setFillColor(colors.HexColor("#F7FAFC"))
    lienzo.rect(30, 520, 552, 120, fill=True, stroke=True)
    lienzo.setFillColor(colors.black)
    
    lienzo.setFont("Helvetica-Bold", 13)
    lienzo.drawString(50, 600, "Métrica Indicador Clave (KPI)")
    lienzo.drawString(350, 600, "Valor Registrado")
    lienzo.setLineWidth(1)
    lienzo.line(50, 590, 550, 590)
    
    lienzo.setFont("Helvetica", 12)
    lienzo.drawString(50, 565, "Ventas Totales (Órdenes Pagadas)")
    lienzo.drawString(350, 565, f"${ventas_totales:.2f} USD")
    
    lienzo.drawString(50, 540, "Total de Órdenes creadas")
    lienzo.drawString(350, 540, f"{ordenes_totales} órdenes")
    
    # Pie de página
    lienzo.setFont("Helvetica-Oblique", 9)
    lienzo.setFillColor(colors.gray)
    lienzo.drawCentredString(306, 50, "Este es un reporte oficial simulado generado asíncronamente por el servidor API.")
    
    lienzo.showPage()
    lienzo.save()
    flujo_archivo.seek(0)
    return flujo_archivo

def generar_csv_reporte(ventas_totales: Decimal, ordenes_totales: int) -> io.BytesIO:
    """Genera un archivo CSV en memoria representando los datos estructurados."""
    flujo_archivo = io.BytesIO()
    texto_csv = (
        "REPORTE DIARIO DE CAFETERIA\n"
        f"Fecha,{datetime.date.today().isoformat()}\n"
        f"Ventas Totales (USD),{ventas_totales:.2f}\n"
        f"Ordenes Totales,{ordenes_totales}\n"
    )
    flujo_archivo.write(texto_csv.encode('utf-8'))
    flujo_archivo.seek(0)
    return flujo_archivo

@router.get("/kpis", response_model=RespuestaKPIs)
async def obtener_kpis(
    db: AsyncSession = Depends(obtener_db),
    usuario_actual: Usuario = Depends(VerificadorRol(["Administrador", "Cajero"]))
):
    """
    Obtener los Indicadores Clave de Rendimiento (KPIs) del día actual:
    - Ventas totales (suma de los totales de las órdenes con estado 'Pagado').
    - Total de órdenes creadas hoy.
    """
    inicio_hoy = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    fin_hoy = datetime.datetime.combine(datetime.date.today(), datetime.time.max)
    
    # Consultar monto de ventas totales
    consulta_ventas = select(func.sum(Pedido.total)).where(
        Pedido.estado == "Pagado",
        Pedido.fecha_hora >= inicio_hoy,
        Pedido.fecha_hora <= fin_hoy
    )
    resultado_ventas = await db.execute(consulta_ventas)
    ventas_totales = resultado_ventas.scalar()
    if ventas_totales is None:
        ventas_totales = Decimal("0.00")
        
    # Consultar cantidad total de órdenes creadas hoy
    consulta_ordenes = select(func.count(Pedido.id)).where(
        Pedido.fecha_hora >= inicio_hoy,
        Pedido.fecha_hora <= fin_hoy
    )
    resultado_ordenes = await db.execute(consulta_ordenes)
    ordenes_totales = resultado_ordenes.scalar() or 0
    
    return {
        "ventas_totales": ventas_totales,
        "ordenes_totales": ordenes_totales
    }

@router.get("/exportar")
async def exportar_reporte(
    formato: Literal["pdf", "xlsx"] = "pdf",
    db: AsyncSession = Depends(obtener_db),
    usuario_actual: Usuario = Depends(VerificadorRol(["Administrador", "Cajero"]))
):
    """
    Simula y exporta el reporte diario como un archivo de descarga.
    Formatos admitidos:
    - pdf: Genera un reporte PDF estructurado.
    - xlsx: Envía un flujo de datos tabulares (en formato CSV).
    """
    # Obtener KPIs para incluir en el archivo
    kpis = await obtener_kpis(db=db, usuario_actual=usuario_actual)
    ventas_totales = kpis["ventas_totales"]
    ordenes_totales = kpis["ordenes_totales"]
    
    if formato == "pdf":
        flujo_archivo = generar_pdf_reporte(ventas_totales, ordenes_totales)
        cabeceras = {
            'Content-Disposition': f'attachment; filename="reporte_{datetime.date.today().isoformat()}.pdf"'
        }
        return StreamingResponse(flujo_archivo, media_type="application/pdf", headers=cabeceras)
    else:
        flujo_archivo = generar_csv_reporte(ventas_totales, ordenes_totales)
        cabeceras = {
            'Content-Disposition': f'attachment; filename="reporte_{datetime.date.today().isoformat()}.csv"'
        }
        return StreamingResponse(flujo_archivo, media_type="text/csv", headers=cabeceras)
