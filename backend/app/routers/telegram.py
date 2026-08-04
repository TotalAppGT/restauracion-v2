from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from app.database import get_db
from app.models import Reporte, Hermano, Seguimiento, Configuracion
from datetime import date, timedelta, datetime
import os
import httpx
import json

router = APIRouter()

ENV_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ENV_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def _get_config(db):
    cfg = {}
    try:
        for c in db.query(Configuracion).all():
            cfg[c.clave] = c.valor
    except:
        pass
    return cfg

def _get_token(db=None):
    token = ENV_TOKEN
    if not token and db:
        cfg = _get_config(db)
        token = cfg.get("telegram_token", "")
    return token

def _get_chat(db=None):
    cid = ENV_CHAT_ID
    if not cid and db:
        cfg = _get_config(db)
        cid = cfg.get("telegram_chat_id", "")
    return cid

def tg_send(text, chat_id=None, db=None):
    token = _get_token(db)
    cid = chat_id or _get_chat(db)
    if not token or not cid: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": cid, "text": str(text)[:4000], "parse_mode": "HTML"}
    try: httpx.post(url, json=payload, timeout=10)
    except: pass

def esc(s): return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

# ─── COMANDOS ─────────────────────────────────────────
def cmd_start(cid, db):
    tg_send("🤖 <b>REDIL Bot v7.0 — Sistema de Gestión Eclesiástica</b>\n\n"
        "<b>📊 Reportes:</b>\n"
        "/stats — Resumen global\n"
        "/semanal — Estadísticas de esta semana\n"
        "/pendientes — Ofrendas pendientes de recibir\n\n"
        "<b>🔍 Búsqueda:</b>\n"
        "/buscar [nombre|código] — Buscar líderes\n"
        "/lider [nombre|código] — Info completa del líder\n"
        "/pastor [nombre] — Líderes a cargo del pastor\n\n"
        "<b>👥 Seguimientos:</b>\n"
        "/seguimientos — Lista de seguimientos\n"
        "/ayuda — Ver todos los comandos", cid, db)

def cmd_ayuda(cid, db):
    tg_send("📋 <b>Comandos REDIL Bot</b>\n\n"
        "/stats — Resumen global (líderes, reportes, ofrenda, asistencia)\n"
        "/semanal — Esta semana\n"
        "/mes YYYY-MM — Estadísticas del mes\n"
        "/pendientes — Ofrendas pendientes con detalle\n"
        "/buscar texto — Buscar líderes y pastores\n"
        "/lider código|nombre — Info del líder\n"
        "/pastor nombre — Líderes del pastor + cumplimiento\n"
        "/seguimientos — Últimos seguimientos\n"
        "/seguimientos pendientes — Solo pendientes\n\n"
        "💡 <b>Ejemplos:</b>\n"
        "/buscar Juan — Busca líderes con 'Juan' en el nombre\n"
        "/lider 11A11 — Info del líder con código 11A11\n"
        "/pastor Fernando — Todos los líderes de Fernando\n"
        "/mes 2026-06 — Estadísticas de junio 2026", cid, db)

def cmd_stats(db):
    lideres = db.query(Hermano).count()
    reportes = db.query(Reporte).count()
    asis = db.query(sqlfunc.coalesce(sqlfunc.sum(Reporte.asistencia), 0)).scalar()
    ofr = float(db.query(sqlfunc.coalesce(sqlfunc.sum(Reporte.ofrenda_total), 0)).scalar())
    pend = db.query(Reporte).filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""])).count()
    segs = db.query(Seguimiento).count()
    hoy = date.today()
    ini_sem = hoy - timedelta(days=hoy.weekday())
    rep_sem = db.query(Reporte).filter(Reporte.fecha >= ini_sem).count()
    return (f"📊 <b>REDIL — Estadísticas Globales</b>\n\n"
        f"👥 Líderes: {lideres}\n"
        f"📋 Reportes totales: {reportes}\n"
        f"📅 Esta semana: {rep_sem} reportes\n"
        f"🙏 Asistencia total: {asis}\n"
        f"💰 Ofrenda total: Q{ofr:,.2f}\n"
        f"⏳ Pendientes: {pend}\n"
        f"📝 Seguimientos: {segs}")

def cmd_semanal(db):
    hoy = date.today()
    ini_sem = hoy - timedelta(days=hoy.weekday())
    rs = db.query(Reporte).filter(Reporte.fecha >= ini_sem, Reporte.fecha <= hoy).all()
    asis = sum(r.asistencia or 0 for r in rs)
    ofr = sum(float(r.ofrenda_total or 0) for r in rs)
    pend = sum(1 for r in rs if r.ofrenda_recibida in ("Pendiente", ""))
    return (f"📅 <b>Semana: {ini_sem} → {hoy}</b>\n\n"
        f"📋 Grupos: {len(rs)}\n"
        f"🙏 Asistencia: {asis}\n"
        f"💰 Ofrenda: Q{ofr:,.2f}\n"
        f"⏳ Pendientes: {pend}")

