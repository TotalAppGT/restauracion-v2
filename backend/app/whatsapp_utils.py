import httpx
import os
import logging

logger = logging.getLogger("whatsapp_utils")

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "EAATUvL0iC3cBSNsEmoNdwUmKBu3ZBaFhMES58Ym2onRFKMF8DwzZCe9O3N5YJDtlfHjnBYYbZBY1QBY2UnUAiO5wP6KAOwXKz500tAZApd0eHiLOVdHu7PFCmptpuWYEg4xXiib2MfhZB1cwQZAexBteGrxX8ZBlVfpAdZBq3TltNL4mekJbu2p8wNukEyT53gZDZD")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "1178159198722196")
WHATSAPP_TEMPLATE = os.getenv("WHATSAPP_TEMPLATE", "totalappgt_aviso")
WHATSAPP_TEMPLATE_LANG = os.getenv("WHATSAPP_TEMPLATE_LANG", "es_MX")
WHATSAPP_API = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}/messages" if WHATSAPP_PHONE_ID else ""

PROXY_URL = os.getenv("PROXY_URL", "")
PROXY_API_KEY = os.getenv("PROXY_API_KEY", "proxy_master_2026_secret")
SISTEMA_NOMBRE = os.getenv("SISTEMA_NOMBRE", "REDIL")
SISTEMA_URL = os.getenv("SISTEMA_URL", "https://redilrestauracion.totalappgt.online")
SISTEMA_WEBHOOK_URL = f"{SISTEMA_URL}/api/whatsapp/webhook"
SISTEMA_ID = os.getenv("SISTEMA_ID", "")

def _registrar_en_proxy(wamid):
    if not PROXY_URL or not wamid:
        return
    try:
        httpx.post(f"{PROXY_URL}/api/registrar-wamid", json={
            "wamid": wamid,
            "sistema_url": SISTEMA_WEBHOOK_URL,
            "sistema_nombre": SISTEMA_NOMBRE
        }, timeout=5)
    except Exception:
        pass

def _registrar_telefono_en_proxy(phone, internal_user_id=None):
    if not PROXY_URL or not phone:
        return
    sid = SISTEMA_ID
    if not sid:
        try:
            resp = httpx.get(f"{PROXY_URL}/api/systems", timeout=5)
            for s in resp.json().get("systems", []):
                if s.get("name") == SISTEMA_NOMBRE:
                    sid = s["id"]
                    break
        except Exception:
            pass
    if not sid:
        return
    try:
        httpx.post(f"{PROXY_URL}/api/systems/register-phone", json={
            "system_id": sid,
            "phone": str(phone).replace("+", "").replace(" ", "").replace("-", ""),
            "internal_user_id": str(internal_user_id) if internal_user_id else None
        }, timeout=5)
    except Exception:
        pass

def registrar_sistema_en_proxy():
    global SISTEMA_ID
    if not PROXY_URL or not PROXY_API_KEY:
        return
    try:
        resp = httpx.post(f"{PROXY_URL}/api/systems", json={
            "name": SISTEMA_NOMBRE,
            "webhook_url": SISTEMA_WEBHOOK_URL
        }, headers={"X-API-Key": PROXY_API_KEY}, timeout=10)
        if resp.status_code in (200, 201):
            data = resp.json()
            SISTEMA_ID = data.get("id", "")
            logger.info(f"Sistema {SISTEMA_NOMBRE} registrado en el proxy (id: {SISTEMA_ID})")
        else:
            logger.warning(f"No se pudo registrar en el proxy: {resp.status_code} {resp.text[:200]}")
    except Exception:
        logger.warning("No se pudo conectar con el proxy para registro inicial")

registrar_sistema_en_proxy()

def _extract_wamid(resp):
    try:
        data = resp.json()
        msgs = data.get("messages", [])
        if msgs:
            return msgs[0].get("id", "")
    except Exception:
        pass
    return ""

