from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Usuario, Hermano, Reporte, Seguimiento,
    Supervisor, Pastore, AyudaPastor, Contacto,
    Diezmo, Gasto, Inventario, Insumo, Privilegio,
    Cronograma, Bitacora, Configuracion, Envio, GeneradorReporte, Bautizo
)
import jwt
import bcrypt
import os
import json
import base64
import requests
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from app.email_utils import send_email
from sqlalchemy import func

router = APIRouter()
SECRET = os.getenv("JWT_SECRET", "redil_secret_key_2026")

def esc(s):
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&#39;")

def pdf_safe(s):
    """Convierte texto a latin-1 para fuentes core de fpdf2 (sin emojis ni unicode raro)."""
    return str(s or "").encode("latin-1", "replace").decode("latin-1")

def _htmlesc(s):
    """Escape HTML entities. Separada de esc() para evitar conflicto con variable local en dispatch()."""
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _get_church_name(db):
    """Obtiene el nombre de la iglesia desde config, con fallback."""
    try:
        from app.models import Configuracion
        c = db.query(Configuracion).filter(Configuracion.clave == "nombre").first()
        if c and c.valor: return c.valor
    except: pass
    return "Iglesia Restauracion"

def _get_system_url(db=None):
    """Obtiene la URL del sistema desde config o env, con fallback."""
    try:
        import os
        url = os.getenv("SISTEMA_URL", "")
        if url: return url.rstrip("/")
    except: pass
    try:
        if db:
            from app.models import Configuracion
            c = db.query(Configuracion).filter(Configuracion.clave == "system_url").first()
            if c and c.valor: return c.valor.rstrip("/")
    except: pass
    return "https://redilrestauracion.totalappgt.online"

def _formatear_whatsapp(msg, pdf_url=""):
    sep = " | "
    from datetime import datetime
    fecha = datetime.now().strftime("%d/%m/%Y")
    msg = str(msg or "").strip()
    hay_pdf = bool(pdf_url and pdf_url.strip())
    if hay_pdf:
        return f"\U0001f4ca \U0001f4c4 {msg}{sep}\U0001f4c5 {fecha}"
    return f"\U0001f514 {msg}{sep}\U0001f4c5 {fecha}"

def _fmt_fecha(fecha_str):
    """2026-08-15 -> Viernes 15/08/2026"""
    from datetime import datetime
    DIAS = ["Lunes","Martes","Miercoles","Jueves","Viernes","Sabado","Domingo"]
    MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    try:
        parts = fecha_str.strip().split("-")
        if len(parts) == 3:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            dt = datetime(y, m, d)
            return f"{DIAS[dt.weekday()]} {d} de {MESES[m-1]}"
    except: pass
    return fecha_str

def _fmt_hora(hora_str):
    """19:00 -> 7:00 PM"""
    try:
        h_str = hora_str.strip()
        parts = h_str.split(":")
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        ampm = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d} {ampm}"
    except: pass
    return hora_str

def _construir_mensaje_notificacion(tipo, titulo, mensaje, evento, lugar, hora_evento, info_extra, cita_biblica=None, fecha_evento=None):
    """Construye el cuerpo del mensaje segun el tipo. El titulo de la iglesia lo pone
    la plantilla ({{sistema}} = Iglesia Restauracion); aqui se envian los DETALLES."""
    tipo = (tipo or "general").lower()
    titulo = (titulo or "").strip()
    mensaje = (mensaje or "").strip()
    evento = (evento or "").strip()
    lugar = (lugar or "").strip()
    hora_evento = _fmt_hora(hora_evento) if hora_evento else ""
    info_extra = (info_extra or "").strip()
    fecha_evento = _fmt_fecha(fecha_evento) if fecha_evento else ""

    lineas = []

    if tipo == "recordatorio":
        lineas.append(f"*{titulo or 'Recordatorio'}*")
        if fecha_evento: lineas.append(f"\U0001f4c5 Fecha: {fecha_evento}")
        if hora_evento: lineas.append(f"\U0001f550 Hora: {hora_evento}")
        if lugar: lineas.append(f"\U0001f4cd Lugar: {lugar}")
        if evento: lineas.append(f"\U0001f4cb {evento}")
        if mensaje: lineas.append(mensaje)
    elif tipo == "reunion":
        lineas.append(f"*{titulo or 'Reunion'}*")
        if fecha_evento: lineas.append(f"\U0001f4c5 Fecha: {fecha_evento}")
        if hora_evento: lineas.append(f"\U0001f550 Hora: {hora_evento}")
        if lugar: lineas.append(f"\U0001f4cd Lugar: {lugar}")
        if mensaje: lineas.append(mensaje)
    elif tipo == "aviso":
        lineas.append(f"*{titulo or 'Comunicado'}*")
        if mensaje: lineas.append(mensaje)
        if evento: lineas.append(f"\U0001f4c5 {evento}")
        if hora_evento: lineas.append(f"\U0001f550 {hora_evento}")
        if lugar: lineas.append(f"\U0001f4cd {lugar}")
    elif tipo == "reporte":
        lineas.append(f"*{titulo or 'Reporte'}*")
        if mensaje: lineas.append(mensaje)
        if info_extra: lineas.append(f"\U0001f4c4 {info_extra}")
        lineas.append("\U0001f4ca Revisa los detalles del reporte.")
    elif tipo == "alerta":
        lineas.append(f"\U000026a0 *{titulo or 'Alerta'}*")
        if mensaje: lineas.append(mensaje)
        if info_extra: lineas.append(f"\U0001f6a8 {info_extra}")
    elif tipo == "ofrenda":
        lineas.append(f"*{titulo or 'Ofrenda'}*")
        if mensaje: lineas.append(mensaje)
        if info_extra: lineas.append(f"\U0001f4b0 {info_extra}")
    else:
        lineas.append(f"*{titulo or 'Notificacion'}*")
        if mensaje: lineas.append(mensaje)
        if evento: lineas.append(f"\U0001f4c5 {evento}")
        if hora_evento: lineas.append(f"\U0001f550 {hora_evento}")
        if lugar: lineas.append(f"\U0001f4cd {lugar}")

    if info_extra and tipo not in ("reporte", "alerta", "ofrenda"):
        lineas.append(info_extra)

    sys_url = _get_system_url()
    lineas.append(f"\U0001f517 Ingresa al sistema: {sys_url}")
    return "\n".join(lineas)

ALL_MENU_IDS = [
    'dashboard','reportes','reporteDigital','formulario','generador',
    'hermanos','cargaMasiva','seguimientos','privilegios',
    'diezmos','gastos','cuadre','inventario','insumos','bautizos',
    'supervisores','pastores','ayudapastor',
    'envio','notificaciones','contactos','usuarios','configuracion','bitacora'
]

ROL_DEFAULT_MENU = {
    'Admin':     ['dashboard','reportes','reporteDigital','formulario','generador','hermanos','cargaMasiva','seguimientos','privilegios','diezmos','gastos','cuadre','inventario','insumos','bautizos','envio','notificaciones','contactos','usuarios','supervisores','pastores','ayudapastor','configuracion','bitacora'],
    'Líder':     ['dashboard','reportes','reporteDigital','formulario','seguimientos'],
    'Secretario':['dashboard','reportes','reporteDigital','generador','seguimientos','envio','contactos'],
    'Tesorero':  ['dashboard','reportes','diezmos','gastos','generador','envio'],
    'Digitador': ['dashboard','reportes','envio','contactos'],
    'Solo Lectura': ['dashboard','reportes','envio','contactos']
}

DB_TO_GAS_ROLE = {
    'propietario': 'Admin', 'admin': 'Admin', 'lider': 'Líder',
    'secretario': 'Secretario', 'tesorero': 'Tesorero', 'digitador': 'Digitador'
}

HERMANO_MAP = {"ID": "id", "CodigoL": "codigo_lead", "NombreL": "nombre", "Distrito": "distrito", "Zona": "zona", "Area": "area", "Sector": "sector", "Grupo": "grupo", "Pastor Zona": "pastor_zona", "Sup SectorL": "sup_sector", "Sup AreaL": "sup_area", "Ayuda Pastor": "ayuda_pastor", "Anfitrion": "anfitrion", "Direccion": "direccion", "CodigoSup": "codigo_sup", "CodigoPastor": "codigo_pastor"}
SUPERVISOR_MAP = {"ID": "id", "CodigoSup": "codigo_sup", "NombreSup": "nombre_sup", "Distrito": "distrito", "Zona": "zona", "Area": "area", "Sector": "sector", "Telefono": "telefono", "Email": "email", "Activo": "activo"}
PASTOR_MAP = {"ID": "id", "CodigoPastor": "codigo_pastor", "NombrePastor": "nombre_pastor", "Distrito": "distrito", "Zona": "zona", "Telefono": "telefono", "Email": "email", "Activo": "activo"}
AYUDA_PASTOR_MAP = {"ID": "id", "CodigoAyuda": "codigo_ayuda", "NombreAyuda": "nombre_ayuda", "Distrito": "distrito", "Zona": "zona", "Area": "area", "Telefono": "telefono", "Email": "email", "Activo": "activo"}
CONTACTO_MAP = {"ID": "id", "Nombre": "nombre", "Correo": "email", "WhatsApp": "telefono", "Telefono": "telefono", "Direccion": "direccion", "Notas": "notas", "Activo": "activo"}
DIEZMO_MAP = {"ID": "id", "Fecha": "fecha", "Nombre": "nombre", "Telefono": "telefono", "Grupo": "grupo", "Tipo": "tipo", "MontoQ": "monto", "Descripcion": "observaciones"}
INVENTARIO_MAP = {"ID": "id", "Articulo": "nombre", "Categoria": "categoria", "Cantidad": "cantidad", "Unidad": "unidad", "Estado": "estado", "Ubicacion": "ubicacion", "ValorQ": "valor_q", "Observaciones": "observaciones"}
INSUMO_MAP = {"ID": "id", "Articulo": "nombre", "Categoria": "categoria", "Cantidad": "cantidad", "Unidad": "unidad", "PrecioUnitarioQ": "precio_unitario_q", "StockMinimo": "stock_minimo", "Proveedor": "proveedor", "Observaciones": "observaciones"}
PRIVILEGIO_MAP = {"ID": "id", "Hermano": "nombre", "Area": "area", "CodigoL": "codigo_lead", "Privilegio": "privilegio", "FechaInicio": "fecha_inicio", "FechaFin": "fecha_fin", "Observaciones": "observaciones", "Activo": "activo"}
CRONOGRAMA_MAP = {"ID": "id", "Hermano": "hermano", "Area": "area", "Servicio": "servicio", "Privilegio": "privilegio", "Lunes": "lunes", "Jueves": "jueves", "Domingo_Mañana": "domingo_manana", "Domingo_Tarde": "domingo_tarde", "FechaAsignacion": "fecha_asignacion", "Observaciones": "observaciones", "Activo": "activo"}
BITACORA_MAP = {"ID": "id", "FechaHora": "fecha", "Usuario": "usuario", "Email": "email", "Rol": "rol", "Accion": "accion", "Detalles": "detalle"}
ENVIO_MAP = {"ID": "id", "IDEnvio": "id_envio", "Fecha Hora": "fecha_hora", "Asunto Correo": "asunto_correo", "Cuerpo Mensaje": "cuerpo_mensaje", "Archivos a Enviar": "archivos_a_enviar", "Destinatarios": "destinatarios", "Estado": "estado", "Rutas Reales PDF": "rutas_reales_pdf"}
USUARIO_MAP = {"ID": "id", "Nombre": "nombre", "Email": "email", "Rol": "rol", "Activo": "activo", "MenuPermitido": "menu_permitido", "PuedeVerBitacora": "puede_ver_bitacora"}
GENERADOR_MAP = {"ID": "id", "ID_Reporte": "id_reporte", "Fecha Inicio": "fecha_inicio", "Fecha Fin": "fecha_fin", "Total Ofrenda": "total_ofrenda", "Total Asistencia": "total_asistencia", "Titulo de Reporte": "titulo_reporte", "Archivo Generado": "archivo_generado", "No Serie": "no_serie", "Mes Reporte": "mes_reporte", "Ano Reporte": "ano_reporte", "Filtro Lider": "filtro_lider", "Filtro Sup Sector": "filtro_sup_sector", "Filtro Sup Area": "filtro_sup_area", "Filtro Pastor Zona": "filtro_pastor_zona", "Filtro Distrito": "filtro_distrito", "Filtro Zona": "filtro_zona"}
BAUTIZO_MAP = {"ID": "id", "Fecha": "fecha", "Nombre": "nombre", "Edad": "edad", "Telefono": "telefono", "Direccion": "direccion", "PastorOficiante": "pastor_oficiante", "Lugar": "lugar", "Observaciones": "observaciones", "Activo": "activo"}
REPORTE_MAP = {"ID": "id", "Codigo": "codigo", "Lider": "lider", "Fecha": "fecha", "Distrito": "distrito", "Zona": "zona", "Area": "area", "Sector": "sector", "Grupo": "grupo", "Sup Sector": "sup_sector", "Sup Area": "sup_area", "Pastor Zona": "pastor_zona", "Anfitrion": "anfitrion", "Direccion": "direccion", "Hora Inicio": "hora_inicio", "Hora Final": "hora_final", "Hnos": "hnos", "Amigos": "amigos", "Niños": "ninos", "Asistencia Grupo Familiar": "asistencia", "Ofrenda Iglesia": "ofrenda_iglesia", "Ofrenda Bus": "ofrenda_bus", "Ofrenda Total": "ofrenda_total", "Ofrenda Recibida": "ofrenda_recibida", "Tipo de Reporte": "tipo_reporte", "Reporte": "reporte_origen", "Martes": "martes", "Jueves": "jueves", "Domingo": "domingo", "Otros": "otros", "Total": "total_cultos"}

def get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        user = db.query(Usuario).filter(Usuario.email == payload.get("email")).first()
        return user
    except:
        return None