def cmd_mes(db, args):
    if not args or not args.startswith("20"):
        return "Usa: /mes YYYY-MM\nEj: /mes 2026-06"
    mes = args.split()[0][:7]
    desde = f"{mes}-01"
    hasta = f"{mes}-31"
    rs = db.query(Reporte).filter(Reporte.fecha >= desde, Reporte.fecha <= hasta).all()
    asis = sum(r.asistencia or 0 for r in rs)
    ofr = sum(float(r.ofrenda_total or 0) for r in rs)
    return (f"📅 <b>Mes: {mes}</b>\n\n"
        f"📋 Grupos: {len(rs)}\n"
        f"🙏 Asistencia: {asis}\n"
        f"💰 Ofrenda: Q{ofr:,.2f}")

def cmd_pendientes(db):
    rs = db.query(Reporte).filter(Reporte.ofrenda_recibida.in_(["Pendiente", ""])).order_by(Reporte.fecha.desc()).all()
    if not rs: return "✅ <b>Todas las ofrendas han sido recibidas.</b>"
    hnos = {h.codigo_lead: h for h in db.query(Hermano).all()}
    grupos = {}
    total_monto = 0
    for r in rs:
        h = hnos.get(r.codigo)
        key = f"{h.distrito}|{h.zona}" if h else "?|?"
        if key not in grupos:
            grupos[key] = {"distrito": h.distrito if h else "?", "zona": h.zona if h else "?", "items": [], "subtotal": 0}
        m = float(r.ofrenda_total or 0)
        grupos[key]["items"].append({
            "nombre": r.lider, "codigo": r.codigo, "monto": m,
            "fecha": str(r.fecha) if r.fecha else "—",
            "pastor": h.pastor_zona if h else "—"
        })
        grupos[key]["subtotal"] += m
        total_monto += m
    t = f"⚠️ <b>Pendientes: {len(rs)}</b> | Q{total_monto:,.2f}\n"
    for k in sorted(grupos.keys())[:8]:
        g = grupos[k]
        t += f"\n📌 <b>D{g['distrito']} Z{g['zona']}</b> — {len(g['items'])} líderes — Q{g['subtotal']:,.2f}\n"
        for it in g['items'][:8]:
            t += f"🔹 <b>{esc(it['nombre'])}</b> ({it['codigo']}) | Q{it['monto']:.2f} | {it['fecha']} | 🙏 {esc(it['pastor'])}\n"
    return t

def cmd_buscar(db, args):
    if not args: return "Usa: /buscar nombre o código\nEj: /buscar Juan\n/buscar 11A11"
    q = args.lower().strip()
    hnos = db.query(Hermano).filter(
        (sqlfunc.lower(Hermano.codigo_lead).contains(q)) | (sqlfunc.lower(Hermano.nombre).contains(q))
    ).limit(15).all()
    if not hnos: return f"❌ Sin resultados para: {args}"
    t = f"🔍 <b>Resultados: {args}</b> ({len(hnos)} encontrados)\n"
    for h in hnos[:15]:
        t += f"\n👤 <b>{esc(h.nombre)}</b> ({h.codigo_lead}) | D{h.distrito} Z{h.zona} | 🙏 {esc(h.pastor_zona or '—')}"
    return t

def cmd_lider(db, args):
    if not args: return "Usa: /lider código o nombre\nEj: /lider Juan\n/lider 11A11"
    q = args.strip()
    h = db.query(Hermano).filter(
        (sqlfunc.lower(Hermano.codigo_lead) == q.lower()) | (Hermano.nombre.ilike(f"%{q}%"))
    ).first()
    if not h: return f"❌ No encontrado: {args}"
    rs = db.query(Reporte).filter(Reporte.codigo == h.codigo_lead).order_by(Reporte.fecha.desc()).all()
    t = (f"👤 <b>{esc(h.nombre)}</b>\n"
        f"Código: {h.codigo_lead}\n"
        f"📍 D{h.distrito} Z{h.zona} Área {h.area} S{h.sector} G{h.grupo}\n"
        f"🏛 Pastor: {esc(h.pastor_zona or '—')}\n"
        f"👤 Sup.Sector: {esc(h.sup_sector or '—')}\n"
        f"📋 Reportes: {len(rs)}\n")
    if rs:
        ult = rs[:3]
        t += "\n<i>Últimos reportes:</i>"
        for r in ult:
            t += f"\n📅 {r.fecha} | Q{float(r.ofrenda_total or 0):.2f} | Asist: {r.asistencia or 0} | {'✅' if r.ofrenda_recibida not in ('Pendiente','') else '⏳'}"
    return t

