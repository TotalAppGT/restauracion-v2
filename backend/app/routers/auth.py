from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from pydantic import BaseModel
import bcrypt
import jwt
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

router = APIRouter()
SECRET = os.getenv("JWT_SECRET", "redil_secret_key_2026")

# Rate limiting: track login attempts per IP
login_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

class LoginRequest(BaseModel):
    email: str
    password: str

def validate_password(password: str) -> bool:
    """Validate password meets minimum security requirements"""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True

def check_rate_limit(client_ip: str) -> bool:
    """Check if IP is rate limited"""
    now = datetime.utcnow()
    # Clean old attempts
    login_attempts[client_ip] = [
        t for t in login_attempts[client_ip]
        if (now - t).total_seconds() < LOCKOUT_MINUTES * 60
    ]
    return len(login_attempts[client_ip]) < MAX_ATTEMPTS

def record_login_attempt(client_ip: str, success: bool):
    """Record login attempt"""
    if not success:
        login_attempts[client_ip].append(datetime.utcnow())

@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit
    if not check_rate_limit(client_ip):
        raise HTTPException(429, f"Demasiados intentos. Intenta en {LOCKOUT_MINUTES} minutos")

    user = db.query(Usuario).filter(Usuario.email == req.email).first()

    if not user or not bcrypt.checkpw(req.password.encode(), user.password.encode()):
        record_login_attempt(client_ip, False)
        raise HTTPException(401, "Credenciales inválidas")

    if not user.activo:
        raise HTTPException(401, "Usuario inactivo")

    # Success - clear attempts
    login_attempts[client_ip].clear()

    token = jwt.encode({
        "id": user.id, "email": user.email, "rol": user.rol,
        "exp": datetime.utcnow() + timedelta(days=7)
    }, SECRET, algorithm="HS256")

    return {"token": token, "usuario": {"nombre": user.nombre, "email": user.email, "rol": user.rol}}

@router.post("/change-password")
def change_password(req: dict, db: Session = Depends(get_db)):
    """Change user password with validation"""
    email = req.get("email")
    old_password = req.get("old_password")
    new_password = req.get("new_password")

    if not all([email, old_password, new_password]):
        raise HTTPException(400, "Todos los campos son requeridos")

    if not validate_password(new_password):
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número")

    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user or not bcrypt.checkpw(old_password.encode(), user.password.encode()):
        raise HTTPException(401, "Contraseña actual incorrecta")

    user.password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    db.commit()

    return {"ok": True, "msg": "Contraseña actualizada"}