def make_user_response(u):
    import ast
    # Normalizar rol para lookup (acepta Admin, admin, ADMIN, etc.)
    rol_lower = str(u.rol).lower().strip() if u.rol else ''
    gas_role = DB_TO_GAS_ROLE.get(rol_lower, 'Solo Lectura')
    
    if u.menu_permitido:
        menu = None
        try:
            menu = json.loads(u.menu_permitido) if isinstance(u.menu_permitido, str) else u.menu_permitido
        except:
            try:
                menu = ast.literal_eval(u.menu_permitido) if isinstance(u.menu_permitido, str) else None
            except:
                pass
        if not isinstance(menu, list) or not menu:
            menu = list(ROL_DEFAULT_MENU.get(gas_role, ROL_DEFAULT_MENU['Solo Lectura']))
        if 'dashboard' not in menu:
            menu.insert(0, 'dashboard')
    else:
        menu = list(ROL_DEFAULT_MENU.get(gas_role, ROL_DEFAULT_MENU['Solo Lectura']))
    
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": gas_role, "menu": menu, "isPropietario": u.rol == "propietario", "puedeVerBitacora": u.puede_ver_bitacora if hasattr(u, 'puede_ver_bitacora') else True, "PuedeEditar": "SI" if rol_lower in ("propietario", "admin") else "NO", "inactMin": 60}

def gas_to_db(gas_key, field_map):
    return field_map.get(gas_key)

def payload_to_kwargs(field_map, payload):
    kwargs = {}
    for gas_key, db_key in field_map.items():
        if gas_key in payload:
            kwargs[db_key] = payload[gas_key]
    return kwargs

def db_to_gas(obj, field_map):
    d = {}
    for gas_key, db_key in field_map.items():
        val = getattr(obj, db_key, None)
        if val is not None:
            d[gas_key] = val
    return d

def save_entity(db, model_class, field_map, payload, id_key="ID"):
    item_id = payload.get(id_key)
    data = payload_to_kwargs(field_map, payload)
    if not item_id:
        data.pop("id", None)  # Evitar error de ID vacio en PostgreSQL
    if item_id:
        obj = db.query(model_class).filter(model_class.id == item_id).first()
        if not obj:
            return {"ok": False, "msg": "Registro no encontrado"}
        for key, val in data.items():
            setattr(obj, key, val)
    else:
        obj = model_class(**data)
        db.add(obj)
    db.commit()
    return {"ok": True}

def delete_entity(db, model_class, payload, id_key="ID"):
    item_id = payload.get(id_key) if isinstance(payload, dict) else payload
    if not item_id and isinstance(payload, dict):
        item_id = payload.get("id")
    if not item_id:
        return {"ok": False, "msg": "ID requerido"}
    obj = db.query(model_class).filter(model_class.id == item_id).first()
    if not obj:
        return {"ok": False, "msg": "Registro no encontrado"}
    db.delete(obj)
    db.commit()
    return {"ok": True}

