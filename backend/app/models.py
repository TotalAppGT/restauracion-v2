from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from app.database import Base
import datetime

class Hermano(Base):
    __tablename__ = "hermanos"
    id = Column(Integer, primary_key=True, index=True)
    codigo_lead = Column(String(50), unique=True, index=True)
    nombre = Column(String(200))
    distrito = Column(String(10))
    zona = Column(String(10))
    area = Column(String(10))
    sector = Column(String(10))
    grupo = Column(String(10))
    pastor_zona = Column(String(200))
    sup_sector = Column(String(200))
    sup_area = Column(String(200))
    ayuda_pastor = Column(String(200))
    anfitrion = Column(String(200))
    direccion = Column(Text)
    codigo_sup = Column(String(50))
    codigo_pastor = Column(String(50))

class Reporte(Base):
    __tablename__ = "reportes"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), index=True)
    lider = Column(String(200))
    fecha = Column(Date, index=True)
    distrito = Column(String(10))
    zona = Column(String(10))
    area = Column(String(10))
    sector = Column(String(10))
    grupo = Column(String(10))
    ofrenda_total = Column(Numeric(12, 2), default=0)
    ofrenda_recibida = Column(String(20), default="Pendiente")
    asistencia = Column(Integer, default=0)
    hnos = Column(Integer, default=0)
    amigos = Column(Integer, default=0)
    ninos = Column(Integer, default=0)
    tipo_reporte = Column(String(50))
    hora_inicio = Column(String(10), default="")
    hora_final = Column(String(10), default="")
    ofrenda_iglesia = Column(Numeric(12, 2), default=0)
    ofrenda_bus = Column(Numeric(12, 2), default=0)
    martes = Column(Integer, default=0)
    jueves = Column(Integer, default=0)
    domingo = Column(Integer, default=0)
    otros = Column(Integer, default=0)
    total_cultos = Column(Integer, default=0)
    reporte_origen = Column(String(20), default="Manual")
    sup_sector = Column(String(200), default="")
    sup_area = Column(String(200), default="")
    pastor_zona = Column(String(200), default="")
    anfitrion = Column(String(200), default="")
    direccion = Column(Text, default="")
    seguimientos_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Seguimiento(Base):
    __tablename__ = "seguimientos"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date)
    persona = Column(String(200))
    tipo = Column(String(100))
    responsable = Column(String(200))
    estado = Column(String(50), default="Pendiente")
    observaciones = Column(Text)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200))
    email = Column(String(200), unique=True, index=True)
    password = Column(String(200))
    rol = Column(String(50), default="usuario")
    activo = Column(Boolean, default=True)
    menu_permitido = Column(Text, nullable=True)
    puede_ver_bitacora = Column(Boolean, default=True)

class Supervisor(Base):
    __tablename__ = "supervisores"
    id = Column(Integer, primary_key=True, index=True)
    codigo_sup = Column(String(50), unique=True, index=True)
    nombre_sup = Column(String(200))
    distrito = Column(String(10))
    zona = Column(String(10))
    area = Column(String(10))
    sector = Column(String(10))
    telefono = Column(String(50))
    email = Column(String(200))
    direccion = Column(Text)
    activo = Column(Boolean, default=True)

class Pastore(Base):
    __tablename__ = "pastores"
    id = Column(Integer, primary_key=True, index=True)
    codigo_pastor = Column(String(50), unique=True, index=True)
    nombre_pastor = Column(String(200))
    distrito = Column(String(10))
    zona = Column(String(10))
    telefono = Column(String(50))
    email = Column(String(200))
    direccion = Column(Text)
    activo = Column(Boolean, default=True)

class PastorDistrito(Base):
    __tablename__ = "pastores_distrito"
    id = Column(Integer, primary_key=True, index=True)
    codigo_pastor_distrito = Column(String(50), unique=True, index=True)
    nombre_pastor_distrito = Column(String(200))
    distrito = Column(String(10))
    telefono = Column(String(50))
    email = Column(String(200))
    direccion = Column(Text)
    activo = Column(Boolean, default=True)

class AyudaPastor(Base):
    __tablename__ = "ayuda_pastor"
    id = Column(Integer, primary_key=True, index=True)
    codigo_ayuda = Column(String(50), unique=True, index=True)
    nombre_ayuda = Column(String(200))
    distrito = Column(String(10))
    zona = Column(String(10))
    area = Column(String(10))
    telefono = Column(String(50))
    email = Column(String(200))
    direccion = Column(Text)
    activo = Column(Boolean, default=True)

class Contacto(Base):
    __tablename__ = "contactos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200))
    telefono = Column(String(50))
    email = Column(String(200))
    direccion = Column(Text)
    notas = Column(Text)
    activo = Column(Boolean, default=True)

class Diezmo(Base):
    __tablename__ = "diezmos"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), index=True)
    nombre = Column(String(200))
    fecha = Column(Date)
    telefono = Column(String(50))
    grupo = Column(String(10))
    monto = Column(Numeric(12, 2), default=0)
    mes = Column(String(20))
    anio = Column(String(10))
    tipo = Column(String(50))
    observaciones = Column(Text)

class Gasto(Base):
    __tablename__ = "gastos"
    id = Column(Integer, primary_key=True, index=True)
    concepto = Column(String(200))
    evento = Column(String(200))
    monto = Column(Numeric(12, 2), default=0)
    fecha = Column(Date)
    categoria = Column(String(100))
    descripcion = Column(Text)
    responsable = Column(String(200))
    metodo = Column(String(100))
    comprobante = Column(String(200))
    observaciones = Column(Text)

