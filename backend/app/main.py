from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.database import engine, Base, SessionLocal
from app.routers import reportes, hermanos, seguimientos, auth, telegram, dispatch
from app.models import Usuario
import bcrypt
import os
# Crear tablas en BD
Base.metadata.create_all(bind=engine)

# Migración: agregar columnas nuevas si no existen
try:
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    cols_u = [c["name"] for c in inspector.get_columns("usuarios")]
    cols_r = [c["name"] for c in inspector.get_columns("reportes")]
    cols_g = [c["name"] for c in inspector.get_columns("gastos")]
    cols_gen = [c["name"] for c in inspector.get_columns("generadores_reporte")]
    with engine.connect() as conn:
        if "menu_permitido" not in cols_u:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN menu_permitido TEXT"))
        if "puede_ver_bitacora" not in cols_u:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN puede_ver_bitacora BOOLEAN DEFAULT TRUE"))
        for col in ["hora_inicio","hora_final","ofrenda_iglesia","ofrenda_bus","martes","jueves","domingo","otros","total_cultos","reporte_origen","sup_sector","sup_area","pastor_zona","anfitrion","seguimientos_count"]:
            if col not in cols_r:
                t = "INTEGER DEFAULT 0" if col in ("martes","jueves","domingo","otros","total_cultos","seguimientos_count") else "NUMERIC(12,2) DEFAULT 0" if col in ("ofrenda_iglesia","ofrenda_bus") else "VARCHAR(200) DEFAULT ''"
                conn.execute(text(f"ALTER TABLE reportes ADD COLUMN {col} {t}"))
        if "direccion" not in cols_r:
            conn.execute(text("ALTER TABLE reportes ADD COLUMN direccion TEXT DEFAULT ''"))
        if "evento" not in cols_g:
            conn.execute(text("ALTER TABLE gastos ADD COLUMN evento VARCHAR(200) DEFAULT ''"))
        if "pdf_data" not in cols_gen:
            conn.execute(text("ALTER TABLE generadores_reporte ADD COLUMN pdf_data TEXT"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bautizos (
                id SERIAL PRIMARY KEY,
                fecha DATE,
                nombre VARCHAR(200),
                edad INTEGER DEFAULT 0,
                telefono VARCHAR(50),
                direccion TEXT,
                pastor_oficiante VARCHAR(200),
                lugar VARCHAR(200),
                observaciones TEXT,
                activo BOOLEAN DEFAULT TRUE,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notificaciones (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(200) DEFAULT '',
                mensaje TEXT NOT NULL,
                tipo VARCHAR(30) DEFAULT 'general',
                evento VARCHAR(200) DEFAULT '',
                lugar VARCHAR(200) DEFAULT '',
                hora_evento VARCHAR(10) DEFAULT '',
                info_extra VARCHAR(300) DEFAULT '',
                frecuencia VARCHAR(20) DEFAULT 'una_vez',
                dia_semana INTEGER,
                dia_mes INTEGER,
                hora_envio VARCHAR(10) DEFAULT '08:00',
                activo BOOLEAN DEFAULT TRUE,
                destinatarios TEXT DEFAULT '[]',
                ultimo_envio TIMESTAMP,
                proximo_envio TIMESTAMP,
                creado_por VARCHAR(200) DEFAULT '',
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notificaciones_log (
                id SERIAL PRIMARY KEY,
                notificacion_id INTEGER,
                titulo VARCHAR(200) DEFAULT '',
                destino VARCHAR(50),
                wamid VARCHAR(200),
                estado VARCHAR(50),
                error_msg VARCHAR(300) DEFAULT '',
                fecha TIMESTAMP DEFAULT NOW()
            )
        """))
        # Migrar columnas nuevas de notificaciones
        try:
            cols_notif = [c["name"] for c in inspector.get_columns("notificaciones")]
            for col, defn in [("tipo","VARCHAR(30) DEFAULT 'general'"),
                              ("evento","VARCHAR(200) DEFAULT ''"),
                              ("lugar","VARCHAR(200) DEFAULT ''"),
                              ("hora_evento","VARCHAR(10) DEFAULT ''"),
                              ("info_extra","VARCHAR(300) DEFAULT ''")]:
                if col not in cols_notif:
                    conn.execute(text(f"ALTER TABLE notificaciones ADD COLUMN {col} {defn}"))
            conn.commit()
        except Exception:
            pass
        conn.commit()
except Exception as e:
    print(f"⚠️ Migración: {e}")

# Seed: crear admin por defecto
try:
    db = SessionLocal()
    admin = db.query(Usuario).filter(Usuario.email == "totalappgt@gmail.com").first()
    if not admin:
        admin = Usuario(
            nombre="TotalAppGT",
            email="totalappgt@gmail.com",
            password=bcrypt.hashpw("admintotal".encode(), bcrypt.gensalt()).decode(),
            rol="propietario",
            activo=True,
            menu_permitido=None,
            puede_ver_bitacora=True
        )
        db.add(admin)
        db.commit()
        print("✅ Admin creado: totalappgt@gmail.com")
    db.close()
except Exception as e:
    print(f"⚠️ Seed admin: {e}")

app = FastAPI(title="REDIL API", version="7.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(hermanos.router, prefix="/api/hermanos", tags=["Hermanos"])
app.include_router(reportes.router, prefix="/api/reportes", tags=["Reportes"])
app.include_router(seguimientos.router, prefix="/api/seguimientos", tags=["Seguimientos"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["Telegram"])
app.include_router(dispatch.router, prefix="/api", tags=["Dispatch"])

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "7.0"}

# ── WHATSAPP WEBHOOK (estado real de entrega + mensajes entrantes) ──
@app.get("/api/whatsapp/webhook")
def wa_webhook_verify(request: Request):
    hub_mode = request.query_params.get("hub.mode", "")
    hub_token = request.query_params.get("hub.verify_token", "")
    hub_challenge = request.query_params.get("hub.challenge", "")
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "redil_verify_2026")
    if hub_mode == "subscribe" and hub_token == verify_token:
        return hub_challenge
    return "Verificacion fallida", 403

@app.post("/api/whatsapp/webhook")
async def wa_webhook(data: dict, request: Request):
    try:
        import json
        from app.database import SessionLocal
        from app.models import EnvioWhatsapp, MensajeRecibido
        db = SessionLocal()
        try:
            proxy_forwarded = request.headers.get("X-Proxy-Forwarded", "")
            internal_user_id = data.get("_internal_user_id") if isinstance(data, dict) else None

            entry = data.get("entry", [{}])[0] if isinstance(data, dict) else {}
            changes = entry.get("changes", [])

            for ch in changes:
                value = ch.get("value", {})

                # Statuses de entrega
                statuses = value.get("statuses", [])
                for st in statuses:
                    db.add(EnvioWhatsapp(
                        wamid=st.get("id", ""),
                        numero=st.get("recipient_id", ""),
                        estado=st.get("status", ""),
                        timestamp=str(st.get("timestamp", "")),
                        error=json.dumps(st.get("errors", [])) if st.get("errors") else "",
                    ))

                # Mensajes entrantes (respuestas de usuarios)
                messages = value.get("messages", [])
                for msg in messages:
                    msg_type = msg.get("type", "text")
                    content = ""
                    if msg_type == "text":
                        content = msg.get("text", {}).get("body", "")
                    elif msg_type == "button":
                        content = msg.get("button", {}).get("text", "")
                    elif msg_type == "interactive":
                        interactive = msg.get("interactive", {})
                        if interactive.get("type") == "button_reply":
                            content = interactive.get("button_reply", {}).get("title", "")
                        elif interactive.get("type") == "list_reply":
                            content = interactive.get("list_reply", {}).get("title", "")
                    else:
                        content = json.dumps(msg.get(msg_type, {}))

                    db.add(MensajeRecibido(
                        wamid=msg.get("id", ""),
                        remitente=msg.get("from", ""),
                        internal_user_id=str(internal_user_id) if internal_user_id else None,
                        tipo=msg_type,
                        contenido=content,
                        raw_json=json.dumps(data, ensure_ascii=False),
                    ))

            db.commit()
        finally:
            db.close()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "ok", "error": str(e)}

# ── PDF DOWNLOAD (PDF real desde DB) ──
@app.get("/api/pdf/{no_serie}")
def descargar_pdf(no_serie: str):
    from app.database import SessionLocal
    from app.models import GeneradorReporte
    from fastapi.responses import Response
    import base64
    db = SessionLocal()
    try:
        gr = db.query(GeneradorReporte).filter(GeneradorReporte.no_serie == no_serie).first()
        if not gr: return Response(b"PDF no encontrado",404)
        if gr.pdf_data:
            pdf_bytes = base64.b64decode(gr.pdf_data)
            fname = f"redil_{gr.titulo_reporte or 'Reporte'}_{no_serie}.pdf".replace(' ','_').replace('/','-')
            return Response(pdf_bytes, media_type="application/pdf",
                headers={"Content-Disposition": f'inline; filename="{fname}"'})
        return Response(b"PDF no disponible",404)
    except Exception as e:
        return Response(f"Error: {e}".encode(),500)
    finally:
        db.close()

@app.get("/form", response_class=HTMLResponse)
async def form_redirect():
    with open("static/formulario_digital.html", "r", encoding="utf-8") as f:
        return f.read()

# ── SCHEDULER DE NOTIFICACIONES ──
import threading, time, json as json_mod
from datetime import datetime, timedelta

def _procesar_notificaciones_pendientes():
    while True:
        time.sleep(60)
        try:
            from app.database import SessionLocal
            from app.models import Notificacion, NotificacionLog
            from app.whatsapp_utils import send_whatsapp_template
            db = SessionLocal()
            try:
                ahora = datetime.utcnow()
                notifs = db.query(Notificacion).filter(Notificacion.activo == True).all()
                for n in notifs:
                    if n.ultimo_envio and n.frecuencia == "una_vez":
                        continue
                    hora_e = str(n.hora_envio or "08:00")
                    hora_actual = ahora.strftime("%H:%M")
                    if hora_actual != hora_e:
                        continue
                    debe_enviar = False
                    if n.frecuencia == "diaria":
                        debe_enviar = not n.ultimo_envio or n.ultimo_envio.date() < ahora.date()
                    elif n.frecuencia == "semanal":
                        if n.dia_semana is not None and ahora.weekday() == n.dia_semana:
                            debe_enviar = not n.ultimo_envio or n.ultimo_envio.date() < ahora.date()
                    elif n.frecuencia == "mensual":
                        if n.dia_mes is not None and ahora.day == n.dia_mes:
                            debe_enviar = not n.ultimo_envio or n.ultimo_envio.date() < ahora.date()
                    if not debe_enviar:
                        continue
                    try:
                        dests = json_mod.loads(n.destinatarios or "[]")
                    except:
                        dests = []
                    if not dests:
                        continue
                    # Extraer links de grupos WhatsApp
                    wa_links = [d.get("walink", "") for d in dests if d.get("walink")]
                    from app.routers.dispatch import _construir_mensaje_notificacion
                    msg_wa = _construir_mensaje_notificacion(
                        n.tipo or "general", n.titulo, n.mensaje,
                        n.evento, n.lugar, n.hora_evento, n.info_extra
                    )
                    if wa_links:
                        msg_wa += " | " + " | ".join(wa_links[:2])
                    for d in dests:
                        num = str(d.get("numero", "")).replace("+", "").replace(" ", "").replace("-", "")
                        if not num or len(num) < 8:
                            continue
                        try:
                            resp = send_whatsapp_template(num, params=[msg_wa])
                            log_estado = "enviado" if resp.get("ok") else "fallo"
                            log_wamid = resp.get("wamid", "")
                            log_error = str(resp.get("msg", ""))[:300]
                        except Exception as e:
                            log_estado = "error"
                            log_wamid = ""
                            log_error = str(e)[:300]
                        db.add(NotificacionLog(
                            notificacion_id=n.id,
                            titulo=n.titulo,
                            destino=num,
                            wamid=log_wamid,
                            estado=log_estado,
                            error_msg=log_error,
                        ))
                    n.ultimo_envio = ahora
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"ERROR scheduler notificaciones: {e}")

_scheduler_thread = threading.Thread(target=_procesar_notificaciones_pendientes, daemon=True)
_scheduler_thread.start()

# Servir frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")
