from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Reporte, Hermano
from datetime import date
from typing import Optional

router = APIRouter()

@router.get("/")
def listar_reportes(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    codigo: Optional[str] = None,
    distrito: Optional[str] = None,
    zona: Optional[str] = None,
    pendientes: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    q = db.query(Reporte)
    if desde: q = q.filter(Reporte.fecha >= desde)
    if hasta: q = q.filter(Reporte.fecha <= hasta)
    if codigo: q = q.filter(Reporte.codigo == codigo)
    if distrito: q = q.filter(Reporte.distrito == distrito)
    if zona: q = q.filter(Reporte.zona == zona)
    if pendientes:
        q = q.filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""]))
    return q.order_by(Reporte.fecha.desc()).limit(500).all()

@router.get("/resumen")
def resumen(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    codigo: Optional[str] = None,
    distrito: Optional[str] = None,
    zona: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Reporte)
    if desde: q = q.filter(Reporte.fecha >= desde)
    if hasta: q = q.filter(Reporte.fecha <= hasta)
    if codigo: q = q.filter(Reporte.codigo == codigo)
    if distrito: q = q.filter(Reporte.distrito == distrito)
    if zona: q = q.filter(Reporte.zona == zona)
    reportes = q.all()
    total = len(reportes)
    asistencia = sum(r.asistencia or 0 for r in reportes)
    of_total = sum(float(r.ofrenda_total or 0) for r in reportes)
    pendientes = sum(1 for r in reportes if r.ofrenda_recibida in ("Pendiente", ""))
    return {
        "total": total,
        "asistencia": asistencia,
        "ofTotal": round(of_total, 2),
        "pendientes": pendientes
    }
