from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Seguimiento
from typing import Optional

router = APIRouter()

@router.get("/")
def listar_seguimientos(
    estado: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Seguimiento)
    if estado:
        q = q.filter(Seguimiento.estado.ilike(f"%{estado}%"))
    return q.order_by(Seguimiento.fecha.desc()).limit(100).all()