@router.post("/dispatch")
def dispatch(data: dict, db: Session = Depends(get_db)):
    action = data.get("action", "")
    payload = data.get("payload", {})
    token = payload.get("token", data.get("token", ""))
    user = get_user_from_token(token, db) if token else None

    try:
        # ── AUTH ──
        if action == "login":
            email = payload.get("email", ""); password = payload.get("password", "")
            u = db.query(Usuario).filter(Usuario.email == email).first()
            if not u or not bcrypt.checkpw(password.encode(), u.password.encode()):
                return {"ok": False, "msg": "Credenciales inválidas"}
            if not u.activo: return {"ok": False, "msg": "Usuario inactivo"}
            new_token = jwt.encode({"id": u.id, "email": u.email, "rol": u.rol, "exp": datetime.utcnow() + timedelta(days=7)}, SECRET, algorithm="HS256")
            return {"ok": True, "token": new_token, "user": make_user_response(u)}

        if action == "firebaseLogin":
            id_token = payload.get("idToken", "")
            if not id_token:
                return {"ok": False, "msg": "Token de Firebase requerido"}
            try:
                # Verify Firebase ID token via REST API
                api_key = os.getenv("FIREBASE_API_KEY", "")
                resp = requests.post(
                    f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}",
                    json={"idToken": id_token},
                    timeout=10
                )
                if resp.status_code != 200:
                    return {"ok": False, "msg": "Token de Firebase inválido"}
                data = resp.json()
                users = data.get("users", [])
                if not users:
                    return {"ok": False, "msg": "Usuario no encontrado en Firebase"}
                firebase_user = users[0]
                email = firebase_user.get("email", "").lower()
                name = firebase_user.get("displayName", email.split("@")[0])
                if not email:
                    return {"ok": False, "msg": "Email no disponible en Firebase"}
            except Exception as e:
                return {"ok": False, "msg": f"Error verificando Firebase: {str(e)}"}

            # Buscar usuario en la DB local
            u = db.query(Usuario).filter(Usuario.email == email).first()
            if not u:
                # Auto-registrar usuario de Firebase
                u = Usuario(
                    nombre=name,
                    email=email,
                    password=bcrypt.hashpw(os.urandom(16).hex().encode(), bcrypt.gensalt()).decode(),
                    rol="admin",
                    activo=True
                )
                db.add(u)
                db.commit()
            if not u.activo:
                return {"ok": False, "msg": "Usuario inactivo. Contacta al administrador."}
            new_token = jwt.encode({"id": u.id, "email": u.email, "rol": u.rol, "exp": datetime.utcnow() + timedelta(days=7)}, SECRET, algorithm="HS256")
            return {"ok": True, "token": new_token, "user": make_user_response(u)}

        if action == "validateSession":
            u = get_user_from_token(payload.get("token", ""), db)
            if u: return {"ok": True, "user": make_user_response(u)}
            return {"ok": False}

        if action == "destroySession":
            return {"ok": True}

        if action == "registrarAcceso":
            db.add(Bitacora(fecha=datetime.utcnow(), usuario=payload.get("usuario",""), email=payload.get("email",""), rol=payload.get("rol",""), accion=payload.get("accion","Login"), detalle=payload.get("detalles","")))
            db.commit()
            return {"ok": True}

        # ── DASHBOARD ──
        if action == "getDashboard":
            lideres = db.query(Hermano).filter(Hermano.codigo_lead != None).count()
            reportes_mes = db.query(Reporte).count()
            pendientes = db.query(Reporte).filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""])).count()
            asistencia_total = db.query(func.coalesce(func.sum(Reporte.asistencia), 0)).scalar()
            of_total = float(db.query(func.coalesce(func.sum(Reporte.ofrenda_total), 0)).scalar())
            seg_total = db.query(Seguimiento).count()
            return {"ok": True, "lideres": lideres, "reportesMes": reportes_mes, "gruposRealizados": reportes_mes, "asistencia": int(asistencia_total), "ofTotal": round(of_total, 2), "convertidos": 0, "reconciliados": 0, "segTotal": seg_total, "pendientes": pendientes, "metaGrupos": 407, "proxCron": [], "grafica": []}

        # ── HERMANOS (returns RAW ARRAY, matching GAS) ──
        if action == "getHermanos":
            hermanos = db.query(Hermano).all()
            return [db_to_gas(h, HERMANO_MAP) for h in hermanos]

        if action == "getHermanoByCodigo":
            h = db.query(Hermano).filter(Hermano.codigo_lead == payload.get("codigo")).first()
            if h: return {"ok": True, "data": db_to_gas(h, HERMANO_MAP)}
            return {"ok": False, "msg": "Hermano no encontrado"}

        if action == "saveHermano":
            return save_entity(db, Hermano, HERMANO_MAP, payload)

        if action == "deleteHermano":
            return delete_entity(db, Hermano, payload)

        # ── REPORTES (returns raw array) ──
        if action == "getReportes":
            q = db.query(Reporte)
            if payload.get("pendientes"):
                q = q.filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""]))
            if payload.get("desde"):
                q = q.filter(Reporte.fecha >= payload["desde"])
            if payload.get("hasta"):
                q = q.filter(Reporte.fecha <= payload["hasta"])
            if payload.get("codigo"):
                q = q.filter(Reporte.codigo == payload["codigo"])
            reportes = q.order_by(Reporte.fecha.desc()).limit(500).all()
            return [{"ID": r.id, "Codigo": r.codigo, "Lider": r.lider, "Fecha": str(r.fecha) if r.fecha else "", "Distrito": r.distrito, "Zona": r.zona, "Area": r.area, "Sector": r.sector, "Grupo": r.grupo, "Ofrenda Total": float(r.ofrenda_total or 0), "Ofrenda Recibida": r.ofrenda_recibida or "Pendiente", "Asistencia Grupo Familiar": r.asistencia or 0, "Hnos": r.hnos or 0, "Amigos": r.amigos or 0, "Niños": r.ninos or 0, "Tipo de Reporte": r.tipo_reporte or "", "Origen": r.reporte_origen or "Fisico"} for r in reportes]

        if action == "saveReporte":
            return save_entity(db, Reporte, REPORTE_MAP, payload)

        if action == "deleteReporte":
            return delete_entity(db, Reporte, payload)

        if action == "buscarLiderFormulario":
            query = payload.get("query", "")
            h = db.query(Hermano).filter(
                (Hermano.codigo_lead.ilike(f"%{query}%")) | (Hermano.nombre.ilike(f"%{query}%"))
            ).first()
            if h: return {"ok": True, "data": db_to_gas(h, HERMANO_MAP)}
            return {"ok": False, "msg": "No encontrado"}

        if action == "buscarLideres":
            query = payload.get("query", "").strip()
            if len(query) < 2:
                return {"ok": True, "data": []}
            hnos = db.query(Hermano).filter(
                (Hermano.codigo_lead.ilike(f"%{query}%")) | (Hermano.nombre.ilike(f"%{query}%"))
            ).limit(10).all()
            return {"ok": True, "data": [db_to_gas(h, HERMANO_MAP) for h in hnos]}

        if action == "registrarReporteDigital":
            from datetime import date, timedelta
            today_utc = date.today()
            # Ajustar a Guatemala UTC-6
            from datetime import datetime as dt_full
            now_utc = dt_full.utcnow()
            guate = now_utc - timedelta(hours=6)
            today = guate.date()
            codigo = str(payload.get("codigo","")).strip()
            herm = db.query(Hermano).filter(Hermano.codigo_lead == codigo).first()
            hnos = int(payload.get("hermanos",0) or 0)
            amigos = int(payload.get("amigos",0) or 0)
            ninos = int(payload.get("ninos",0) or 0)
            agf = hnos + amigos + ninos
            martes = int(payload.get("martes",0) or 0)
            jueves = int(payload.get("jueves",0) or 0)
            domingo = int(payload.get("domingo",0) or 0)
            otros = int(payload.get("otros",0) or 0)
            total_cultos_val = martes + jueves + domingo + otros
            of_ig = float(payload.get("ofrendaIglesia",0) or 0)
            of_bus = float(payload.get("ofrendaBus",0) or 0)
            of_tot = of_ig + of_bus
            seg_count = sum(1 for i in range(1,11) if payload.get(f"nombre{i}","") and str(payload.get(f"nombre{i}","")).strip())
            r = Reporte(
                codigo=codigo,
                lider=herm.nombre if herm else codigo,
                fecha=today,
                distrito=herm.distrito if herm else "",
                zona=herm.zona if herm else "",
                area=herm.area if herm else "",
                sector=herm.sector if herm else "",
                grupo=herm.grupo if herm else "",
                ofrenda_total=of_tot,
                ofrenda_recibida="Pendiente",
                asistencia=agf,
                hnos=hnos, amigos=amigos, ninos=ninos,
                tipo_reporte=payload.get("tipoReunion","Mixta (Reunión Regular)"),
                hora_inicio=str(payload.get("horaInicio","")),
                hora_final=str(payload.get("horaFinal","")),
                ofrenda_iglesia=of_ig, ofrenda_bus=of_bus,
                martes=martes, jueves=jueves, domingo=domingo, otros=otros,
                total_cultos=total_cultos_val,
                reporte_origen="Digital",
                sup_sector=herm.sup_sector if herm else "",
                sup_area=herm.sup_area if herm else "",
                pastor_zona=herm.pastor_zona if herm else "",
                anfitrion=herm.anfitrion if herm else "",
                direccion=herm.direccion if herm else "",
                seguimientos_count=seg_count,
            )
            db.add(r)
            db.commit()
            # Auto-registrar seguimientos
            lider_nombre = herm.nombre if herm else codigo
            for i in range(1, 11):
                nom = payload.get(f"nombre{i}","")
                if nom and str(nom).strip():
                    tipo = payload.get(f"tipo{i}","Otro")
                    existing = db.query(Seguimiento).filter(
                        Seguimiento.persona == str(nom).strip(),
                        Seguimiento.fecha == today,
                        Seguimiento.responsable == lider_nombre
                    ).first()
                    if not existing:
                        db.add(Seguimiento(
                            fecha=today, persona=str(nom).strip(),
                            tipo=tipo or "Otro", responsable=lider_nombre,
                            estado="En Proceso",
                            observaciones=f"Auto-registrado desde Formulario Digital · {lider_nombre}"
                        ))
            db.commit()
            return {"ok": True}

        if action == "getResumen":
            q = db.query(Reporte)
            if payload.get("desde"): q = q.filter(Reporte.fecha >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Reporte.fecha <= payload["hasta"])
            reportes = q.all()
            total = len(reportes)
            asistencia = sum(r.asistencia or 0 for r in reportes)
            of_total = sum(float(r.ofrenda_total or 0) for r in reportes)
            pendientes = sum(1 for r in reportes if r.ofrenda_recibida in ("Pendiente", ""))
            hnos = sum(r.hnos or 0 for r in reportes)
            amigos = sum(r.amigos or 0 for r in reportes)
            return {"ok": True, "total": total, "asistencia": asistencia, "ofTotal": round(of_total, 2), "pendientes": pendientes, "hnos": hnos, "amigos": amigos}

        # ── CONFIG ──
        if action == "getConfig":
            configs = {}
            try:
                for c in db.query(Configuracion).all():
                    configs[c.clave] = c.valor
            except: pass
            menuConfig = {}
            for m in ALL_MENU_IDS:
                menuConfig[m] = configs.get(f"menu_mod_{m}", "SI") != "NO"
            return {"ok": True, "ssId": configs.get("ssId",""), "nombre": configs.get("nombre","REDIL"), "formUrl": configs.get("formUrl",""), "formUrlPublic": configs.get("formUrlPublic","https://redilrestauracion.totalappgt.online/formulario_digital.html"), "activo": True, "logo_url": configs.get("logo_url","https://i.postimg.cc/SsCZVFwp/Logo-Icono2.jpg"), "logoUrl": configs.get("logoUrl","https://i.postimg.cc/SsCZVFwp/Logo-Icono2.jpg"), "menuConfig": menuConfig, "ownerEmail": configs.get("ownerEmail","totalappgt@gmail.com"), "inactividadMinutos": int(configs.get("inactividadMinutos","60")), "metaGrupos": configs.get("metaGrupos","407"), "driveFolderId": configs.get("driveFolderId","1OHBSDIk7e1FOyC1tgkkAJoRb_nJh2CKM"), "botPdfFolderId": configs.get("botPdfFolderId",""), "pdf_id": configs.get("pdf_id",""), "gemini_api_key": configs.get("gemini_api_key",""), "openrouter_api_key": configs.get("openrouter_api_key",""), "deepseek_api_key": configs.get("deepseek_api_key",""), "telegram_token": configs.get("telegram_token", os.getenv("TELEGRAM_TOKEN", "")), "telegram_chat_id": configs.get("telegram_chat_id", os.getenv("TELEGRAM_CHAT_ID", "")),
            "firebaseApiKey": configs.get("firebaseApiKey", os.getenv("FIREBASE_API_KEY", "")),
            "firebaseAuthDomain": configs.get("firebaseAuthDomain", os.getenv("FIREBASE_AUTH_DOMAIN", "totalappgt-d15b9.firebaseapp.com")),
            "firebaseProjectId": configs.get("firebaseProjectId", os.getenv("FIREBASE_PROJECT_ID", "totalappgt-d15b9")),
            "firebaseAppId": configs.get("firebaseAppId", os.getenv("FIREBASE_APP_ID", "")), "whatsapp_soporte": configs.get("whatsapp_soporte","+502 5830-3182"), "nombre_soporte": configs.get("nombre_soporte","Total App GT - Daniel Martínez"), "titleMantenimiento": configs.get("titleMantenimiento","Sistema en Mantenimiento"), "msgMantenimiento": configs.get("msgMantenimiento","El sistema no está disponible en este momento."), "bot_habilitado": configs.get("bot_habilitado","True") == "True", "ai_provider": configs.get("ai_provider","auto"), "servicios_dinamicos": [], "cron_lunes": configs.get("cron_lunes","Lunes 6:30 PM"), "cron_jueves": configs.get("cron_jueves","Jueves 6:30 PM"), "cron_domTarde": configs.get("cron_domTarde","Domingo 10:30 AM"), "theme_colors": configs.get("theme_colors",""), "smtp_user": configs.get("smtp_user","totalappgt@gmail.com"), "smtp_password": configs.get("smtp_password", os.getenv("RESEND_API_KEY",""))}

        if action == "guardarPDF":
            no_serie = payload.get("noSerie", "").strip()
            pdf_b64 = payload.get("pdfBase64", "")
            if not no_serie or not pdf_b64:
                return {"ok": False, "msg": "noSerie y pdfBase64 requeridos"}
            if pdf_b64.startswith("data:"):
                pdf_b64 = pdf_b64.split(",",1)[-1]
            gr = db.query(GeneradorReporte).filter(GeneradorReporte.no_serie == no_serie).first()
            if not gr:
                return {"ok": False, "msg": "Reporte no encontrado"}
            gr.pdf_data = pdf_b64
            gr.archivo_generado = f"/api/pdf/{no_serie}"
            db.commit()
            return {"ok": True, "msg": "PDF guardado"}
            for key, val in payload.items():
                if key in ("token", "action"): continue
                existing = db.query(Configuracion).filter(Configuracion.clave == key).first()
                if existing: existing.valor = str(val)
                else: db.add(Configuracion(clave=key, valor=str(val)))
            db.commit()
            return {"ok": True}

        if action == "changePassword":
            import re
            email = payload.get("email", "")
            old_password = payload.get("old_password", "")
            new_password = payload.get("new_password", "")
            if not all([email, old_password, new_password]):
                return {"ok": False, "msg": "Todos los campos son requeridos"}
            if len(new_password) < 8 or not re.search(r"[A-Z]", new_password) or not re.search(r"[a-z]", new_password) or not re.search(r"\d", new_password):
                return {"ok": False, "msg": "La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número"}
            user = db.query(Usuario).filter(Usuario.email == email).first()
            if not user or not bcrypt.checkpw(old_password.encode(), user.password.encode()):
                return {"ok": False, "msg": "Contraseña actual incorrecta"}
            user.password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            db.commit()
            return {"ok": True, "msg": "Contraseña actualizada"}

        if action == "inicializarSistema":
            return {"ok": True, "msg": "Sistema listo. Configura tu bot de Telegram en Config."}

        # ── SEGUIMIENTOS (returns raw array) ──
        if action == "getSeguimientos":
            return [{"ID": s.id, "Fecha": str(s.fecha) if s.fecha else "", "Persona": s.persona, "Tipo": s.tipo, "Responsable": s.responsable, "Estado": s.estado, "Observaciones": s.observaciones} for s in db.query(Seguimiento).order_by(Seguimiento.fecha.desc()).limit(200).all()]

        if action == "saveSeguimiento":
            return save_entity(db, Seguimiento, {"Persona":"persona","Tipo":"tipo","Responsable":"responsable","Estado":"estado","Observaciones":"observaciones"}, payload)

        if action == "deleteSeguimiento":
            return delete_entity(db, Seguimiento, payload)

        # ── SUPERVISORES / PASTORES / AYUDA (wrapped in {ok, data}) ──
        if action == "getSupervisores":
            return {"ok": True, "data": [db_to_gas(s, SUPERVISOR_MAP) for s in db.query(Supervisor).all()]}

        if action == "saveSupervisor":
            return save_entity(db, Supervisor, SUPERVISOR_MAP, payload)

        if action == "deleteSupervisor":
            return delete_entity(db, Supervisor, payload)

        if action == "getPastores":
            return {"ok": True, "data": [db_to_gas(p, PASTOR_MAP) for p in db.query(Pastore).all()]}

        if action == "savePastor":
            return save_entity(db, Pastore, PASTOR_MAP, payload)

        if action == "deletePastor":
            return delete_entity(db, Pastore, payload)

        if action == "getAyudaPastor":
            return {"ok": True, "data": [db_to_gas(a, AYUDA_PASTOR_MAP) for a in db.query(AyudaPastor).all()]}

        if action == "saveAyudaPastor":
            return save_entity(db, AyudaPastor, AYUDA_PASTOR_MAP, payload)

        if action == "deleteAyudaPastor":
            return delete_entity(db, AyudaPastor, payload)

        # ── CONTACTOS (raw array) ──
        if action == "getContactos":
            return [db_to_gas(c, CONTACTO_MAP) for c in db.query(Contacto).all()]

        if action == "saveContacto":
            return save_entity(db, Contacto, CONTACTO_MAP, payload, id_key="IDContacto")

        if action == "deleteContacto":
            return delete_entity(db, Contacto, payload)

        if action == "deleteAllContactos":
            try:
                count = db.query(Contacto).count()
                db.query(Contacto).delete()
                db.commit()
                return {"ok": True, "msg": f"{count} contactos eliminados"}
            except Exception as e:
                return {"ok": False, "msg": str(e)}

        # ── DIEZMOS (raw array) ──
        if action == "getDiezmos":
            q = db.query(Diezmo)
            if payload.get("desde"): q = q.filter(Diezmo.fecha >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Diezmo.fecha <= payload["hasta"])
            return [db_to_gas(d, DIEZMO_MAP) for d in q.all()]

        if action == "saveDiezmo":
            return save_entity(db, Diezmo, DIEZMO_MAP, payload)

        if action == "deleteDiezmo":
            return delete_entity(db, Diezmo, payload)

        # ── GASTOS (returns {ok, gastos}) ──
        if action == "getGastos":
            q = db.query(Gasto)
            if payload.get("evento"): q = q.filter(Gasto.evento == payload["evento"])
            if payload.get("desde"): q = q.filter(Gasto.fecha >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Gasto.fecha <= payload["hasta"])
            return {"ok": True, "gastos": [db_to_gas(g, GASTO_MAP) for g in q.all()]}

        if action == "saveGasto":
            return save_entity(db, Gasto, GASTO_MAP, payload, id_key="id")

        if action == "deleteGasto":
            return delete_entity(db, Gasto, payload)

        # ── INVENTARIO (raw array) ──
        if action == "getInventario":
            return [db_to_gas(i, INVENTARIO_MAP) for i in db.query(Inventario).all()]

        if action == "saveInventario":
            return save_entity(db, Inventario, INVENTARIO_MAP, payload)

        if action == "deleteInventario":
            return delete_entity(db, Inventario, payload)

        # ── INSUMOS (raw array) ──
        if action == "getInsumos":
            return [db_to_gas(i, INSUMO_MAP) for i in db.query(Insumo).all()]

        if action == "saveInsumo":
            return save_entity(db, Insumo, INSUMO_MAP, payload)

        if action == "deleteInsumo":
            return delete_entity(db, Insumo, payload)

        # ── PRIVILEGIOS (raw array) ──
        if action == "getPrivilegios":
            return [db_to_gas(p, PRIVILEGIO_MAP) for p in db.query(Privilegio).all()]

        if action == "savePrivilegio":
            return save_entity(db, Privilegio, PRIVILEGIO_MAP, payload)

        if action == "deletePrivilegio":
            return delete_entity(db, Privilegio, payload)

        # ── CRONOGRAMA (wrapped) ──
        if action == "getCronograma":
            return {"ok": True, "data": [db_to_gas(c, CRONOGRAMA_MAP) for c in db.query(Cronograma).all()]}

        if action == "saveCronograma":
            return save_entity(db, Cronograma, CRONOGRAMA_MAP, payload)

        if action == "deleteCronograma":
            return delete_entity(db, Cronograma, payload)

        # ── BAUTIZOS ──
        if action == "getBautizos":
            q = db.query(Bautizo).order_by(Bautizo.fecha.desc())
            if payload.get("desde"): q = q.filter(Bautizo.fecha >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Bautizo.fecha <= payload["hasta"])
            return [db_to_gas(b, BAUTIZO_MAP) for b in q.all()]

        if action == "saveBautizo":
            return save_entity(db, Bautizo, BAUTIZO_MAP, payload)

        if action == "deleteBautizo":
            return delete_entity(db, Bautizo, payload)

        # ── BITACORA (raw array) ──
        if action == "getBitacora":
            q = db.query(Bitacora).order_by(Bitacora.fecha_hora.desc()).limit(500)
            if payload.get("desde"): q = q.filter(Bitacora.fecha_hora >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Bitacora.fecha_hora <= payload["hasta"])
            if payload.get("rol"): q = q.filter(Bitacora.rol == payload["rol"])
            return [db_to_gas(b, BITACORA_MAP) for b in q.all()]

        if action == "limpiarBitacora":
            db.query(Bitacora).delete(); db.commit()
            return {"ok": True}

        # ── ENVIOS (raw array) ──
        if action == "getEnvios":
            return [db_to_gas(e, ENVIO_MAP) for e in db.query(Envio).all()]

        if action == "deleteEnvio":
            return delete_entity(db, Envio, payload)

        # ── USUARIOS (raw array) ──
        if action == "getUsuarios":
            return [{"ID": u.id, "Nombre": u.nombre, "Email": u.email, "Rol": u.rol, "Activo": "SI" if u.activo else "NO", "MenuPermitido": u.menu_permitido or "", "PuedeVerBitacora": "SI" if u.puede_ver_bitacora else "NO"} for u in db.query(Usuario).all()]

        if action == "saveUsuario":
            item_id = payload.get("ID")
            email = payload.get("Email","").strip().lower()
            if not email:
                return {"ok": False, "msg": "Email requerido"}
            exist = db.query(Usuario).filter(Usuario.email == email).first()
            if exist and (not item_id or int(exist.id) != int(item_id)):
                return {"ok": False, "msg": "Ya existe un usuario con el email: " + email}
            data = payload_to_kwargs(USUARIO_MAP, payload)
            if not item_id:
                data.pop("id", None)  # Remover ID vacio para nuevos
            # Normalizar rol a minúscula
            if "rol" in data and data["rol"]:
                data["rol"] = str(data["rol"]).lower().strip()
            # Convertir MenuPermitido a JSON string si es lista
            if "menu_permitido" in data and isinstance(data["menu_permitido"], list):
                data["menu_permitido"] = json.dumps(data["menu_permitido"])
            password = payload.get("Password", "")
            if password: data["password"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            # Convertir strings SI/NO a booleanos
            if "activo" in data:
                data["activo"] = str(data["activo"]).upper() in ("SI", "TRUE", "1", "YES")
            if "puede_ver_bitacora" in data:
                data["puede_ver_bitacora"] = str(data["puede_ver_bitacora"]).upper() in ("SI", "TRUE", "1", "YES")
            if item_id:
                obj = db.query(Usuario).filter(Usuario.id == item_id).first()
                if not obj: return {"ok": False, "msg": "Usuario no encontrado"}
                for key, val in data.items(): setattr(obj, key, val)
            else:
                if "password" not in data: data["password"] = bcrypt.hashpw(b"redil2026", bcrypt.gensalt()).decode()
                obj = Usuario(**data)
                db.add(obj)
            db.commit()
            return {"ok": True}

        if action == "deleteUsuario":
            return delete_entity(db, Usuario, payload)

        # ── GENERADORES (raw array) ──
        if action == "getGeneradores":
            return [db_to_gas(g, GENERADOR_MAP) for g in db.query(GeneradorReporte).all()]

        # ── FORM URL ──
        if action == "getFormUrl":
            c = db.query(Configuracion).filter(Configuracion.clave == "formUrlPublic").first()
            url = c.valor if c else f"{_get_system_url()}/formulario_digital.html"
            return {"ok": True, "url": url}

        if action == "getFormHtml":
            # Buscar en múltiples ubicaciones posibles
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            possible_paths = [
                os.path.join(base, "static", "formulario_digital.html"),
                os.path.join(os.getcwd(), "static", "formulario_digital.html"),
                os.path.join(os.getcwd(), "app", "static", "formulario_digital.html"),
            ]
            html_content = None
            for p in possible_paths:
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    break
            if html_content:
                return {"ok": True, "html": html_content}
            return {"ok": False, "msg": f"Formulario no encontrado. Buscado en: {possible_paths}"}

        # ── REPORTE FINANCIERO ──
        if action == "getReporteFinancieroDistrito":
            q = db.query(Reporte.distrito, Reporte.zona, func.count(Reporte.id).label("total_reportes"), func.coalesce(func.sum(Reporte.asistencia), 0).label("total_asistencia"), func.coalesce(func.sum(Reporte.ofrenda_total), 0).label("total_ofrenda"))
            if payload.get("desde"): q = q.filter(Reporte.fecha >= payload["desde"])
            if payload.get("hasta"): q = q.filter(Reporte.fecha <= payload["hasta"])
            rows = q.group_by(Reporte.distrito, Reporte.zona).all()
            data = [{"distrito": r.distrito or "", "zona": r.zona or "", "reportes": r.total_reportes, "asistencia": int(r.total_asistencia), "ofrendaTotal": float(r.total_ofrenda), "ofrendaRecibida": 0, "pendientes": 0} for r in rows]
            total_reportes = sum(r["reportes"] for r in data)
            total_asistencia = sum(r["asistencia"] for r in data)
            total_ofrenda = sum(r["ofrendaTotal"] for r in data)
            return {"ok": True, "byZona": data, "totalReportes": total_reportes, "totalAsistencia": total_asistencia, "totalOfrenda": round(total_ofrenda, 2)}

        # ── CUADRE DOMINICAL ──
        if action == "getCuadreDominical":
            fecha = payload.get("fecha", "")
            lideres = db.query(Hermano).filter(Hermano.codigo_lead != None).all()
            reportes_q = db.query(Reporte)
            if fecha:
                try:
                    d = datetime.strptime(fecha, "%Y-%m-%d").date()
                    ini = d - timedelta(days=d.weekday())  # Lunes
                    fin = ini + timedelta(days=6)  # Domingo
                    reportes_q = reportes_q.filter(Reporte.fecha >= ini, Reporte.fecha <= fin)
                except:
                    reportes_q = reportes_q.filter(Reporte.fecha == fecha)
            reportes = reportes_q.all()
            codigos_reportados = set(r.codigo for r in reportes)
            data, total_lideres, entregaron, pendientes_c, ofrenda_total = [], 0, 0, 0, 0.0
            # Agrupar por distrito
            distritos = {}
            for h in lideres:
                total_lideres += 1
                reporto = h.codigo_lead in codigos_reportados
                rpts = [r for r in reportes if r.codigo == h.codigo_lead]
                ofrenda = sum(float(r.ofrenda_total or 0) for r in rpts)
                ofrenda_total += ofrenda
                if reporto: entregaron += 1
                else: pendientes_c += 1
                d = str(h.distrito or "?")
                z = str(h.zona or "?")
                item = {"codigo": h.codigo_lead or "", "nombre": h.nombre or "", "tieneReporte": reporto, "ofrendaTotal": round(ofrenda, 2), "ofrendaRecibida": True if rpts and rpts[0].ofrenda_recibida not in ("Pendiente", "", None) else False, "pastorZona": h.pastor_zona or "", "supSector": h.sup_sector or "", "distrito": d, "zona": z}
                data.append(item)
                if d not in distritos: distritos[d] = {"distrito": d, "totalLideres": 0, "entregaron": 0, "pendientes": 0, "ofrendaTotal": 0.0, "zonas": {}}
                distritos[d]["totalLideres"] += 1
                if reporto: distritos[d]["entregaron"] += 1
                else: distritos[d]["pendientes"] += 1
                distritos[d]["ofrendaTotal"] += ofrenda
                if z not in distritos[d]["zonas"]: distritos[d]["zonas"][z] = {"zona": z, "totalLideres": 0, "entregaron": 0, "pendientes": 0, "ofrendaTotal": 0.0, "lideres": []}
                distritos[d]["zonas"][z]["totalLideres"] += 1
                if reporto: distritos[d]["zonas"][z]["entregaron"] += 1
                else: distritos[d]["zonas"][z]["pendientes"] += 1
                distritos[d]["zonas"][z]["ofrendaTotal"] += ofrenda
                distritos[d]["zonas"][z]["lideres"].append(item)
            # Convertir zonas de dict a lista ordenada
            distritos_list = []
            for dk in sorted(distritos.keys()):
                dg = distritos[dk]
                zonas_list = []
                for zk in sorted(dg["zonas"].keys()):
                    zg = dg["zonas"][zk]
                    zg["ofrendaTotal"] = round(zg["ofrendaTotal"], 2)
                    zonas_list.append(zg)
                dg["zonas"] = zonas_list
                dg["ofrendaTotal"] = round(dg["ofrendaTotal"], 2)
                distritos_list.append(dg)
            generar_pdf = payload.get("generarPDF", False)
            result = {"ok": True, "data": data, "agrupado": distritos_list, "totalLideres": total_lideres, "entregaron": entregaron, "pendientes": pendientes_c, "ofrendaTotal": round(ofrenda_total, 2)}
            if generar_pdf:
                try:
                    from fpdf import FPDF
                    from datetime import datetime as dt2
                    sys_nom = ""
                    try:
                        cfg2 = db.query(Configuracion).filter(Configuracion.clave == "nombre").first()
                        if cfg2: sys_nom = cfg2.valor
                    except: pass
                    today_str = dt2.now().strftime('%Y%m%d')
                    count = db.query(GeneradorReporte).filter(GeneradorReporte.no_serie.like(f'%cuadre_{today_str}%')).count() + 1
                    no_serie = f"cuadre_{today_str}_{count:03d}"
                    fecha_gen = dt2.now().strftime('%d/%m/%Y %I:%M %p')
                    pdf = FPDF('L','mm','Letter'); pdf.set_auto_page_break(True,10); pdf.add_page(); pdf.set_margin(10)
                    w=pdf.w-20; cx=10
                    pdf.set_fill_color(26,58,92); pdf.rect(0,0,pdf.w,24,'F')
                    pdf.set_text_color(255,255,255); pdf.set_font('Helvetica','B',16)
                    pdf.set_xy(cx,4); pdf.cell(w*0.6,7,pdf_safe(sys_nom or'REDIL')[:35],0,0,'L')
                    pdf.set_font('Helvetica','',8); pdf.set_text_color(185,205,230)
                    pdf.set_xy(cx,13); pdf.cell(w*0.6,4,f'Cuadre Dominical - {fecha or "Hoy"} - {fecha_gen}',0,0,'L')
                    bw,bh=58,14; bx=pdf.w-cx-bw; by=5
                    pdf.set_fill_color(255,255,255); pdf.rect(bx,by,bw,bh,'F'); pdf.set_draw_color(26,58,92); pdf.rect(bx,by,bw,bh,'D')
                    pdf.set_text_color(26,58,92); pdf.set_font('Helvetica','B',11)
                    pdf.set_xy(bx,by+1); pdf.cell(bw,7,no_serie,0,0,'C')
                    pdf.set_font('Helvetica','',7); pdf.set_text_color(100,115,135)
                    pdf.set_xy(bx,by+8); pdf.cell(bw,4,f'{total_lideres} lideres',0,0,'C')
                    # KPIs
                    colors=[(99,102,241),(16,185,129),(239,68,68),(249,115,22)]
                    kpi_data=[('Lideres',str(total_lideres)),('Entregaron',str(entregaron)),('Pendientes',str(pendientes_c)),('Ofrenda',pdf_safe(f'Q{ofrenda_total:,.2f}'))]
                    cw4=(w-9)/4; ch4=18; gap=3; y0=29
                    for i,(lbl,val) in enumerate(kpi_data):
                        x=cx+i*(cw4+gap); y=y0
                        pdf.set_fill_color(250,252,255); pdf.set_draw_color(220,228,240); pdf.rect(x,y,cw4,ch4,'DF')
                        cr,cg,cb=colors[i]; pdf.set_fill_color(cr,cg,cb); pdf.rect(x+1,y+2,3,ch4-4,'F')
                        pdf.set_text_color(cr,cg,cb); pdf.set_font('Helvetica','B',12)
                        pdf.set_xy(x+7,y+2); pdf.cell(cw4-10,8,val,0,0,'L')
                        pdf.set_font('Helvetica','',6.5); pdf.set_text_color(130,140,155)
                        pdf.set_xy(x+7,y+11); pdf.cell(cw4-10,4,lbl.upper(),0,0,'L')
                    # Table
                    tbl_y=y0+ch4+10; rh=5
                    cols=[('Codigo',18),('Lider',50),('D-Z',16),('Pastor Zona',42),('Sup.Sector',38),('Estado',24),('Ofrenda',22)]
                    cw_list=[c[1] for c in cols]; ch_headers=[c[0] for c in cols]
                    pdf.set_fill_color(26,58,92); pdf.set_text_color(255,255,255); pdf.set_font('Helvetica','B',7)
                    pdf.set_y(tbl_y)
                    for ci,cwv in enumerate(cw_list): pdf.set_xy(sum(cw_list[:ci])+cx,tbl_y); pdf.cell(cwv,6,ch_headers[ci],0,0,'C',True)
                    y=tbl_y+6; max_rows=int((190-y)/rh)
                    for ri,lid in enumerate(data):
                        if ri>0 and ri%max_rows==0:
                            pdf.add_page(); y=12; pdf.set_fill_color(26,58,92)
                            pdf.set_y(y)
                            for ci2,cwv2 in enumerate(cw_list): pdf.set_xy(sum(cw_list[:ci2])+cx,y); pdf.cell(cwv2,6,ch_headers[ci2],0,0,'C',True)
                            y+=6
                        pdf.set_fill_color(252,254,255) if ri%2==0 else pdf.set_fill_color(246,249,253)
                        tiene=lid.get("tieneReporte",False); of_v=lid.get("ofrendaTotal",0)
                        vals=[pdf_safe(lid.get("codigo","-"))[:8],pdf_safe(lid.get("nombre","-"))[:30],f'D{pdf_safe(lid.get("distrito","?"))} Z{pdf_safe(lid.get("zona","?"))}',pdf_safe(lid.get("pastorZona","-"))[:24],pdf_safe(lid.get("supSector","-"))[:22],'',f'Q{of_v:,.2f}' if of_v else '-']
                        for vi,cwv3 in enumerate(cw_list):
                            xpos=sum(cw_list[:vi])+cx
                            if vi==5:
                                if not tiene:
                                    pdf.set_fill_color(254,238,238); pdf.set_draw_color(240,190,190); pdf.rect(xpos+1,y+0.5,cwv3-4,rh-1,'DF')
                                    pdf.set_text_color(200,40,40)
                                else:
                                    pdf.set_fill_color(234,252,240); pdf.set_draw_color(175,225,195); pdf.rect(xpos+1,y+0.5,cwv3-4,rh-1,'DF')
                                    pdf.set_text_color(5,150,105)
                                pdf.set_font('Helvetica','B',6); pdf.set_xy(xpos,y)
                                pdf.cell(cwv3,rh,'Pendiente'if not tiene else'Entregado',0,0,'C')
                            else:
                                pdf.set_text_color(50,60,75); pdf.set_xy(xpos,y); pdf.set_font('Helvetica','',6.5)
                                pdf.cell(cwv3,rh,vals[vi],0,0,'L'if vi<2 else'C',True)
                        y+=rh
                    pdf.set_y(y+4); pdf.set_draw_color(180,195,215); pdf.set_line_width(0.4)
                    pdf.line(cx,pdf.get_y(),pdf.w-cx,pdf.get_y())
                    pdf.set_font('Helvetica','B',7.5); pdf.set_text_color(26,58,92)
                    pdf.set_xy(cx,pdf.get_y()+2); pdf.cell(w*0.5,5,f'{total_lideres} lideres - Q{ofrenda_total:,.2f}',0,0,'L')
                    pdf.set_font('Helvetica','',6.5); pdf.set_text_color(140,150,165)
                    pdf.set_xy(cx,pdf.get_y()+6); pdf.cell(w,5,'Daniel Martinez - Total App GT',0,0,'R')
                    pdf_b64 = base64.b64encode(pdf.output()).decode()
                    gr = GeneradorReporte(
                        no_serie=no_serie, fecha_inicio=fecha or None, fecha_fin=fecha or None,
                        total_ofrenda=round(ofrenda_total,2), total_asistencia=total_lideres,
                        titulo_reporte="Cuadre Dominical", archivo_generado=f"/api/pdf/{no_serie}"
                    )
                    gr.pdf_data = pdf_b64; db.add(gr); db.commit()
                    result["pdfUrl"] = f"/api/pdf/{no_serie}"; result["pdfSerie"] = no_serie
                except Exception as e:
                    result["pdfError"] = str(e)
                    print(f"PDF cuadre fallo: {e}")
            return result

        # ── CARGA MASIVA ──
        if action == "getEncabezadosCargaMasiva":
            tipo = payload.get("tipo", "")
            headers_map = {"hermanos": ['ID','CodigoL','NombreL','Distrito','Zona','Area','Sector','Grupo','Anfitrion','Direccion','Sup SectorL','Sup AreaL','Ayuda Pastor','Pastor Zona','CodigoSup','CodigoPastor'], "supervisores": ['ID','CodigoSup','NombreSup','Distrito','Zona','Area','Sector','Telefono','Email','Direccion','Activo'], "pastores": ['ID','CodigoPastor','NombrePastor','Distrito','Zona','Telefono','Email','Direccion','Activo'], "ayudapastor": ['ID','CodigoAyuda','NombreAyuda','Distrito','Zona','Area','Telefono','Email','Direccion','Activo']}
            return {"ok": True, "data": headers_map.get(tipo, [])}

        if action == "importarDatosMasivos":
            tipo = payload.get("tipo", ""); rows = payload.get("rows", [])
            if not rows: return {"ok": False, "msg": "No hay datos para importar"}
            tipo_map = {"hermanos": (Hermano, HERMANO_MAP), "supervisores": (Supervisor, SUPERVISOR_MAP), "pastores": (Pastore, PASTOR_MAP), "ayudapastor": (AyudaPastor, AYUDA_PASTOR_MAP)}
            pair = tipo_map.get(tipo)
            if not pair: return {"ok": False, "msg": f"Tipo '{tipo}' no soportado"}
            model_class, field_map = pair
            insertados = 0
            for row in rows:
                data = payload_to_kwargs(field_map, row)
                if data: db.add(model_class(**data)); insertados += 1
            db.commit()
            return {"ok": True, "msg": f"{insertados} registros importados"}

        # ── MISC ──
        if action == "invalidateDashCache":
            return {"ok": True}

        if action == "preguntarAI":
            pregunta = payload.get("pregunta", "")
            if not pregunta: return {"ok": False, "msg": "Pregunta requerida"}
            c = db.query(Configuracion).filter(Configuracion.clave == "gemini_api_key").first()
            api_key = c.valor if c else os.getenv("GEMINI_API_KEY", "")
            if not api_key: return {"ok": False, "msg": "API key de Gemini no configurada"}
            try:
                resp = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}", json={"contents": [{"parts": [{"text": pregunta}]}]}, timeout=30)
                if resp.status_code == 200:
                    parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    return {"ok": True, "respuesta": parts[0].get("text","") if parts else ""}
                return {"ok": False, "msg": f"Error Gemini API: {resp.status_code}"}
            except Exception as e: return {"ok": False, "msg": str(e)}

        # ── ENVÍO DE CORREOS ──
        if action == "enviarReportesPorSeries":
            dest = payload.get("destinatarios", "")
            series = payload.get("series", [])
            asunto = payload.get("asunto", "")
            cuerpo = payload.get("cuerpo", "")
            emails_list = [e.strip() for e in dest.replace(";", ",").split(",") if e.strip()]
            if not emails_list: return {"ok": False, "msg": "Sin destinatarios"}
            cfg_dict = {}
            for c in db.query(Configuracion).all(): cfg_dict[c.clave] = c.valor
            sys_nom = cfg_dict.get("nombre", "REDIL")
            smtp_user = cfg_dict.get("smtp_user", "totalappgt@gmail.com")
            smtp_password = cfg_dict.get("smtp_password", os.getenv("RESEND_API_KEY",""))
            gen_records = db.query(GeneradorReporte).filter(GeneradorReporte.no_serie.in_(series)).all()
            if not gen_records: return {"ok": False, "msg": f"No se encontraron reportes: {','.join(series)}"}
            html_parts = []
            total_asist, total_of, total_rptes = 0, 0, 0
            for gr in gen_records:
                q = db.query(Reporte)
                if gr.fecha_inicio: q = q.filter(Reporte.fecha >= gr.fecha_inicio)
                if gr.fecha_fin: q = q.filter(Reporte.fecha <= gr.fecha_fin)
                if gr.filtro_lider: q = q.filter(Reporte.lider == gr.filtro_lider)
                if gr.filtro_sup_area: q = q.filter(Reporte.sup_area == gr.filtro_sup_area)
                if gr.filtro_distrito: q = q.filter(Reporte.distrito == gr.filtro_distrito)
                if gr.filtro_zona: q = q.filter(Reporte.zona == gr.filtro_zona)
                rep_rows = q.order_by(Reporte.lider).all()
                total_rptes += len(rep_rows)
                by_lider = {}
                for r in rep_rows:
                    ln = r.lider or "Sin líder"
                    if ln not in by_lider:
                        by_lider[ln] = {"cod": r.codigo or "", "rptes": 0, "agf": 0, "hnos": 0, "amigos": 0, "ninos": 0, "of": 0, "pend": 0}
                    by_lider[ln]["rptes"] += 1
                    by_lider[ln]["agf"] += r.asistencia or 0
                    by_lider[ln]["hnos"] += r.hnos or 0
                    by_lider[ln]["amigos"] += r.amigos or 0
                    by_lider[ln]["ninos"] += r.ninos or 0
                    by_lider[ln]["of"] += float(r.ofrenda_total or 0)
                    if r.ofrenda_recibida in ("Pendiente", ""): by_lider[ln]["pend"] += 1
                asist_gr = sum(v["agf"] for v in by_lider.values())
                of_gr = sum(v["of"] for v in by_lider.values())
                total_asist += asist_gr; total_of += of_gr
                lider_rows = "".join(
                    f'<tr>'
                    f'<td style="padding:6px 10px;font-weight:700">{esc(ln)}{" <span style=color:#e74c3c>⚠"+str(v["pend"])+"</span>" if v["pend"] else ""}</td>'
                    f'<td style="padding:6px 10px;text-align:center">{v["cod"]}</td>'
                    f'<td style="padding:6px 10px;text-align:center">{v["rptes"]}</td>'
                    f'<td style="padding:6px 10px;text-align:center;font-weight:800">{v["agf"]}</td>'
                    f'<td style="padding:6px 10px;text-align:center">{v["hnos"]}</td>'
                    f'<td style="padding:6px 10px;text-align:center">{v["amigos"]}</td>'
                    f'<td style="padding:6px 10px;text-align:center">{v["ninos"]}</td>'
                    f'<td style="padding:6px 10px;text-align:right;font-weight:800">Q{v["of"]:.2f}</td></tr>'
                    for ln, v in sorted(by_lider.items())
                )
                fecha_desde = gr.fecha_inicio.strftime("%d/%m/%Y") if gr.fecha_inicio else "—"
                fecha_hasta = gr.fecha_fin.strftime("%d/%m/%Y") if gr.fecha_fin else "—"
                html_parts.append(f'''
                <div style="margin-bottom:24px;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1)">
                  <table width="100%" style="background:linear-gradient(135deg,#1a3a5c,#2563a8);color:#fff">
                    <tr>
                      <td style="padding:10px 14px;vertical-align:middle">
                        <div style="font-size:11px;opacity:.7;text-transform:uppercase;letter-spacing:1px">Reporte</div>
                        <div style="font-size:20px;font-weight:900">{gr.no_serie}</div>
                        <div style="font-size:12px;opacity:.8">{gr.titulo_reporte}</div>
                      </td>
                      <td style="padding:10px 14px;text-align:right;vertical-align:middle">
                        <div style="font-size:13px;opacity:.7">{fecha_desde} → {fecha_hasta}</div>
                        <div style="font-size:24px;font-weight:900;margin-top:2px">{len(rep_rows)}</div>
                        <div style="font-size:11px;opacity:.7">grupos</div>
                      </td>
                    </tr>
                  </table>
                  <table width="100%" style="border-collapse:collapse;background:#fff">
                    <tr>
                      <td style="padding:10px 6px;text-align:center;border-right:1px solid #eef0f5;vertical-align:middle">
                        <div style="font-size:18px;font-weight:900;color:#1a3a5c">{asist_gr}</div>
                        <div style="font-size:9px;color:#888;margin-top:2px">Asistencia</div>
                      </td>
                      <td style="padding:10px 6px;text-align:center;border-right:1px solid #eef0f5;vertical-align:middle">
                        <div style="font-size:18px;font-weight:900;color:#1e7e34">{sum(v["hnos"] for v in by_lider.values())}</div>
                        <div style="font-size:9px;color:#888;margin-top:2px">Hnos</div>
                      </td>
                      <td style="padding:10px 6px;text-align:center;border-right:1px solid #eef0f5;vertical-align:middle">
                        <div style="font-size:18px;font-weight:900;color:#2563a8">{sum(v["amigos"] for v in by_lider.values())}</div>
                        <div style="font-size:9px;color:#888;margin-top:2px">Amigos</div>
                      </td>
                      <td style="padding:10px 6px;text-align:center;border-right:1px solid #eef0f5;vertical-align:middle">
                        <div style="font-size:18px;font-weight:900;color:#7d3c98">{sum(v["ninos"] for v in by_lider.values())}</div>
                        <div style="font-size:9px;color:#888;margin-top:2px">Niños</div>
                      </td>
                      <td style="padding:10px 6px;text-align:center;border-right:1px solid #eef0f5;vertical-align:middle">
                        <div style="font-size:18px;font-weight:900;color:#c87f00">Q{of_gr:.2f}</div>
                        <div style="font-size:9px;color:#888;margin-top:2px">Ofrenda</div>
                      </td>
                    </tr>
                  </table>
                  <table style="width:100%;border-collapse:collapse;font-size:12px;background:#fff">
                    <thead><tr style="background:#f0f4ff">
                      <th style="padding:6px 10px;text-align:left;font-size:11px">Líder</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">Cód</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">Rptes</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">AGF</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">Hnos</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">Amigos</th>
                      <th style="padding:6px 10px;text-align:center;font-size:11px">Niños</th>
                      <th style="padding:6px 10px;text-align:right;font-size:11px">Ofrenda</th>
                    </tr></thead>
                    <tbody>{lider_rows}</tbody>
                  </table>
                </div>''')
            subj = asunto or f"{sys_nom} · Informes · {datetime.now().strftime('%d/%m/%Y')}"
            logo_url = cfg_dict.get("logo_url", "")
            logo_html = f'<img src="{logo_url}" style="height:40px;vertical-align:middle;margin-right:10px">' if logo_url else ""
            full_html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body style="font-family:Arial,sans-serif;background:#f0f4f8;padding:20px">
              <div style="max-width:700px;margin:0 auto">
                <div style="text-align:center;padding:16px 0;color:#1a3a5c">
                  {logo_html}<span style="font-size:22px;font-weight:900">{sys_nom}</span>
                </div>
                {cuerpo + "<br><br>" if cuerpo else ""}
                {"".join(html_parts)}
                <div style="text-align:center;padding:16px;font-size:11px;color:#999">
                  {sys_nom} · Sistema de Reportes · {datetime.now().strftime('%d/%m/%Y %H:%M')}
                </div>
              </div></body></html>'''
            attachments = []
            for gr in gen_records:
                if gr.pdf_data:
                    safe_name = f"redil_{gr.titulo_reporte or 'reporte'}_{gr.no_serie}.pdf".replace(" ", "_")
                    attachments.append({"filename": safe_name, "content": gr.pdf_data})
            try:
                send_email(emails_list, subj, full_html, smtp_user=smtp_user, smtp_password=smtp_password, attachments=attachments if attachments else None)
                estado = "Enviado"
            except Exception as e:
                estado = f"Error: {str(e)}"
            db.add(Envio(fecha_envio=datetime.utcnow(), asunto=subj, mensaje=cuerpo, archivos_a_enviar=",".join(series), destinatarios=",".join(emails_list), estado=estado))
            db.commit()
            if estado != "Enviado":
                return {"ok": False, "msg": estado}
            return {"ok": True, "msg": "Enviado", "enviados": len(emails_list)}

        if action == "enviarReporte":
            dest = payload.get("destinatarios", "")
            asunto = payload.get("asunto", "")
            cuerpo = payload.get("cuerpo", "")
            filtros = payload.get("filtros", {})
            emails_list = [e.strip() for e in dest.replace(";", ",").split(",") if e.strip()]
            if not emails_list: return {"ok": False, "msg": "Sin destinatarios"}
            cfg_dict = {}
            for c in db.query(Configuracion).all(): cfg_dict[c.clave] = c.valor
            sys_nom = cfg_dict.get("nombre", "REDIL")
            smtp_user = cfg_dict.get("smtp_user", "totalappgt@gmail.com")
            smtp_password = cfg_dict.get("smtp_password", os.getenv("RESEND_API_KEY",""))
            subj = asunto or f"{sys_nom} · Informe · {datetime.now().strftime('%d/%m/%Y')}"
            full_html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body style="font-family:Arial,sans-serif;padding:20px">
              <div style="max-width:600px;margin:0 auto"><h2 style="color:#1a3a5c">{sys_nom}</h2>
              {cuerpo or "<p>Se adjunta el informe solicitado.</p>"}</div></body></html>'''
            try:
                send_email(emails_list, subj, full_html, smtp_user=smtp_user, smtp_password=smtp_password)
                estado = "Enviado"
            except Exception as e:
                estado = f"Error: {str(e)}"
            db.add(Envio(fecha_envio=datetime.utcnow(), asunto=subj, mensaje=cuerpo, archivos_a_enviar="", destinatarios=",".join(emails_list), estado=estado))
            db.commit()
            if estado != "Enviado":
                return {"ok": False, "msg": estado}
            return {"ok": True, "msg": "Enviado", "enviados": len(emails_list)}

        if action == "exportExcel":
            return {"ok": False, "msg": "Exportación Excel disponible próximamente"}

        if action == "getAreaSupervisores":
            sup_map = {}
            for s in db.query(Supervisor).all():
                area = s.area or "Sin Area"
                if area not in sup_map: sup_map[area] = []
                sup_map[area].append(db_to_gas(s, SUPERVISOR_MAP))
            return {"ok": True, "data": sup_map}

        if action == "generarReporte":
            desde = payload.get("desde", "").strip()
            hasta = payload.get("hasta", "").strip()
            lider = payload.get("lider", "").strip()
            sup_sector = payload.get("supSector", "").strip()
            sup_area = payload.get("supArea", "").strip()
            pastor_zona = payload.get("pastorZona", "").strip()
            distrito = payload.get("distrito", "").strip()
            zona = payload.get("zona", "").strip()
            tipo = payload.get("tipo", "Reporte de Grupos").strip()
            no_guardar = payload.get("_noGuardar", False)

            q = db.query(Reporte)
            if desde:
                try:
                    d = datetime.strptime(desde, "%Y-%m-%d").date()
                    q = q.filter(Reporte.fecha >= d)
                except: q = q.filter(Reporte.fecha >= desde)
            if hasta:
                try:
                    d = datetime.strptime(hasta, "%Y-%m-%d").date()
                    q = q.filter(Reporte.fecha <= d)
                except: q = q.filter(Reporte.fecha <= hasta)
            if lider: q = q.filter(Reporte.lider.ilike(f"%{lider.strip()}%"))
            if sup_sector: q = q.filter(Reporte.sup_sector.ilike(f"%{sup_sector.strip()}%"))
            if sup_area: q = q.filter(Reporte.sup_area.ilike(f"%{sup_area.strip()}%"))
            if pastor_zona: q = q.filter(Reporte.pastor_zona.ilike(f"%{pastor_zona.strip()}%"))
            if distrito: q = q.filter(Reporte.distrito == distrito)
            if zona: q = q.filter(Reporte.zona == zona)

            reportes = q.order_by(Reporte.fecha.desc(), Reporte.distrito, Reporte.zona).all()
            total_en_db = db.query(Reporte).count()
            if not reportes:
                # Ayudar al usuario a diagnosticar
                fechas = db.query(func.min(Reporte.fecha), func.max(Reporte.fecha)).first()
                rango_db = f"{fechas[0]} a {fechas[1]}" if fechas[0] else "sin datos"
                return {"ok": False, "msg": f"No se encontraron reportes. Hay {total_en_db} en total (rango: {rango_db}). Filtros: desde={desde or 'cualquiera'}, hasta={hasta or 'cualquiera'}, lider={lider or 'todos'}"}

            total_grupos = len(reportes)
            total_asist = sum(r.asistencia or 0 for r in reportes)
            total_hnos = sum(r.hnos or 0 for r in reportes)
            total_amigos = sum(r.amigos or 0 for r in reportes)
            total_ninos = sum(r.ninos or 0 for r in reportes)
            total_ofrenda = sum(float(r.ofrenda_total or 0) for r in reportes)
            total_pendientes = sum(1 for r in reportes if r.ofrenda_recibida in ("Pendiente", ""))
            total_recibidas = total_grupos - total_pendientes

            sys_nom = ""
            try:
                cfg = db.query(Configuracion).filter(Configuracion.clave == "nombre").first()
                if cfg: sys_nom = cfg.valor
            except: pass

            # Nomenclatura: redil_YYYYMMDD_correlativo
            today_str = datetime.now().strftime('%Y%m%d')
            count = db.query(GeneradorReporte).filter(GeneradorReporte.no_serie.like(f'%{today_str}%')).count() + 1
            no_serie = f"redil_{today_str}_{count:03d}"
            fecha_gen = datetime.now().strftime('%d/%m/%Y %I:%M %p')
            rango_str = f"{desde or 'Inicio'} -> {hasta or 'Hoy'}"

            rows_html = ""
            for r in reportes:
                pend = r.ofrenda_recibida in ("Pendiente", "")
                of_val = float(r.ofrenda_total or 0)
                rows_html += f"""<tr>
                    <td><span class="cod">{esc(r.codigo or '')}</span></td>
                    <td><b>{esc(r.lider or '')}</b></td>
                    <td>{esc(str(r.fecha) if r.fecha else '')}</td>
                    <td>D{r.distrito or '?'} Z{r.zona or '?'}</td>
                    <td class="num">{r.asistencia or 0}</td>
                    <td class="num">Q{of_val:,.2f}</td>
                    <td class="num">{r.hnos or 0}</td>
                    <td class="num">{r.amigos or 0}</td>
                    <td class="{'pend' if pend else 'ok'}">{'Pendiente' if pend else 'Recibida'}</td>
                </tr>"""

            estado_pct = round(total_recibidas / total_grupos * 100, 1) if total_grupos else 0

            html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{esc(sys_nom or 'REDIL')} — {esc(tipo)}</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
            <style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            @page{{size:letter;margin:0.35in}}
            body{{font-family:'Inter',-apple-system,sans-serif;background:#f5f6fa;color:#2d3436;padding:0;font-size:9px}}
            .rpt{{max-width:100%;margin:0 auto;background:#fff;overflow:hidden}}
            .hdr{{background:linear-gradient(135deg,#1a3a5c 0%,#2d6a9f 50%,#3b82c4 100%);color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:flex-start;gap:10px;-webkit-print-color-adjust:exact}}
            .hdr-l h1{{font-size:16px;font-weight:900;letter-spacing:-.3px;margin-bottom:2px}}
            .hdr-l .sub{{font-size:8.5px;opacity:.85}}
            .hdr-badge{{background:rgba(255,255,255,.2);padding:5px 12px;border-radius:20px;font-size:10px;font-weight:800;white-space:nowrap}}
            .hdr-badge span{{opacity:.7;font-size:8px;font-weight:400;display:block}}
            .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;padding:10px 16px;background:#f8f9fe;border-bottom:1px solid #eef0f8;page-break-inside:avoid}}
            .kpi{{background:#fff;border-radius:8px;padding:8px 10px;box-shadow:0 1px 3px rgba(0,0,0,.05);border-left:2.5px solid var(--kc,#1a3a5c)}}
            .kpi .v{{font-size:15px;font-weight:900;color:#1a3a5c;line-height:1.1;margin-bottom:1px}}
            .kpi .l{{font-size:7.5px;color:#7f8c9b;font-weight:600;text-transform:uppercase;letter-spacing:.2px}}
            .kpi.c0{{--kc:#6366f1}} .kpi.c1{{--kc:#f59e0b}} .kpi.c2{{--kc:#10b981}} .kpi.c3{{--kc:#3b82f6}} .kpi.c4{{--kc:#ef4444}} .kpi.c5{{--kc:#8b5cf6}} .kpi.c6{{--kc:#14b8a6}} .kpi.c7{{--kc:#f97316}}
            table{{width:100%;border-collapse:collapse;font-size:8px}}
            thead th{{background:#1a3a5c;color:#fff;font-size:7px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;padding:5px 5px;text-align:center;border-right:1px solid rgba(255,255,255,.15);-webkit-print-color-adjust:exact}}
            thead th:last-child{{border-right:none}}
            thead th:first-child{{border-radius:0;padding-left:10px;text-align:left}}
            tbody td{{padding:4px 5px;border-bottom:1px solid #f0f2f5;vertical-align:middle;text-align:center}}
            tbody td:first-child{{text-align:left;padding-left:10px}}
            tbody tr:nth-child(even){{background:#fafbfe}}
            .cod{{font-family:monospace;font-size:7.5px;background:#eef0f8;padding:1px 5px;border-radius:4px;color:#2d6a9f;font-weight:700}}
            .num{{font-weight:700;font-family:'Inter',sans-serif}}
            .pend{{color:#dc2626;font-weight:700;background:#fef2f2;padding:2px 6px;border-radius:10px;font-size:7px}}
            .ok{{color:#059669;font-weight:700;background:#ecfdf5;padding:2px 6px;border-radius:10px;font-size:7px}}
            .footer{{padding:8px 16px;border-top:2px solid #eef0f8;display:flex;justify-content:space-between;align-items:center;font-size:7.5px;color:#7f8c9b}}
            .footer b{{color:#1a3a5c}}
            .footer-r{{text-align:right;line-height:1.3}}
            @media print{{body{{background:#fff}}.rpt{{box-shadow:none}}.kpis{{page-break-inside:avoid}}}}
            @media screen{{body{{background:#f0f4f8;padding:10px 8px}}.rpt{{border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.08)}}}}
            </style></head><body>
            <div class="rpt">
                <div class="hdr">
                    <div class="hdr-l">
                        <h1>{esc(sys_nom or 'REDIL')}</h1>
                        <div class="sub">{esc(tipo)} — {rango_str} — {fecha_gen}</div>
                    </div>
                    <div class="hdr-badge">{no_serie}<span>{total_grupos} grupos</span></div>
                </div>
                <div class="kpis">
                    <div class="kpi c0"><div class="v">{total_grupos}</div><div class="l">Grupos</div></div>
                    <div class="kpi c1"><div class="v">{total_asist}</div><div class="l">Asistencia</div></div>
                    <div class="kpi c2"><div class="v">Q{total_ofrenda:,.2f}</div><div class="l">Ofrenda</div></div>
                    <div class="kpi c3"><div class="v">{estado_pct}%</div><div class="l">Recibidas</div></div>
                    <div class="kpi c4"><div class="v">{total_pendientes}</div><div class="l">Pendientes</div></div>
                    <div class="kpi c5"><div class="v">{total_hnos}</div><div class="l">Hermanos</div></div>
                    <div class="kpi c6"><div class="v">{total_amigos}</div><div class="l">Amigos</div></div>
                    <div class="kpi c7"><div class="v">{total_ninos}</div><div class="l">Niños</div></div>
                </div>
                <div class="tw">
                    <table>
                        <thead><tr><th>Código</th><th>Líder</th><th>Fecha</th><th>D-Z</th><th class="num">AGF</th><th class="num">Ofrenda</th><th class="num">Hnos</th><th class="num">Amg</th><th>Estado</th></tr></thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
                <div class="footer">
                    <div><b>{total_grupos}</b> reportes · <b>Q{total_ofrenda:,.2f}</b></div>
                    <div class="footer-r">
                        <div>Daniel Martínez</div>
                        <div>Total App GT</div>
                    </div>
                </div>
            </div>
            </body></html>"""

            result = {"ok": True, "html": html, "noSerie": no_serie}
            # Guardar registro en generador_reportes (solo si no es preview)
            if not no_guardar:
                try:
                    gr = GeneradorReporte(
                        no_serie=no_serie,
                        fecha_inicio=desde or None,
                        fecha_fin=hasta or None,
                        total_ofrenda=total_ofrenda,
                        total_asistencia=total_asist,
                        titulo_reporte=tipo,
                        filtro_lider=lider or None,
                        filtro_sup_sector=sup_sector or None,
                        filtro_sup_area=sup_area or None,
                        filtro_pastor_zona=pastor_zona or None,
                        filtro_distrito=distrito or None,
                        filtro_zona=zona or None,
                        archivo_generado=""
                    )
                    db.add(gr)
                    db.commit()
                    db.add(gr)
                    db.commit()
                    try:
                        from fpdf import FPDF
                        pdf = FPDF('L','mm','Letter'); pdf.set_auto_page_break(True,8)
                        pdf.add_page()
                        pw=pdf.w; ph=pdf.h; mx=10; rw=pw-20
                        pdf.set_fill_color(26,58,92); pdf.rect(0,0,pw,22,'F')
                        pdf.set_fill_color(18,48,78); pdf.rect(0,0,pw,2,'F')
                        pdf.set_text_color(255,255,255); pdf.set_font('Helvetica','B',15)
                        pdf.set_xy(mx,3); pdf.cell(rw*0.55,7,pdf_safe(sys_nom or'Iglesia Restauracion')[:35],0,0,'L')
                        pdf.set_font('Helvetica','',7.5); pdf.set_text_color(190,210,230)
                        df2=datetime.now().strftime('%d/%m/%Y %I:%M %p')
                        pdf.set_xy(mx,12); pdf.cell(rw*0.55,4,f'{pdf_safe(tipo)[:45]}  |  {rango_str}  |  {df2}',0,0,'L')
                        bx2=pw-mx-56; by2=3
                        pdf.set_fill_color(255,255,255); pdf.rect(bx2,by2,56,15,'F')
                        pdf.set_draw_color(60,120,180); pdf.set_line_width(0.4); pdf.rect(bx2,by2,56,15,'D')
                        pdf.set_text_color(26,58,92); pdf.set_font('Helvetica','B',10)
                        pdf.set_xy(bx2,by2+1); pdf.cell(56,7,no_serie,0,0,'C')
                        pdf.set_font('Helvetica','',6.5); pdf.set_text_color(100,120,140)
                        pdf.set_xy(bx2,by2+8); pdf.cell(56,4,f'{total_grupos} rep | Q{total_ofrenda:,.0f}',0,0,'C')
                        kpi=[(str(total_grupos),'REPORTES',(99,102,241)),(str(total_asist),'ASISTENCIA',(16,185,129)),(f'Q{total_ofrenda:,.0f}','OFRENDA',(239,68,68)),(f'{estado_pct}%','RECIBIDAS',(59,130,246)),(str(total_pendientes),'PENDIENTES',(249,115,22)),(str(total_hnos),'HNOS',(139,92,246)),(str(total_amigos),'AMIGOS',(20,184,166)),(str(total_ninos),'NINOS',(245,158,11))]
                        kw=(rw-7*4)/8; kh=15; ky=26
                        for i,(v,l,(cr,cg,cb)) in enumerate(kpi):
                            kx=mx+i*(kw+4); pdf.set_fill_color(248,251,255); pdf.set_draw_color(215,225,240); pdf.rect(kx,ky,kw,kh,'DF')
                            pdf.set_fill_color(cr,cg,cb); pdf.rect(kx,ky,2.5,kh,'F')
                            pdf.set_text_color(cr,cg,cb); pdf.set_font('Helvetica','B',11); pdf.set_xy(kx+4,ky+1); pdf.cell(kw-6,7,v,0,0,'L')
                            pdf.set_font('Helvetica','',5.5); pdf.set_text_color(120,130,145); pdf.set_xy(kx+4,ky+10); pdf.cell(kw-6,4,l,0,0,'L')
                        cd=[('Codigo',15,'L'),('Lider',38,'L'),('Fecha',18,'C'),('D-Z',17,'C'),('AGF',12,'C'),('Ofrenda',18,'C'),('Hnos',10,'C'),('Amigos',10,'C'),('Ninos',10,'C'),('Estado',22,'C')]
                        cw=[c[1]for c in cd]; scale=rw/sum(cw); cw=[w*scale for w in cw]; chd=[c[0]for c in cd]; ca=[c[2]for c in cd]
                        ty=ky+kh+8; th=6; pdf.set_fill_color(26,58,92); pdf.set_text_color(255,255,255); pdf.set_font('Helvetica','B',7)
                        xh=mx
                        for ci in range(len(chd)): pdf.set_xy(xh,ty); pdf.cell(cw[ci],th,chd[ci],0,0,'C',True); xh+=cw[ci]
                        ry=ty+th; rh=5; mr=int((ph-ry-14)/rh)
                        for ri,r in enumerate(reportes):
                            if ri>0 and ri%mr==0:
                                pdf.add_page(); ry=10; xh=mx; pdf.set_fill_color(26,58,92); pdf.set_text_color(255,255,255); pdf.set_font('Helvetica','B',7)
                                for ci in range(len(chd)): pdf.set_xy(xh,ry); pdf.cell(cw[ci],th,chd[ci],0,0,'C',True); xh+=cw[ci]
                                ry+=th
                            pdf.set_fill_color(253,254,255)if ri%2==0 else pdf.set_fill_color(246,250,254)
                            pend=r.ofrenda_recibida in("Pendiente",""); ov=float(r.ofrenda_total or 0)
                            vs=[pdf_safe(r.codigo or'-')[:12],pdf_safe(r.lider or'-')[:28],str(r.fecha)[:10]if r.fecha else'-','D'+pdf_safe(str(r.distrito or'?'))+' Z'+pdf_safe(str(r.zona or'?')),str(r.asistencia or 0),'Q'+f'{ov:,.0f}',str(r.hnos or 0),str(r.amigos or 0),str(r.ninos or 0),'']
                            cv=mx
                            for vi in range(len(cd)):
                                if vi==9:
                                    if pend: pdf.set_fill_color(254,238,238); pdf.set_draw_color(230,190,190); pdf.set_text_color(190,30,30); et='Pendiente'
                                    else: pdf.set_fill_color(233,251,240); pdf.set_draw_color(170,220,195); pdf.set_text_color(5,140,95); et='Recibida'
                                    pdf.set_font('Helvetica','B',6.5); pdf.rect(cv+1.5,ry,cw[vi]-3,rh,'DF'); pdf.set_xy(cv,ry); pdf.cell(cw[vi],rh,et,0,0,'C')
                                else: pdf.set_text_color(45,55,70); pdf.set_font('Helvetica','',7); pdf.set_xy(cv,ry); pdf.cell(cw[vi],rh,vs[vi],0,0,ca[vi],True)
                                cv+=cw[vi]
                            ry+=rh
                        pdf.set_y(ry+3); pdf.set_draw_color(180,195,215); pdf.set_line_width(0.4); pdf.line(mx,pdf.get_y(),pw-mx,pdf.get_y())
                        pdf.set_font('Helvetica','B',7); pdf.set_text_color(26,58,92)
                        pdf.set_xy(mx,pdf.get_y()+2); pdf.cell(rw*0.5,5,f'{total_grupos} reportes  |  Q{total_ofrenda:,.2f}  |  {df2}',0,0,'L')
                        pdf.set_font('Helvetica','',6); pdf.set_text_color(130,140,155)
                        sys_url2 = _get_system_url(db)
                        pdf.set_xy(mx,pdf.get_y()+6); pdf.cell(rw,4,f'Sistema REDIL  |  {sys_url2}',0,0,'R')
                        pdf_b64=base64.b64encode(pdf.output()).decode()
                        gr.pdf_data=pdf_b64; gr.archivo_generado=f"/api/pdf/{no_serie}"; db.commit()
                        result["pdfUrl"]=f"/api/pdf/{no_serie}"; result["pdfStatus"]="PDF listo"
                    except Exception as e:
                        result["pdfError"]=str(e); print(f"PDF fallo ({no_serie}): {e}")
                except: pass
            return result

        # ── WHATSAPP ──
        if action == "sendWhatsapp":
            from app.whatsapp_utils import send_whatsapp, send_whatsapp_bulk, send_whatsapp_template
            to_num = payload.get("to", "")
            msg = payload.get("message", "")
            forzar_texto = payload.get("forzarTexto", False)
            if not msg:
                return {"ok": False, "msg": "Mensaje requerido"}
            nums = [n.strip() for n in to_num.split(",") if n.strip()] if to_num and "," in to_num else [to_num] if to_num else []
            if not nums:
                return {"ok": False, "msg": "Número requerido"}
            # Normalizar numeros: 8 digitos -> 502XXXXXXXX
            nums = [("502"+n if len(n.replace("+","").replace(" ",""))==8 and not n.startswith("+") and not n.startswith("502") else n) for n in nums]
            if forzar_texto:
                result = send_whatsapp_bulk(nums, msg) if len(nums) > 1 else send_whatsapp(nums[0], msg)
            else:
                texto_wa = _formatear_whatsapp(msg)
                cn = _get_church_name(db)
                results = [send_whatsapp_template(n, params=[cn, texto_wa]) for n in nums]
                ok_count = sum(1 for r in results if r.get("ok"))
                result = {"ok": ok_count > 0, "msg": f"Plantilla enviada a {ok_count}/{len(nums)} contactos"}
            return result

        # ── ENVÍO MASIVO WHATSAPP (desde Centro Envíos) ──
        if action == "enviarWhatsappMasivo":
            from app.whatsapp_utils import send_whatsapp_bulk, send_whatsapp_template
            numbers = payload.get("numeros", [])
            msg = payload.get("mensaje", "")
            pdf_url = payload.get("pdfUrl", "")
            forzar_texto_raw = payload.get("usarPlantilla") == False
            if not numbers or not msg:
                return {"ok": False, "msg": "Números y mensaje requeridos"}
            # Si hay PDF, SIEMPRE enviar como documento (la plantilla no soporta adjuntos)
            forzar = forzar_texto_raw or bool(pdf_url and pdf_url.strip())
            # Normalizar numeros: 8 digitos -> 502XXXXXXXX
            numbers = [("502"+n if len(str(n).replace("+","").replace(" ",""))==8 and not str(n).startswith("+") and not str(n).startswith("502") else str(n)) for n in numbers]
            if forzar:
                return send_whatsapp_bulk(numbers, msg, pdf_url if pdf_url else None)
            texto_wa = _formatear_whatsapp(msg, pdf_url)
            cn = _get_church_name(db)
            results = [send_whatsapp_template(n, params=[cn, texto_wa]) for n in numbers]
            ok_count = sum(1 for r in results if r.get("ok"))
            return {"ok": ok_count > 0, "msg": f"Plantilla enviada a {ok_count}/{len(numbers)} contactos"}

        # ── RECURRENTE (PAGOS) ──
        if action == "getPlanes":
            from app.recurrente_utils import listar_planes
            return listar_planes()

        # ── NOTIFICACIONES ──
        if action == "getNotificaciones":
            from app.models import Notificacion
            rows = db.query(Notificacion).order_by(Notificacion.timestamp.desc()).all()
            return {"ok": True, "data": [
                {"id": n.id, "titulo": n.titulo, "mensaje": n.mensaje,
                 "tipo": n.tipo, "evento": n.evento, "lugar": n.lugar,
                 "hora_evento": n.hora_evento, "info_extra": n.info_extra,
                 "cita_biblica": n.cita_biblica, "fecha_evento": n.fecha_evento,
                 "frecuencia": n.frecuencia, "dia_semana": n.dia_semana,
                 "dia_mes": n.dia_mes, "hora_envio": n.hora_envio,
                 "activo": n.activo, "destinatarios": n.destinatarios,
                 "ultimo_envio": str(n.ultimo_envio) if n.ultimo_envio else "",
                 "proximo_envio": str(n.proximo_envio) if n.proximo_envio else "",
                 "creado_por": n.creado_por, "timestamp": str(n.timestamp)}
                for n in rows
            ]}

        if action == "saveNotificacion":
            from app.models import Notificacion
            nid = payload.get("id")
            titulo = payload.get("titulo", "")
            mensaje = payload.get("mensaje", "")
            tipo = payload.get("tipo", "general")
            evento = payload.get("evento", "")
            lugar = payload.get("lugar", "")
            hora_evento = payload.get("hora_evento", "")
            info_extra = payload.get("info_extra", "")
            cita_biblica = payload.get("cita_biblica", "")
            fecha_evento = payload.get("fecha_evento", "")
            frecuencia = payload.get("frecuencia", "una_vez")
            dia_s = payload.get("dia_semana")
            dia_m = payload.get("dia_mes")
            hora = payload.get("hora_envio", "08:00")
            activo = payload.get("activo", True)
            dests = payload.get("destinatarios", [])
            creador = payload.get("creado_por", user.nombre if user else "")
            if isinstance(dests, list):
                dests = json.dumps(dests, ensure_ascii=False)
            if not mensaje and not evento:
                return {"ok": False, "msg": "Mensaje o evento requerido"}
            if nid:
                n = db.query(Notificacion).filter(Notificacion.id == nid).first()
                if not n:
                    return {"ok": False, "msg": "Notificacion no encontrada"}
                n.titulo = titulo; n.mensaje = mensaje
                n.tipo = tipo; n.evento = evento; n.lugar = lugar
                n.hora_evento = hora_evento; n.info_extra = info_extra
                n.cita_biblica = cita_biblica; n.fecha_evento = fecha_evento
                n.frecuencia = frecuencia
                n.dia_semana = int(dia_s) if dia_s is not None else None
                n.dia_mes = int(dia_m) if dia_m is not None else None
                n.hora_envio = hora; n.activo = activo; n.destinatarios = dests
            else:
                n = Notificacion(
                    titulo=titulo, mensaje=mensaje, tipo=tipo,
                    evento=evento, lugar=lugar, hora_evento=hora_evento, info_extra=info_extra,
                    cita_biblica=cita_biblica, fecha_evento=fecha_evento,
                    frecuencia=frecuencia,
                    dia_semana=int(dia_s) if dia_s is not None else None,
                    dia_mes=int(dia_m) if dia_m is not None else None,
                    hora_envio=hora, activo=activo, destinatarios=dests,
                    creado_por=creador
                )
                db.add(n)
            db.commit()
            return {"ok": True, "msg": "Notificacion guardada"}

        if action == "deleteNotificacion":
            from app.models import Notificacion
            nid = payload.get("id")
            if not nid:
                return {"ok": False, "msg": "ID requerido"}
            n = db.query(Notificacion).filter(Notificacion.id == nid).first()
            if not n:
                return {"ok": False, "msg": "No encontrada"}
            db.delete(n)
            db.commit()
            return {"ok": True}

        if action == "enviarNotificacionPrueba":
            from app.whatsapp_utils import send_whatsapp_template
            from app.email_utils import send_email
            from datetime import datetime as dt
            from app.models import NotificacionLog
            numero = str(payload.get("numero", "") or "").replace("+", "").replace(" ", "").replace("-", "")
            if len(numero) == 8 and numero.isdigit() and not numero.startswith("502"):
                numero = "502" + numero
            email = str(payload.get("email", "") or "").strip()
            tipo = str(payload.get("tipo", "") or "general").lower()
            titulo = payload.get("titulo", "")
            mensaje = payload.get("mensaje", "")
            evento = str(payload.get("evento", "") or "").strip()
            lugar = str(payload.get("lugar", "") or "").strip()
            hora_evento = str(payload.get("hora_evento", "") or "").strip()
            fecha_evento = str(payload.get("fecha_evento", "") or "").strip()
            cita_biblica = str(payload.get("cita_biblica", "") or "").strip()
            info_extra = str(payload.get("info_extra", "") or "").strip()
            canal = str(payload.get("canal", "") or "whatsapp").lower()
            msg_construido = _construir_mensaje_notificacion(
                tipo, titulo, mensaje, evento, lugar, hora_evento, info_extra,
                cita_biblica=cita_biblica, fecha_evento=fecha_evento
            )
            if canal in ("correo", "email"):
                if not email or not msg_construido:
                    return {"ok": False, "msg": "Correo y mensaje requeridos"}
                try:
                    cn_email = _get_church_name(db)
                    lineas_html = "".join(f'<div style="margin-bottom:8px">{_htmlesc(l)}</div>' for l in msg_construido.split("\n"))
                    html = '<div style="font-family:sans-serif;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;max-width:520px">'
                    html += '<div style="background:linear-gradient(135deg,#1a3a5c,#2563a8);color:#fff;padding:20px"><b style="font-size:18px">'+_htmlesc(cn_email)+'</b><div style="font-size:13px;opacity:.9">Restaurando vidas y familias</div></div>'
                    html += '<div style="padding:22px">'+lineas_html+'</div></div>'
                    send_email([email], f"{cn_email} - {titulo or 'Notificacion'}", html)
                    estado = "enviado"
                    destino = email
                    res = {"ok": True, "msg": "Enviado", "canal": "correo"}
                except Exception as e:
                    estado = "fallo"
                    destino = email
                    res = {"ok": False, "msg": str(e)[:300]}
                db.add(NotificacionLog(
                    notificacion_id=0, titulo=titulo, destino=destino, canal="correo",
                    wamid="", estado=estado, error_msg=str(res.get('msg',''))[:300]
                ))
                db.commit()
                return res
            if not numero or not msg_construido:
                return {"ok": False, "msg": "Numero y mensaje requeridos"}
            # Template no soporta saltos de linea, usar separador
            msg_wa_tpl = msg_construido.replace("\n", "  ·  ")
            cn = _get_church_name(db)
            resp = send_whatsapp_template(numero, params=[cn, msg_wa_tpl])
            db.add(NotificacionLog(
                notificacion_id=0, titulo=titulo, destino=numero, canal="whatsapp",
                wamid=resp.get("wamid", ""),
                estado="enviado" if resp.get("ok") else "fallo",
                error_msg=str(resp.get("msg", ""))[:300]
            ))
            db.commit()
            return resp

        if action == "getNotificacionesLog":
            from app.models import NotificacionLog
            rows = db.query(NotificacionLog).order_by(NotificacionLog.fecha.desc()).limit(200).all()
            return {"ok": True, "data": [
                {"id": r.id, "notificacion_id": r.notificacion_id,
                 "titulo": r.titulo, "destino": r.destino, "canal": r.canal,
                 "wamid": r.wamid, "estado": r.estado,
                 "error_msg": r.error_msg, "fecha": str(r.fecha)}
                for r in rows
            ]}

        if action == "getContactosWhatsapp":
            contactos = []
            for s in db.query(Supervisor).filter(Supervisor.telefono.isnot(None), Supervisor.telefono != "").all():
                contactos.append({"nombre": s.nombre_sup or "", "numero": str(s.telefono).replace("+", "").replace(" ", ""), "email": s.email or "", "tipo": "Supervisor"})
            for p in db.query(Pastore).filter(Pastore.telefono.isnot(None), Pastore.telefono != "").all():
                contactos.append({"nombre": p.nombre_pastor or "", "numero": str(p.telefono).replace("+", "").replace(" ", ""), "email": p.email or "", "tipo": "Pastor"})
            for a in db.query(AyudaPastor).filter(AyudaPastor.telefono.isnot(None), AyudaPastor.telefono != "").all():
                contactos.append({"nombre": a.nombre_ayuda or "", "numero": str(a.telefono).replace("+", "").replace(" ", ""), "email": a.email or "", "tipo": "Ayuda Pastor"})
            for c in db.query(Contacto).filter(Contacto.telefono.isnot(None), Contacto.telefono != "").all():
                contactos.append({"nombre": c.nombre or "", "numero": str(c.telefono).replace("+", "").replace(" ", ""), "email": c.email or "", "tipo": "Contacto"})
            for c in db.query(Contacto).filter((Contacto.email.isnot(None)) & (Contacto.email != "") & ((Contacto.telefono.is_(None)) | (Contacto.telefono == ""))).all():
                contactos.append({"nombre": c.nombre or "", "numero": "", "email": c.email or "", "tipo": "Contacto"})
            return {"ok": True, "data": contactos}

        # ── ESTADOS DE ENTREGA WHATSAPP (webhook) ──
        if action == "getWhatsappEstados":
            from app.models import EnvioWhatsapp
            rows = db.query(EnvioWhatsapp).order_by(EnvioWhatsapp.id.desc()).limit(100).all()
            return {"ok": True, "data": [
                {"wamid": r.wamid, "numero": r.numero, "estado": r.estado,
                 "timestamp": r.timestamp, "error": r.error, "fecha": str(r.fecha)}
                for r in rows
            ]}

        if action == "getWhatsappMensajes":
            from app.models import MensajeRecibido
            rows = db.query(MensajeRecibido).order_by(MensajeRecibido.id.desc()).limit(100).all()
            return {"ok": True, "data": [
                {"id": r.id, "wamid": r.wamid, "remitente": r.remitente,
                 "internal_user_id": r.internal_user_id, "tipo": r.tipo,
                 "contenido": r.contenido, "procesado": r.procesado, "fecha": str(r.fecha)}
                for r in rows
            ]}

        if action == "sincronizarContactosProxy":
            from app.whatsapp_utils import sincronizar_contactos_proxy
            return sincronizar_contactos_proxy(db)

        if action == "crearCheckout":
            from app.recurrente_utils import crear_checkout
            return crear_checkout(
                payload.get("plan_id", ""),
                payload.get("success_url", ""),
                payload.get("cancel_url", ""),
                payload.get("email", "")
            )

        # ── ENVÍO DE CORREO MANUAL ──
        if action == "enviarCorreo":
            dest = payload.get("destinatarios", "")
            asunto = payload.get("asunto", "")
            cuerpo = payload.get("cuerpo", "")
            emails_list = [e.strip() for e in dest.replace(";", ",").split(",") if e.strip()]
            if not emails_list: return {"ok": False, "msg": "Sin destinatarios"}
            cfg_dict = {}
            for c in db.query(Configuracion).all(): cfg_dict[c.clave] = c.valor
            sys_nom = cfg_dict.get("nombre", "REDIL")
            full_html = f'<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body style="font-family:Arial,sans-serif;padding:20px"><div style="max-width:600px;margin:0 auto"><h2 style="color:#1a3a5c">{esc(sys_nom)}</h2>{cuerpo or "<p>Mensaje del sistema REDIL.</p>"}</div></body></html>'
            try:
                send_email(emails_list, asunto or f"{sys_nom} · Comunicado", full_html)
                return {"ok": True, "msg": f"Correo enviado a {len(emails_list)} destinatario(s)"}
            except Exception as e:
                return {"ok": False, "msg": str(e)}

        # ── CUADRE DOMINICAL ──
        if action == "obtenerVistazoDistritalDominical":
            desde = payload.get("desde","")
            hasta = payload.get("hasta","")
            distrito = payload.get("distrito","")
            zona = payload.get("zona","")
            distritos = payload.get("distritos",[])
            zonas = payload.get("zonas",[])
            # Build base query
            q = db.query(
                Reporte.distrito, Reporte.zona,
                func.count(Reporte.id).label("reportes"),
                func.sum(Reporte.ofrenda_total).label("monto_ofrenda"),
                func.sum(Reporte.asistencia).label("asistencia")
            )
            if desde: q = q.filter(Reporte.fecha >= desde)
            if hasta: q = q.filter(Reporte.fecha <= hasta)
            if distrito: q = q.filter(Reporte.distrito == distrito)
            if zona: q = q.filter(Reporte.zona == zona)
            if isinstance(distritos, list) and distritos: q = q.filter(Reporte.distrito.in_(distritos))
            if isinstance(zonas, list) and zonas: q = q.filter(Reporte.zona.in_(zonas))
            q = q.group_by(Reporte.distrito, Reporte.zona).order_by(Reporte.distrito, Reporte.zona)
            rows = q.all()
            data = []
            for row in rows:
                d, z, rptes, monto, asis = row
                # Digitales
                dig_q = db.query(func.count(Reporte.id)).filter(Reporte.distrito == d, Reporte.zona == z, Reporte.reporte_origen == "Digital")
                if desde: dig_q = dig_q.filter(Reporte.fecha >= desde)
                if hasta: dig_q = dig_q.filter(Reporte.fecha <= hasta)
                digitales = dig_q.scalar() or 0
                # Digital con ofrenda
                dig_ok = db.query(func.count(Reporte.id)).filter(Reporte.distrito == d, Reporte.zona == z, Reporte.reporte_origen == "Digital", Reporte.ofrenda_recibida.notin_(["Pendiente",""]))
                if desde: dig_ok = dig_ok.filter(Reporte.fecha >= desde)
                if hasta: dig_ok = dig_ok.filter(Reporte.fecha <= hasta)
                digitalConOfrenda = dig_ok.scalar() or 0
                # Digital sin ofrenda
                digitalSinOfrenda = digitales - digitalConOfrenda
                # Montos digitales con ofrenda
                m_dig_ok = db.query(func.coalesce(func.sum(Reporte.ofrenda_total),0)).filter(Reporte.distrito == d, Reporte.zona == z, Reporte.reporte_origen == "Digital", Reporte.ofrenda_recibida.notin_(["Pendiente",""]))
                if desde: m_dig_ok = m_dig_ok.filter(Reporte.fecha >= desde)
                if hasta: m_dig_ok = m_dig_ok.filter(Reporte.fecha <= hasta)
                montoConOfrenda = float(m_dig_ok.scalar() or 0)
                # Sin ofrenda monto
                m_dig_no = db.query(func.coalesce(func.sum(Reporte.ofrenda_total),0)).filter(Reporte.distrito == d, Reporte.zona == z, Reporte.reporte_origen == "Digital", Reporte.ofrenda_recibida.in_(["Pendiente",""]))
                if desde: m_dig_no = m_dig_no.filter(Reporte.fecha >= desde)
                if hasta: m_dig_no = m_dig_no.filter(Reporte.fecha <= hasta)
                montoSinOfrenda = float(m_dig_no.scalar() or 0)
                # Fisico (no es digital) = sobres
                fis_q = db.query(func.count(Reporte.id)).filter(Reporte.distrito == d, Reporte.zona == z, Reporte.reporte_origen != "Digital")
                if desde: fis_q = fis_q.filter(Reporte.fecha >= desde)
                if hasta: fis_q = fis_q.filter(Reporte.fecha <= hasta)
                sobres = fis_q.scalar() or 0
                # Monto fisico
                m_fis = db.query(func.coalesce(func.sum(Reporte.ofrenda_total),0)).filter(Reporte.distrito == d, Reporte.zona == z, Reporte.reporte_origen != "Digital")
                if desde: m_fis = m_fis.filter(Reporte.fecha >= desde)
                if hasta: m_fis = m_fis.filter(Reporte.fecha <= hasta)
                montoFisico = float(m_fis.scalar() or 0)
                # Pendientes
                pend_q = db.query(func.count(Reporte.id)).filter(Reporte.distrito == d, Reporte.zona == z, Reporte.ofrenda_recibida.in_(["Pendiente",""]))
                if desde: pend_q = pend_q.filter(Reporte.fecha >= desde)
                if hasta: pend_q = pend_q.filter(Reporte.fecha <= hasta)
                pendientes = pend_q.scalar() or 0
                data.append({
                    "distrito": d or "?", "zona": z or "?",
                    "reportes": rptes, "digitales": digitales,
                    "digitalConOfrenda": digitalConOfrenda, "digitalSinOfrenda": digitalSinOfrenda,
                    "sobres": sobres, "montoDigital": float(monto or 0),
                    "montoConOfrenda": montoConOfrenda, "montoSinOfrenda": montoSinOfrenda,
                    "montoFisico": montoFisico, "pendientes": pendientes
                })
            return {"ok": True, "data": data}

        # ── SEMILLA DATOS DE PRUEBA ──
        if action == "seedData":
            import random
            from datetime import date as dt_date
            models_to_clear = [Hermano, Reporte, Seguimiento, Supervisor, Pastore, AyudaPastor, Contacto, Diezmo, Gasto, Inventario, Insumo, Privilegio, Cronograma, Bautizo]
            for model in models_to_clear:
                try: db.query(model).delete()
                except: pass
            db.commit()
            hoy = dt_date.today()
            # Supervisores, Pastores, Ayuda Pastor
            svs = [Supervisor(codigo_sup=f"SP{i:03d}", nombre_sup=f"Supervisor {i}", distrito=str((i%3)+1), zona=str((i%2)+1), area=chr(65+(i%5)), sector=str((i%3)+1), telefono=f"5551-{i:04d}", email=f"sup{i}@iglesia.com", activo=True) for i in range(1,4)]
            pas = [Pastore(codigo_pastor=f"PZ{i:02d}", nombre_pastor=["Fernando García","Ana Morales","Pedro Hernández"][i-1], distrito=str(i), zona="1", telefono=f"5550-{i:04d}", email=f"pastor{i}@iglesia.com", activo=True) for i in range(1,4)]
            db.add_all(svs+pas)
            db.add(AyudaPastor(codigo_ayuda="AP01", nombre_ayuda="Luis Castillo", distrito="1", zona="1", area="A", telefono="5550-2001", email="luis@iglesia.com", activo=True))
            # Hermanos (50)
            nombres = ["Juan Pérez","María Gómez","Carlos Ruiz","Ana Martínez","Luis Sánchez","Elena Torres","Pedro Vargas","Sofía López","Diego Ramírez","Laura Jiménez","Miguel Cruz","Carmen Flores","Roberto Ortiz","Patricia Núñez","Francisco Reyes","Gabriela Mendoza","Antonio Rojas","Isabel Delgado","Ricardo Castro","Verónica Peña","Alejandro Mora","Daniela Herrera","Oscar Pineda","Lucía Aguirre","Manuel Esquivel","Raquel Medina","Felipe Campos","Natalia Vega","Héctor Fuentes","Adriana León","Jorge Rivas","Cecilia Avila","Rubén Solís","Mónica Ortega","Alberto Farfán","Silvia Calderón","Eduardo Miranda","Rosa Benítez","Enrique Gallardo","Teresa Cárdenas","Samuel Arévalo","Paola Gutiérrez","David Valle","Margarita Ponce","Arturo Chávez","Brenda Rosales","Gustavo Rangel","Alicia Padilla","César Ochoa","Claudia Serrano"]
            hnos = []
            for i, nom in enumerate(nombres):
                d, z, a, s, g = str((i%5)+1), str((i%3)+1), chr(65+(i//5%6)), str((i%4)+1), str((i%2)+1)
                cod = f"{d}{z}{a}{s}{g}"
                hnos.append(Hermano(codigo_lead=cod, nombre=nom, distrito=d, zona=z, area=a, sector=s, grupo=g, pastor_zona=["Fernando García","Ana Morales","Pedro Hernández"][i%3], sup_sector=["Supervisor 1","Supervisor 2","Supervisor 3"][i%3], sup_area="Luis Castillo", anfitrion=f"Casa {nom.split()[0]}", direccion=f"{(i%50)+1} Calle Principal Z{z}"))
            db.add_all(hnos)
            # Reportes (150)
            tipos = ["Mixta","Jóvenes","Damas","Caballeros"]
            for _ in range(150):
                h = random.choice(hnos)
                f = hoy - timedelta(days=random.randint(0,90))
                db.add(Reporte(codigo=h.codigo_lead, lider=h.nombre, fecha=f, distrito=h.distrito, zona=h.zona, area=h.area, sector=h.sector, grupo=h.grupo, ofrenda_total=round(random.uniform(25,300),2), ofrenda_recibida=random.choice(["Recibida","Recibida","Pendiente"]), asistencia=random.randint(5,45), hnos=random.randint(2,20), amigos=random.randint(0,10), ninos=random.randint(0,10), tipo_reporte=random.choice(tipos), sup_sector=h.sup_sector, sup_area=h.sup_area, pastor_zona=h.pastor_zona, anfitrion=h.anfitrion))
            # Seguimientos (80)
            pers = ["Marta Álvarez","José Ibarra","Rosa Elena","Francisco Paz","Julia Ventura","David Reyes","Sara Montero","Tomás Aguilar"]
            for _ in range(80):
                h = random.choice(hnos)
                db.add(Seguimiento(fecha=hoy-timedelta(days=random.randint(0,60)), persona=random.choice(pers), tipo=random.choice(["Convertido","Reconciliación","Visita","Sanidad","Oración"]), responsable=h.nombre, estado=random.choice(["Pendiente","En Proceso","Completado"])))
            # Diezmos (40), Gastos (30), Inventario (15), Insumos (15), Bautizos (5), Contactos (4)
            for _ in range(40):
                h = random.choice(hnos)
                db.add(Diezmo(fecha=hoy-timedelta(days=random.randint(0,60)), nombre=h.nombre, telefono=f"5550-{random.randint(1000,9999)}", grupo=h.grupo, monto=round(random.uniform(50,500),2), tipo=random.choice(["Diezmo","Ofrenda","Siembra"])))
            cats = ["Limpieza","Mantenimiento","Eventos","Papelería","Transporte"]
            for _ in range(30):
                db.add(Gasto(concepto=random.choice(["Compra insumos","Reparación","Actividad","Refrigerio"]), evento=random.choice(["Servicio","Reunión Líderes","",""]), monto=round(random.uniform(25,800),2), fecha=hoy-timedelta(days=random.randint(0,90)), categoria=random.choice(cats), responsable=random.choice(["Fernando García","Ana Morales"]), metodo=random.choice(["Efectivo","Transferencia"])))
            inv_items = [("Sillas",80,"Unidad","Bueno",12000),("Mesas",15,"Unidad","Bueno",4500),("Micrófonos",4,"Unidad","Bueno",3200),("Proyector",1,"Unidad","Bueno",7800),("Biblias",40,"Unidad","Bueno",3200)]
            for n, c, u, e, v in inv_items:
                db.add(Inventario(nombre=n, categoria="Mobiliario", cantidad=c, unidad=u, estado=e, valor_q=v))
            for n, ct, pr, st in [("Papel resmas",25,45,5),("Bolígrafos",100,3,20),("Cloro",12,28,3),("Vasos",300,0.8,80),("Focos LED",12,35,3)]:
                db.add(Insumo(nombre=n, categoria="Papelería" if ct>20 else "Limpieza", cantidad=ct, unidad="Unidad", precio_unitario_q=pr, stock_minimo=st, proveedor="Proveedor GT"))
            db.add_all([Bautizo(fecha=hoy-timedelta(days=15), nombre="Andrea Castillo", edad=22, pastor_oficiante="Fernando García", lugar="Iglesia Central"), Bautizo(fecha=hoy-timedelta(days=8), nombre="Ricardo Palma", edad=18, pastor_oficiante="Ana Morales", lugar="Sede Norte"), Bautizo(fecha=hoy-timedelta(days=3), nombre="Valentina Ruiz", edad=15, pastor_oficiante="Pedro Hernández", lugar="Iglesia Central")])
            db.add_all([Contacto(nombre="Proveedor Audio", email="audio@prov.com"), Contacto(nombre="Distribuidora", email="ventas@dist.com"), Contacto(nombre="Imprenta", email="info@imprenta.com"), Contacto(nombre="Mantenimiento", email="soporte@equipos.com")])
            db.commit()
            return {"ok": True, "msg": f"Datos de prueba generados: 50 líderes, 150 reportes, 80 seguimientos, 40 diezmos, 30 gastos, y más."}

        return {"ok": False, "msg": f"Acción '{action}' no implementada en API"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "msg": str(e)}
