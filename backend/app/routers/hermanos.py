from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Hermano

router = APIRouter()

@router.get("/")
def listar_hermanos(db: Session = Depends(get_db)):
    return db.query(Hermano).all()

@router.get("/{codigo}")
def get_hermano(codigo: str, db: Session = Depends(get_db)):
    h = db.query(Hermano).filter(Hermano.codigo_lead == codigo).first()
    if not h:
        h = db.query(Hermano).filter(Hermano.nombre.ilike(f"%{codigo}%")).first()
    return h or {"error": "No encontrado"}