class Inventario(Base):
    __tablename__ = "inventario"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200))
    cantidad = Column(Numeric(12, 2), default=0)
    unidad = Column(String(50))
    descripcion = Column(Text)
    categoria = Column(String(100))
    estado = Column(String(50))
    ubicacion = Column(String(200))
    valor_q = Column(Numeric(12, 2), default=0)
    observaciones = Column(Text)

class Insumo(Base):
    __tablename__ = "insumos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200))
    cantidad = Column(Numeric(12, 2), default=0)
    unidad = Column(String(50))
    tipo = Column(String(100))
    categoria = Column(String(100))
    precio_unitario_q = Column(Numeric(12, 2), default=0)
    stock_minimo = Column(Numeric(12, 2), default=0)
    proveedor = Column(String(200))
    observaciones = Column(Text)

class Privilegio(Base):
    __tablename__ = "privilegios"
    id = Column(Integer, primary_key=True, index=True)
    codigo_lead = Column(String(50), index=True)
    nombre = Column(String(200))
    area = Column(String(100))
    privilegio = Column(String(200))
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    activo = Column(Boolean, default=True)
    observaciones = Column(Text)

class Bautizo(Base):
    __tablename__ = "bautizos"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, index=True)
    nombre = Column(String(200))
    edad = Column(Integer, default=0)
    telefono = Column(String(50))
    direccion = Column(Text)
    pastor_oficiante = Column(String(200))
    lugar = Column(String(200))
    observaciones = Column(Text)
    activo = Column(Boolean, default=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Cronograma(Base):
    __tablename__ = "cronograma"
    id = Column(Integer, primary_key=True, index=True)
    hermano = Column(String(200))
    area = Column(String(100))
    servicio = Column(String(200))
    privilegio = Column(String(200))
    lunes = Column(String(100))
    jueves = Column(String(100))
    domingo_manana = Column(String(100))
    domingo_tarde = Column(String(100))
    fecha_asignacion = Column(Date)
    observaciones = Column(Text)
    activo = Column(Boolean, default=True)

class Bitacora(Base):
    __tablename__ = "bitacora"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    usuario = Column(String(200))
    email = Column(String(200))
    rol = Column(String(50))
    accion = Column(String(200))
    detalle = Column(Text)

class Configuracion(Base):
    __tablename__ = "configuraciones"
    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(100), unique=True, index=True)
    valor = Column(Text)

class Envio(Base):
    __tablename__ = "envios"
    id = Column(Integer, primary_key=True, index=True)
    fecha_envio = Column(DateTime)
    asunto = Column(String(200))
    mensaje = Column(Text)
    archivos_a_enviar = Column(Text)
    destinatarios = Column(Text)
    estado = Column(String(50), default="Pendiente")
    rutas_reales_pdf = Column(Text)

class GeneradorReporte(Base):
    __tablename__ = "generadores_reporte"
    id = Column(Integer, primary_key=True, index=True)
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    total_ofrenda = Column(Numeric(12, 2), default=0)
    total_asistencia = Column(Integer, default=0)
    titulo_reporte = Column(String(200))
    archivo_generado = Column(String(200))
    no_serie = Column(String(50))
    mes_reporte = Column(String(20))
    ano_reporte = Column(String(10))
    filtro_lider = Column(String(200))
    filtro_sup_sector = Column(String(200))
    filtro_sup_area = Column(String(200))
    filtro_pastor_zona = Column(String(200))
    filtro_distrito = Column(String(10))
    filtro_zona = Column(String(10))
    pdf_data = Column(Text, nullable=True)

class EnvioWhatsapp(Base):
    __tablename__ = "envios_whatsapp"
    id = Column(Integer, primary_key=True, index=True)
    wamid = Column(String(200), index=True)
    numero = Column(String(50))
    estado = Column(String(50))
    timestamp = Column(String(50))
    error = Column(Text, default="")
    fecha = Column(DateTime, default=datetime.datetime.utcnow)

class MensajeRecibido(Base):
    __tablename__ = "mensajes_recibidos"
    id = Column(Integer, primary_key=True, index=True)
    wamid = Column(String(200), index=True)
    remitente = Column(String(50), index=True)
    internal_user_id = Column(String(100), nullable=True)
    tipo = Column(String(50))
    contenido = Column(Text)
    raw_json = Column(Text)
    procesado = Column(Boolean, default=False)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)

class Notificacion(Base):
    __tablename__ = "notificaciones"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), default="")
    mensaje = Column(Text, nullable=False)
    tipo = Column(String(30), default="general")
    evento = Column(String(200), default="")
    lugar = Column(String(200), default="")
    hora_evento = Column(String(10), default="")
    info_extra = Column(String(300), default="")
    cita_biblica = Column(String(300), default="")
    fecha_evento = Column(String(20), default="")
    frecuencia = Column(String(20), default="una_vez")
    dia_semana = Column(Integer, nullable=True)
    dia_mes = Column(Integer, nullable=True)
    hora_envio = Column(String(10), default="08:00")
    activo = Column(Boolean, default=True)
    destinatarios = Column(Text, default="[]")
    ultimo_envio = Column(DateTime, nullable=True)
    proximo_envio = Column(DateTime, nullable=True)
    creado_por = Column(String(200), default="")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class NotificacionLog(Base):
    __tablename__ = "notificaciones_log"
    id = Column(Integer, primary_key=True, index=True)
    notificacion_id = Column(Integer, index=True)
    titulo = Column(String(200), default="")
    destino = Column(String(50))
    canal = Column(String(20), default="whatsapp")
    wamid = Column(String(200))
    estado = Column(String(50))
    error_msg = Column(String(300), default="")
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