def cmd_pastor(db, args):
    if not args: return "Usa: /pastor nombre\nEj: /pastor Fernando"
    q = args.strip()
    hnos = db.query(Hermano).filter(Hermano.pastor_zona.ilike(f"%{q}%")).all()
    if not hnos: return f"❌ Pastor no encontrado: {args}"
    pz_name = hnos[0].pastor_zona
    total = hnos
    asis_total = 0; ofr_total = 0
    for h in total:
        rep = db.query(Reporte).filter(Reporte.codigo == h.codigo_lead).order_by(Reporte.fecha.desc()).first()
        if rep:
            asis_total += rep.asistencia or 0
            ofr_total += float(rep.ofrenda_total or 0)
    t = (f"🙏 <b>{esc(pz_name)}</b>\n"
        f"👥 Líderes a cargo: {len(total)}\n"
        f"💰 Ofrenda última: Q{ofr_total:,.2f}\n"
        f"🙏 Asistencia última: {asis_total}\n\n"
        f"<b>Líderes:</b>\n")
    for h in total[:20]:
        ult = db.query(Reporte).filter(Reporte.codigo == h.codigo_lead).order_by(Reporte.fecha.desc()).first()
        status = "✅" if (ult and ult.ofrenda_recibida not in ('Pendiente','')) else ("⏳" if ult else "❌")
        t += f"{status} <b>{esc(h.nombre)}</b> ({h.codigo_lead}) | D{h.distrito} Z{h.zona}"
        if ult: t += f" | Q{float(ult.ofrenda_total or 0):.2f} | {ult.fecha}"
        t += "\n"
    if len(total) > 20: t += f"\n... y {len(total)-20} más"
    return t

def cmd_seguimientos(db, args=None):
    q = db.query(Seguimiento).order_by(Seguimiento.fecha.desc()).limit(50)
    if args and args.lower() in ("pendiente","pendientes"):
        q = q.filter(Seguimiento.estado.ilike("%pendiente%"))
    segs = q.all()
    if not segs: return "📭 Sin seguimientos registrados."
    t = f"📋 <b>Seguimientos ({len(segs)}):</b>\n"
    for s in segs[:15]:
        icon = {"Pendiente": "⏳", "En Proceso": "🔄", "Completado": "✅"}.get(s.estado, "🔹")
        t += f"\n{icon} <b>{esc(s.persona)}</b> | {esc(s.tipo)} | {esc(s.estado)} | 👤 {esc(s.responsable)} | {s.fecha}"
    if len(segs) > 15: t += f"\n\n... y {len(segs)-15} más"
    return t

# ─── WEBHOOK ──────────────────────────────────────────
@router.post("/webhook")
async def webhook(data: dict, db: Session = Depends(get_db)):
    try:
        msg = data.get("message", {})
        txt = msg.get("text", "").strip()
        cid = msg.get("chat", {}).get("id")
        if not txt or not cid: return {"ok": True}

        cmd = txt.split()[0].lower()
        args = txt[len(cmd):].strip() if len(txt) > len(cmd) else ""

        if cmd in ("/start",):
            cmd_start(cid, db)
        elif cmd in ("/ayuda", "/help", "/comandos"):
            cmd_ayuda(cid, db)
        elif cmd == "/stats":
            tg_send(cmd_stats(db), cid, db)
        elif cmd in ("/semanal", "/semana"):
            tg_send(cmd_semanal(db), cid, db)
        elif cmd in ("/mes", "/mensual"):
            tg_send(cmd_mes(db, args), cid, db)
        elif cmd in ("/pendientes", "/pendiente"):
            tg_send(cmd_pendientes(db), cid, db)
        elif cmd in ("/buscar", "/search", "/find"):
            tg_send(cmd_buscar(db, args), cid, db)
        elif cmd in ("/lider", "/info", "/leader"):
            tg_send(cmd_lider(db, args), cid, db)
        elif cmd in ("/pastor", "/supervisor"):
            tg_send(cmd_pastor(db, args), cid, db)
        elif cmd in ("/seguimientos", "/seguimiento", "/segs"):
            tg_send(cmd_seguimientos(db, args), cid, db)
        else:
            tg_send(f"🤷 Comando no reconocido: <b>{cmd}</b>\nUsa /ayuda para ver los comandos disponibles.", cid, db)

        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