def send_whatsapp(to_number, message, db=None, internal_user_id=None):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return {"ok": False, "msg": "WhatsApp no configurado"}
    try:
        clean_number = str(to_number).replace("+", "").replace(" ", "").replace("-", "")
        resp = httpx.post(
            WHATSAPP_API,
            json={
                "messaging_product": "whatsapp",
                "to": clean_number,
                "type": "text",
                "text": {"body": str(message)[:4000]}
            },
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=15
        )
        wamid = _extract_wamid(resp) if resp.status_code < 400 else ""
        if wamid:
            _registrar_en_proxy(wamid)
        if resp.status_code < 400:
            _registrar_telefono_en_proxy(clean_number, internal_user_id)
        return {"ok": resp.status_code < 400, "msg": resp.text[:200] if resp.status_code >= 400 else "Enviado", "wamid": wamid}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

def send_whatsapp_document(to_number, pdf_url, caption="", filename="informe.pdf", internal_user_id=None):
    """Send PDF document via WhatsApp"""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return {"ok": False, "msg": "WhatsApp no configurado"}
    try:
        clean_number = str(to_number).replace("+", "").replace(" ", "").replace("-", "")
        fn = filename or "informe.pdf"
        if fn == "informe.pdf" and pdf_url:
            parts = pdf_url.strip("/").split("/")
            if parts:
                no_serie = parts[-1]
                fn = f"{no_serie}.pdf"
        print(f"[WA-DOC] Enviando a {clean_number} link={pdf_url} fn={fn}")
        resp = httpx.post(
            WHATSAPP_API,
            json={
                "messaging_product": "whatsapp",
                "to": clean_number,
                "type": "document",
                "document": {
                    "link": pdf_url,
                    "filename": fn,
                    "caption": caption[:1024] if caption else None
                }
            },
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        print(f"[WA-DOC] Status={resp.status_code} Resp={resp.text[:500]}")
        wamid = _extract_wamid(resp) if resp.status_code < 400 else ""
        if wamid:
            _registrar_en_proxy(wamid)
        if resp.status_code < 400:
            _registrar_telefono_en_proxy(clean_number, internal_user_id)
        return {"ok": resp.status_code < 400, "msg": resp.text[:300] if resp.status_code >= 400 else "Enviado", "wamid": wamid, "status_code": resp.status_code}
    except Exception as e:
        print(f"[WA-DOC] Error: {e}")
        return {"ok": False, "msg": str(e)}

def sincronizar_contactos_proxy(db_session=None):
    """Sincroniza todos los contactos con telefono al proxy para enrutamiento."""
    if not PROXY_URL or not SISTEMA_ID:
        logger.warning("Proxy no configurado, omitiendo sincronizacion de contactos")
        return {"ok": False, "msg": "Proxy no configurado"}

    try:
        from app.database import SessionLocal
        from app.models import Hermano, Supervisor, Pastore, AyudaPastor, Contacto, Bautizo
        cerrar_db = False
        if db_session is None:
            db_session = SessionLocal()
            cerrar_db = True

        try:
            count = 0
            telefonos_vistos = set()

            # Supervisor
            for obj in db_session.query(Supervisor).filter(Supervisor.telefono.isnot(None), Supervisor.telefono != "").all():
                phone = str(obj.telefono).replace("+", "").replace(" ", "").replace("-", "")
                if phone and len(phone) >= 8 and phone not in telefonos_vistos:
                    telefonos_vistos.add(phone)
                    try:
                        httpx.post(f"{PROXY_URL}/api/systems/register-phone", json={
                            "system_id": SISTEMA_ID, "phone": phone,
                            "internal_user_id": f"sup_{obj.codigo_sup}"
                        }, timeout=3)
                        count += 1
                    except Exception: pass

            # Pastore
            for obj in db_session.query(Pastore).filter(Pastore.telefono.isnot(None), Pastore.telefono != "").all():
                phone = str(obj.telefono).replace("+", "").replace(" ", "").replace("-", "")
                if phone and len(phone) >= 8 and phone not in telefonos_vistos:
                    telefonos_vistos.add(phone)
                    try:
                        httpx.post(f"{PROXY_URL}/api/systems/register-phone", json={
                            "system_id": SISTEMA_ID, "phone": phone,
                            "internal_user_id": f"pastor_{obj.codigo_pastor}"
                        }, timeout=3)
                        count += 1
                    except Exception: pass

            # AyudaPastor
            for obj in db_session.query(AyudaPastor).filter(AyudaPastor.telefono.isnot(None), AyudaPastor.telefono != "").all():
                phone = str(obj.telefono).replace("+", "").replace(" ", "").replace("-", "")
                if phone and len(phone) >= 8 and phone not in telefonos_vistos:
                    telefonos_vistos.add(phone)
                    try:
                        httpx.post(f"{PROXY_URL}/api/systems/register-phone", json={
                            "system_id": SISTEMA_ID, "phone": phone,
                            "internal_user_id": f"ayuda_{obj.codigo_ayuda}"
                        }, timeout=3)
                        count += 1
                    except Exception: pass

            # Contacto
            for obj in db_session.query(Contacto).filter(Contacto.telefono.isnot(None), Contacto.telefono != "").all():
                phone = str(obj.telefono).replace("+", "").replace(" ", "").replace("-", "")
                if phone and len(phone) >= 8 and phone not in telefonos_vistos:
                    telefonos_vistos.add(phone)
                    try:
                        httpx.post(f"{PROXY_URL}/api/systems/register-phone", json={
                            "system_id": SISTEMA_ID, "phone": phone,
                            "internal_user_id": f"contacto_{obj.id}"
                        }, timeout=3)
                        count += 1
                    except Exception: pass

            # Bautizo
            for obj in db_session.query(Bautizo).filter(Bautizo.telefono.isnot(None), Bautizo.telefono != "").all():
                phone = str(obj.telefono).replace("+", "").replace(" ", "").replace("-", "")
                if phone and len(phone) >= 8 and phone not in telefonos_vistos:
                    telefonos_vistos.add(phone)
                    try:
                        httpx.post(f"{PROXY_URL}/api/systems/register-phone", json={
                            "system_id": SISTEMA_ID, "phone": phone,
                            "internal_user_id": f"bautizo_{obj.id}"
                        }, timeout=3)
                        count += 1
                    except Exception: pass

            logger.info(f"Sincronizados {count} contactos al proxy")
            return {"ok": True, "msg": f"{count} contactos sincronizados", "total": count}
        finally:
            if cerrar_db:
                db_session.close()
    except Exception as e:
        logger.error(f"Error sincronizando contactos: {e}")
        return {"ok": False, "msg": str(e)}

def send_whatsapp_bulk(numbers, message, pdf_url=None):
    """Send WhatsApp message to multiple numbers, optionally with PDF"""
    results = []
    for num in numbers:
        if pdf_url:
            r = send_whatsapp_document(num, pdf_url, message)
        else:
            r = send_whatsapp(num, message)
        results.append(r)
    ok_count = sum(1 for r in results if r.get("ok"))
    return {"ok": ok_count > 0, "msg": f"Enviado a {ok_count}/{len(numbers)} contactos"}

def send_whatsapp_template(to_number, template_name=None, params=None, internal_user_id=None):
    """Send approved WhatsApp template. Template alerta_totalappgt body: 'Notificacion: {{1}} Abre el enlace en tu correo.'"""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return {"ok": False, "msg": "WhatsApp no configurado"}
    try:
        tname = template_name or WHATSAPP_TEMPLATE
        clean_number = str(to_number).replace("+", "").replace(" ", "").replace("-", "")
        body = {
            "messaging_product": "whatsapp",
            "to": clean_number,
            "type": "template",
            "template": {"name": tname, "language": {"code": WHATSAPP_TEMPLATE_LANG}}
        }
        if params:
            if tname == "totalappgt_aviso":
                if len(params) < 2:
                    return {"ok": False, "msg": "totalappgt_aviso requiere 2 parametros (sistema, mensaje)"}
                body["template"]["components"] = [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(params[0]), "parameter_name": "sistema"},
                        {"type": "text", "text": str(params[1]), "parameter_name": "mensaje"}
                    ]
                }]
            else:
                body["template"]["components"] = [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(p)} for p in params]
                }]
        resp = httpx.post(
            WHATSAPP_API,
            json=body,
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=15
        )
        wamid = _extract_wamid(resp) if resp.status_code < 400 else ""
        if wamid:
            _registrar_en_proxy(wamid)
        if resp.status_code < 400:
            _registrar_telefono_en_proxy(clean_number, internal_user_id)
        return {"ok": resp.status_code < 400, "msg": resp.text[:200] if resp.status_code >= 400 else "Enviado", "wamid": wamid}
    except Exception as e:
        return {"ok": False, "msg": str(e)}
