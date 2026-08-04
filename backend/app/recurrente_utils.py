import httpx
import os

RECURRENTE_API_KEY = os.getenv("RECURRENTE_API_KEY", "")
RECURRENTE_API = "https://app.recurrente.com/api"

def crear_plan(nombre, precio, moneda="GTQ", intervalo="month", descripcion=""):
    try:
        resp = httpx.post(
            f"{RECURRENTE_API}/plans",
            json={
                "name": nombre,
                "amount": int(precio * 100),
                "currency": moneda,
                "interval": intervalo,
                "description": descripcion
            },
            headers={"Authorization": f"Bearer {RECURRENTE_API_KEY}"},
            timeout=15
        )
        return {"ok": resp.status_code < 400, "data": resp.json() if resp.status_code < 400 else resp.text}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

def crear_cliente(nombre, email, telefono=""):
    try:
        resp = httpx.post(
            f"{RECURRENTE_API}/customers",
            json={"name": nombre, "email": email, "phone": telefono},
            headers={"Authorization": f"Bearer {RECURRENTE_API_KEY}"},
            timeout=15
        )
        return {"ok": resp.status_code < 400, "data": resp.json() if resp.status_code < 400 else resp.text}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

def crear_suscripcion(customer_id, plan_id):
    try:
        resp = httpx.post(
            f"{RECURRENTE_API}/subscriptions",
            json={"customer_id": customer_id, "plan_id": plan_id},
            headers={"Authorization": f"Bearer {RECURRENTE_API_KEY}"},
            timeout=15
        )
        return {"ok": resp.status_code < 400, "data": resp.json() if resp.status_code < 400 else resp.text}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

def crear_checkout(plan_id, success_url, cancel_url, customer_email=""):
    try:
        resp = httpx.post(
            f"{RECURRENTE_API}/checkout/sessions",
            json={
                "plan_id": plan_id,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "customer_email": customer_email
            },
            headers={"Authorization": f"Bearer {RECURRENTE_API_KEY}"},
            timeout=15
        )
        return {"ok": resp.status_code < 400, "data": resp.json() if resp.status_code < 400 else resp.text}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

def listar_planes():
    try:
        resp = httpx.get(
            f"{RECURRENTE_API}/plans",
            headers={"Authorization": f"Bearer {RECURRENTE_API_KEY}"},
            timeout=15
        )
        return {"ok": True, "data": resp.json() if resp.status_code < 400 else []}
    except Exception as e:
        return {"ok": False, "data": [], "msg": str(e)}
